import os
import sys
import json
import datetime
import shutil
import difflib
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure Windows terminal handles UTF-8 smoothly
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from openai import OpenAI
from src.config import (
    BASE_DIR, ARTIFACTS_DIR,
    GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, AI_PROVIDER
)

VIEWS_DIR = BASE_DIR / "target-app" / "views"
EDITS_DIR = ARTIFACTS_DIR / "edits"
EDITS_DIR.mkdir(parents=True, exist_ok=True)

LIVE_EDIT_PROMPT = """You are Sentinel's Live AI Code Editor for the target web application.
Your task is to apply a precise, minimal edit to the target HTML/view file based on the user's plain-English instruction.

STRICT REQUIREMENTS:
1. Make ONLY the minimal change requested. Do NOT refactor, reformat, reorder, or touch any other part of the file.
2. Preserve all existing HTML elements, attributes, IDs, inline styles, script tags, and template variables (e.g. {{DRIFT_MODE}}, {{REFRESH_BTN_ID}}, {{RESULTS_SECTION_ID}}, {{RANK_BADGE_ID}}, {{EXPORT_BTN_ID}}, {{RANK_BADGE_TEXT}}) UNLESS the user explicitly asks to modify that specific element or text.
3. Return the COMPLETE, valid, updated file content from the very first line to the very last line.
4. Return ONLY the raw file content — absolutely NO markdown code fences (do NOT include ```html or ```), NO conversational commentary, and NO explanations.
"""

def resolve_target_file(instruction: str, explicit_file: str = None) -> Path:
    """
    Determines which view file in target-app/views/ should be edited.
    Explicit parameter takes priority; otherwise infers from instruction context.
    """
    if explicit_file:
        candidate = Path(explicit_file)
        if candidate.is_file():
            return candidate
        candidate_in_views = VIEWS_DIR / candidate.name
        if candidate_in_views.is_file():
            return candidate_in_views

    # Infer from instruction text
    inst_lower = instruction.lower()
    available_files = list(VIEWS_DIR.glob("*.html"))

    # Direct filename mention
    for f in available_files:
        if f.name.lower() in inst_lower:
            print(f"[LiveEditor] Target view inferred from filename mention: target-app/views/{f.name}")
            return f

    # Contextual keywords
    if any(k in inst_lower for k in ["dashboard", "control panel", "diagnostic", "drift button", "matrix"]):
        dash = VIEWS_DIR / "dashboard.html"
        if dash.exists():
            print(f"[LiveEditor] Target view inferred from context: target-app/views/dashboard.html")
            return dash
    elif any(k in inst_lower for k in ["decoy", "resume", "ats"]):
        decoy = VIEWS_DIR / "decoy.html"
        if decoy.exists():
            print(f"[LiveEditor] Target view inferred from context: target-app/views/decoy.html")
            return decoy

    # Default to primary target app view (index.html)
    primary = VIEWS_DIR / "index.html"
    print(f"[LiveEditor] Target view selected (primary app view): target-app/views/{primary.name}")
    return primary

