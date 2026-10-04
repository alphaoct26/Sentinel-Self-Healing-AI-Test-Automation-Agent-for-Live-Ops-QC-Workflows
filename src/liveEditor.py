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
Your task is to identify the EXACT snippet in the target HTML file that needs to be modified based on the user's plain-English instruction.

CRITICAL INSTRUCTIONS:
1. Return ONLY a valid JSON object or JSON array with "find" and "replace" keys:
{
  "find": "exact unique text or HTML snippet in the file to be replaced",
  "replace": "new text or HTML snippet to replace it with"
}

Or if multiple replacements are required:
[
  { "find": "exact text 1", "replace": "new text 1" },
  { "find": "exact text 2", "replace": "new text 2" }
]

CRITICAL RULES:
1. "find" MUST match existing characters in the file EXACTLY (case-sensitive verbatim match).
2. Keep "find" concise (just the tag, attribute, or string that needs changing).
3. Do NOT include markdown fences, commentary, or conversational text. Return ONLY the raw JSON.
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
    match = re.search(r"^```(?:html|json)?\s*\n(.*?)\n```$", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    if cleaned.startswith("```html") or cleaned.startswith("```json"):
        cleaned = cleaned[7:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned

def fallback_heuristic_edit(content: str, instruction: str) -> str:
    """
    Rule-based smart fallback for plain-English instructions.
    Handles phrases like 'Change the player name Viper_QC to vaibhav',
    'Set rank to Diamond Legend', 'Btn -> "Sync Match Data"', etc.
    """
    clean_inst = instruction.strip()
    inst_lower = clean_inst.lower()

    # Preset 1: Player name replacement (e.g. "Change the player name Viper_QC to vaibhav" or "Player -> 'Phoenix_Pro'")
    if ("player" in inst_lower or "viper" in inst_lower) and ("to" in inst_lower or "->" in inst_lower or "=>" in inst_lower):
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_name = parts[-1].strip(" '\"`")
            for current_player in ["Viper_QC", "vaibhav", "Phoenix_Pro"]:
                if current_player in content:
                    print(f"[LiveEditor Fallback] Player name update: '{current_player}' -> '{new_name}'")
                    return content.replace(current_player, new_name)

    # Preset 2: Rank badge update (e.g. "Rank -> 'Diamond Legend'" or "Change rank to Diamond Legend")
    if any(k in inst_lower for k in ["rank", "tier", "badge", "diamond"]):
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_rank = parts[-1].strip(" '\"`")
            for current_rank in ["Top Rank: Elite", "Diamond Legend", "Grandmaster", "Bronze Tier"]:
                if current_rank in content:
                    print(f"[LiveEditor Fallback] Rank tier update: '{current_rank}' -> '{new_rank}'")
                    return content.replace(current_rank, new_rank)

    # Preset 3: Win message update (e.g. "Win Msg -> 'Victory!'" or "Change win message to Victory!")
    if any(k in inst_lower for k in ["win msg", "win message", "victory", "match complete"]):
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_msg = parts[-1].strip(" '\"`")
            for current_msg in ["Match Complete: You Win!", "Victory!", "Match Complete", "Mission Accomplished"]:
                if current_msg in content:
                    print(f"[LiveEditor Fallback] Win message update: '{current_msg}' -> '{new_msg}'")
                    return content.replace(current_msg, new_msg)

    # Preset 4: Button text update (e.g. "Btn -> 'Sync Match Data'")
    if any(k in inst_lower for k in ["btn", "button", "refresh", "sync"]):
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_btn = parts[-1].strip(" '\"`")
            for current_btn in ["Refresh Leaderboard", "Sync Match Data", "Reload Table"]:
                if current_btn in content:
                    print(f"[LiveEditor Fallback] Button text update: '{current_btn}' -> '{new_btn}'")
                    return content.replace(current_btn, new_btn)

    # Preset 5: Title update (e.g. "Title -> 'eSports Live'")
    if any(k in inst_lower for k in ["title", "esports", "standings"]):
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_title = parts[-1].strip(" '\"`")
            for current_title in ["Cyber Arena: Match Standings", "eSports Live", "Global Standings"]:
                if current_title in content:
                    print(f"[LiveEditor Fallback] Title update: '{current_title}' -> '{new_title}'")
                    return content.replace(current_title, new_title)

    # Preset 6: Season update (e.g. "Season 4 -> 7")
    if "season" in inst_lower:
        parts = re.split(r"\bto\b|->|=>", clean_inst, flags=re.IGNORECASE)
        if len(parts) >= 2:
            new_val = parts[-1].strip(" '\"`")
            new_season = f"Season {new_val}" if not new_val.lower().startswith("season") else new_val
            for s in ["Season 4", "Season 7", "Season 1", "Season 2", "Season 3"]:
                if s in content:
                    print(f"[LiveEditor Fallback] Season update: '{s}' -> '{new_season}'")
                    return content.replace(s, new_season)

    # General split on ' to ', ' with ', ' into ', ' -> ', ' => '
    parts = re.split(r"\bto\b|\bwith\b|\binto\b|->|=>", clean_inst, flags=re.IGNORECASE)
    if len(parts) >= 2:
        left_part = parts[0].strip()
        new_str = parts[1].strip(" '\"`")

        # Strip prefixes like "change", "replace", "rename", "set", "the", etc.
        noise = ["change the", "replace the", "update the", "rename the", "set the", "change", "replace", "update", "rename", "set", "say"]
        for n in noise:
            if left_part.lower().startswith(n + " "):
                left_part = left_part[len(n)+1:].strip()

        # Further strip qualifiers
        qualifiers = [
            "player name", "player", "button selector", "button id", "button text", "button",
            "rank tier", "rank badge", "rank", "text", "message", "msg", "element"
        ]
        for q in qualifiers:
            if left_part.lower().startswith(q + " "):
                left_part = left_part[len(q)+1:].strip()

        old_str = left_part.strip(" '\"`")

        # Direct string replacement
        if old_str and old_str in content:
            print(f"[LiveEditor Fallback] Direct replacement: '{old_str}' -> '{new_str}'")
            return content.replace(old_str, new_str)

        # Check individual words in old_str to see if any exist in content
        for word in old_str.split():
            w_clean = word.strip(" '\"`,;:")
            if len(w_clean) >= 3 and w_clean in content:
                print(f"[LiveEditor Fallback] Word token replacement: '{w_clean}' -> '{new_str}'")
                return content.replace(w_clean, new_str)

    return content

def apply_live_edit(instruction: str, target_file: str = None, auto_confirm: bool = False) -> bool:
    """
    Executes a live AI code-edit on a view file:
    1. Resolves target view.
    2. Sends instruction + current content to LLM to produce targeted find/replace JSON.
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
                max_tokens=1000,
                timeout=60
            )
            raw_response = response.choices[0].message.content.strip()

            # Attempt parsing JSON find/replace
            try:
                json_match = re.search(r"(\[.*\]|\{.*\})", raw_response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                    if isinstance(data, dict):
                        data = [data]
                    if isinstance(data, list):
                        temp_content = current_content
                        replaced_count = 0
                        for item in data:
                            f_str = item.get("find", "")
                            r_str = item.get("replace", "")
                            if f_str and f_str in temp_content:
                                temp_content = temp_content.replace(f_str, r_str)
                                replaced_count += 1
                                print(f"[LiveEditor AI] Replaced '{f_str[:40]}' with '{r_str[:40]}'")
                        if replaced_count > 0:
                            proposed_content = temp_content
            except Exception:
                pass

            # Fallback check if AI returned full HTML
            if not proposed_content:
                cleaned = clean_llm_response(raw_response)
                if (cleaned.startswith("<!DOCTYPE") or "<html" in cleaned[:200]) and len(cleaned) >= len(current_content) * 0.8:
                    proposed_content = cleaned

        except Exception as e:
            print(f"[LiveEditor Warning] {AI_PROVIDER} API call failed ({e}). Attempting fallback edit...")

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