def backup_file_before_edit(target_file: Path, instruction: str, original_content: str, diff_text: str):
    """
    Creates an automated backup of the target file before any modifications are committed to disk.
    Saved to artifacts/edits/<timestamp>/ in the same spirit as selfHealer.py repair artifacts.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = EDITS_DIR / timestamp
    backup_folder.mkdir(parents=True, exist_ok=True)

    backup_path = backup_folder / target_file.name
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(original_content)

    # Save diff & metadata for audit trail
    with open(backup_folder / "edit.patch", "w", encoding="utf-8") as f:
        f.write(diff_text)

    metadata = {
        "timestamp": timestamp,
        "target_file": str(target_file.relative_to(BASE_DIR)).replace("\\", "/"),
        "instruction": instruction,
        "backup_path": str(backup_path.relative_to(BASE_DIR)).replace("\\", "/")
    }
    with open(backup_folder / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return backup_path, backup_folder

def clean_llm_response(raw_text: str) -> str:
    """
    Strips accidental markdown code block fences or leading/trailing comments.
    """
    cleaned = raw_text.strip()
    match = re.search(r"^```(?:html)?\s*\n(.*?)\n```$", cleaned, re.DOTALL)
    if match:
        return match.group(1)
    
    if cleaned.startswith("```html"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned

def fallback_heuristic_edit(content: str, instruction: str) -> str:
    """
    Rule-based regex fallback if AI API is unreachable.
    Handles standard patterns like 'change "old" to "new"' or 'rename "old" to "new"'.
    """
    patterns = [
        r'(?:change|replace|update|set)\s+[\'"]?([^\'"]+?)[\'"]?\s+(?:to|with|into)\s+[\'"]?([^\'"]+?)[\'"]?$',
        r'(?:rename)\s+[\'"]?([^\'"]+?)[\'"]?\s+(?:to)\s+[\'"]?([^\'"]+?)[\'"]?$',
        r'say\s+[\'"]([^\'"]+)[\'"]\s+instead\s+of\s+[\'"]([^\'"]+)[\'"]'
    ]

    for pat in patterns:
        m = re.search(pat, instruction, re.IGNORECASE)
        if m:
            if "say" in pat and "instead of" in pat:
                new_str, old_str = m.group(1), m.group(2)
            else:
                old_str, new_str = m.group(1), m.group(2)

            # Strip leading/trailing quote artifacts if captured
            old_str = old_str.strip("'\"")
            new_str = new_str.strip("'\"")

            if old_str in content:
                print(f"[LiveEditor Fallback] Replacing '{old_str}' with '{new_str}'")
                return content.replace(old_str, new_str, 1)

    return content

def apply_live_edit(instruction: str, target_file: str = None, auto_confirm: bool = False) -> bool:
    """
    Executes a live AI code-edit on a view file:
    1. Resolves target view.
    2. Sends instruction + current content to LLM.
    3. Computes unified diff.
    4. Prompts for explicit [y/N] confirmation.
    5. Backs up original file to artifacts/edits/<timestamp>/.
    6. Writes confirmed edit to disk and prints summary.
    """
    file_path = resolve_target_file(instruction, target_file)
    if not file_path.exists():
        print(f"[LiveEditor Error] Selected file {file_path} does not exist.")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        current_content = f.read()

    rel_path = file_path.relative_to(BASE_DIR).as_posix()
    print(f"\n[LiveEditor] Applying live edit to: {rel_path}")
    print(f"[LiveEditor] Instruction: \"{instruction}\"")

    proposed_content = None

    if GEMINI_API_KEY:
        try:
            print(f"[LiveEditor] Sending edit request to {AI_PROVIDER} API ({GEMINI_MODEL})...")
            client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            response = client.chat.completions.create(
                model=GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": LIVE_EDIT_PROMPT},
                    {
                        "role": "user",
                        "content": f"Target File: {file_path.name}\n\nModification Instruction:\n{instruction}\n\nFull Current File Content:\n{current_content}"
                    }
                ],
                temperature=0.1,
                timeout=60
            )
            raw_response = response.choices[0].message.content
            proposed_content = clean_llm_response(raw_response)
        except Exception as e:
            print(f"[LiveEditor Warning] {AI_PROVIDER} API call failed ({e}). Attempting fallback edit...")

    # Safeguard against accidental truncation from token limits
    if proposed_content and len(proposed_content) < len(current_content) * 0.7:
        if "delete" not in instruction.lower() and "remove" not in instruction.lower():
            print("[LiveEditor Warning] AI proposed unusually truncated content. Falling back to targeted replacement...")
            proposed_content = fallback_heuristic_edit(current_content, instruction)

    if not proposed_content or proposed_content == current_content:
        proposed_content = fallback_heuristic_edit(current_content, instruction)

    # Compute unified diff
    diff_lines = list(difflib.unified_diff(
        current_content.splitlines(keepends=True),
        proposed_content.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}"
    ))
    diff_text = "".join(diff_lines)

    if not diff_text.strip():
        print("[LiveEditor] No changes proposed. The resulting file is identical to the original.")
        return False

    # Display unified diff in terminal
    print("\n" + "=" * 72)
    print(f"[LiveEditor] PROPOSED UNIFIED DIFF for {rel_path}:")
    print("=" * 72)
    for line in diff_lines:
        try:
            sys.stdout.write(line)
        except UnicodeEncodeError:
            sys.stdout.write(line.encode("ascii", errors="replace").decode("ascii"))
    if not diff_lines[-1].endswith("\n"):
        sys.stdout.write("\n")
    print("=" * 72 + "\n")

    # Explicit confirmation required before writing to disk
    if not auto_confirm:
        try:
            choice = input(f"Apply this change to '{rel_path}'? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"
            print()

        if choice not in ["y", "yes"]:
            print(f"[LiveEditor] Edit aborted by user. '{rel_path}' was NOT modified.")
            return False
    else:
        print("[LiveEditor] Auto-confirm flag provided; proceeding with write.")

    # Automated backup before write
    backup_file, backup_folder = backup_file_before_edit(file_path, instruction, current_content, diff_text)

    # Write changes to disk
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(proposed_content)

    # Calculate summary metrics
    lines_added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    lines_removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    print(f"\n[LiveEditor] SUCCESS: Edit applied and written to disk!")
    print(f" |-- Target File:    {rel_path}")
    print(f" |-- Lines Modified: +{lines_added} / -{lines_removed}")
    print(f" |-- Safe Backup:    {backup_file.relative_to(BASE_DIR).as_posix()}")
    print(f" +-- Instruction:    \"{instruction}\"\n")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/liveEditor.py \"<plain-English instruction>\" [--file <view-file>] [-y]")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description="Live AI Code Editor")
    parser.add_argument("instruction", help="Plain-English edit instruction")
    parser.add_argument("--file", help="Specific view file to edit", default=None)
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm diff")
    args = parser.parse_args()

    apply_live_edit(args.instruction, target_file=args.file, auto_confirm=args.yes)
