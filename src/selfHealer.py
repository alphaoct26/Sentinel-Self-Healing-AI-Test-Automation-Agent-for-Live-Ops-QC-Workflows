import os
import sys
import json
import re
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from openai import OpenAI
import shutil
import difflib
from playwright.sync_api import sync_playwright
from src.config import (
    SPECS_DIR, TESTS_DIR, RUNS_DIR, REPAIRS_DIR, ARTIFACTS_DIR, TARGET_APP_URL,
    GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, AI_PROVIDER,
    CONFIDENCE_THRESHOLD
)

def record_audit_artifacts(timestamp, drift_mode, classification, confidence, rationale, old_code, new_code, verification_result, run_data):
    repair_folder = REPAIRS_DIR / timestamp
    repair_folder.mkdir(parents=True, exist_ok=True)

    before_img_path = repair_folder / "before.png"
    after_img_path = repair_folder / "after.png"

    # Copy before screenshot if available from run_data, else capture
    before_src = run_data.get("screenshot") or run_data.get("full_screenshot")
    if before_src and Path(before_src).exists():
        try:
            shutil.copy(before_src, before_img_path)
        except Exception:
            pass

    if not before_img_path.exists():
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                pg = b.new_page()
                pg.goto(TARGET_APP_URL)
                pg.screenshot(path=str(before_img_path), full_page=True)
                b.close()
        except Exception:
            pass

    # Capture after screenshot of current target app state
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page()
            pg.goto(TARGET_APP_URL)
            pg.screenshot(path=str(after_img_path), full_page=True)
            b.close()
    except Exception:
        if before_img_path.exists():
            shutil.copy(before_img_path, after_img_path)

    # Compute actual unified diff
    test_rel_path = "tests/test_leaderboard.py"
    diff_lines = list(difflib.unified_diff(
        old_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        fromfile=f"{test_rel_path} (Original)",
        tofile=f"{test_rel_path} (Repaired)"
    ))
    diff_text = "".join(diff_lines).strip()
    if not diff_text:
        diff_text = "No code changes made (Safeguard Triggered)."

    # Structured edit_log.json
    edit_log_json_data = {
        "timestamp": timestamp,
        "drift_mode": drift_mode,
        "classification": classification,
        "file_changed": test_rel_path,
        "diff": diff_text,
        "diagnosis": rationale,
        "confidence": confidence,
        "verification_result": verification_result,
        "before_screenshot": "before.png",
        "after_screenshot": "after.png"
    }

    with open(repair_folder / "edit_log.json", "w", encoding="utf-8") as f:
        json.dump(edit_log_json_data, f, indent=2)

    # Human-readable edit_log.md
    with open(repair_folder / "edit_log.md", "w", encoding="utf-8") as f:
        f.write(f"# Sentinel Self-Healing Edit Log\n\n")
        f.write(f"- **Timestamp**: `{timestamp}`\n")
        f.write(f"- **Drift Mode**: `{drift_mode}`\n")
        f.write(f"- **File Changed**: `{test_rel_path}`\n")
        f.write(f"- **AI Diagnosis Engine**: `{AI_PROVIDER} API ({GEMINI_MODEL})`\n")
        f.write(f"- **Classification**: `{classification}`\n")
        f.write(f"- **Confidence**: `{confidence * 100:.1f}%`\n")
        f.write(f"- **Verification Result**: `{verification_result}`\n\n")
        f.write(f"## Diagnostic Rationale\n{rationale}\n\n")
        f.write(f"## Code Patch Diff\n```diff\n{diff_text}\n```\n\n")
        f.write(f"## Visual Audit Trail\n\n")
        f.write(f"| Before Repair | After Repair |\n")
        f.write(f"| :---: | :---: |\n")
        f.write(f"| ![Before Repair](before.png) | ![After Repair](after.png) |\n")

    # Master Audit Log (artifacts/AUDIT_LOG.md)
    master_audit_file = ARTIFACTS_DIR / "AUDIT_LOG.md"
    if not master_audit_file.exists():
        with open(master_audit_file, "w", encoding="utf-8") as f:
            f.write("# Master Audit Trail of Autonomous AI Edits\n\n")
            f.write("| Timestamp | Drift Mode | File Changed | Confidence | Result | Edit Log |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

    with open(master_audit_file, "a", encoding="utf-8") as f:
        f.write(f"| {timestamp} | {drift_mode} | {test_rel_path} | {confidence * 100:.1f}% | {verification_result} | [edit_log.md](repairs/{timestamp}/edit_log.md) |\n")

    print(f"[SelfHealer] Visual + edit audit trail recorded at {repair_folder / 'edit_log.md'}")
    print(f"[SelfHealer] Master audit index updated at {master_audit_file}")

DIAGNOSTIC_PROMPT = """You are Sentinel's Self-Healing Test Diagnostic Agent.
Analyze the provided test failure log, DOM snapshot, and feature spec.

Determine whether the failure is caused by:
1. SELECTOR_DRIFT: Element locator changed in UI (e.g. ID, class, or button label renamed).
2. ASSERTION_DRIFT: Displayed text/value formatting changed while underlying logic is working.
3. GENUINE_BUG: Backend application error (500 status), broken functional workflow, or server fault.

Respond in strict JSON format:
{
  "classification": "SELECTOR_DRIFT" | "ASSERTION_DRIFT" | "GENUINE_BUG",
  "confidence": float between 0.0 and 1.0,
  "rationale": "Clear technical explanation of diagnosis",
  "target_selector_old": "old selector if applicable else null",
  "target_selector_new": "new selector if applicable else null",
  "target_assertion_old": "old expected text if applicable else null",
  "target_assertion_new": "new expected text if applicable else null"
}
"""

def heal_last_run():
    # Find latest run file
    run_files = sorted(list(RUNS_DIR.glob("run_*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_files:
        print("[SelfHealer] No execution run logs found in artifacts/runs/")
        return False

    latest_run_file = run_files[0]
    with open(latest_run_file, "r", encoding="utf-8") as f:
        run_data = json.load(f)

    if run_data.get("status") == "PASSED":
        print(f"[SelfHealer] Latest run ({latest_run_file.name}) was PASSED. No repair needed.")
        return True

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    drift_mode = run_data.get("drift_mode", "UNKNOWN")
    print(f"\n[SelfHealer] Analyzing failure log: {latest_run_file.name} (Drift Mode: {drift_mode})...")

    # Load spec & test file
    spec_path = SPECS_DIR / "leaderboard_spec.md"
    if not spec_path.exists():
        spec_path = SPECS_DIR / "resume_ats_spec.md"

    spec_content = ""
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            spec_content = f.read()

    test_file_path = TESTS_DIR / "test_leaderboard.py"
    if not test_file_path.exists():
        test_file_path = TESTS_DIR / "test_resume_ats.py"

    with open(test_file_path, "r", encoding="utf-8") as f:
        test_code_old = f.read()

    dom_snippet = run_data.get("dom_snapshot", "")
    error_summary = run_data.get("error_summary", "")

    diagnosis = None

    # Call Gemini API if key available
    if GEMINI_API_KEY:
        try:
            print(f"[SelfHealer] Sending diagnostic payload to {AI_PROVIDER} API ({GEMINI_MODEL})...")
            client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            res = client.chat.completions.create(
                model=GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": DIAGNOSTIC_PROMPT},
                    {"role": "user", "content": f"Spec:\n{spec_content}\n\nError Summary:\n{error_summary}\n\nDOM Snapshot:\n{dom_snippet[:3000]}"}
                ],
                temperature=0.1,
                timeout=15
            )
            raw = res.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```json"):
                raw = raw[7:].rstrip("`").strip()
            elif raw.startswith("```"):
                raw = raw[3:].rstrip("`").strip()
            diagnosis = json.loads(raw)
        except Exception as e:
            print(f"[SelfHealer Warning] {AI_PROVIDER} API diagnostic failed ({e}). Running local rule-based heuristic...")

    # Precision rule-based heuristic classifier (fallback only)
    if not diagnosis:
        if "500" in error_summary or "Internal Server Error" in error_summary or "HTTP 500" in error_summary or "ERR_HTTP_RESPONSE_CODE_FAILURE" in error_summary or "Status 500" in error_summary:
            diagnosis = {
                "classification": "GENUINE_BUG",
                "confidence": 0.95,
                "rationale": "Backend API endpoint returned HTTP 500 Internal Server Error during export report request.",
                "target_selector_old": None,
                "target_selector_new": None,
                "target_assertion_old": None,
                "target_assertion_new": None
            }
        elif ("reload-leaderboard-btn" in dom_snippet or "submit-resume-btn" in dom_snippet) and ("#refresh-btn" in test_code_old or "#analyze-btn" in test_code_old):
            old_s = "#refresh-btn" if "#refresh-btn" in test_code_old else "#analyze-btn"
            new_s = "#reload-leaderboard-btn" if "reload-leaderboard-btn" in dom_snippet else "#submit-resume-btn"
            diagnosis = {
                "classification": "SELECTOR_DRIFT",
                "confidence": 0.92,
                "rationale": f"Refresh button ID renamed from '{old_s}' to '{new_s}' in DOM (simulating UI redesign).",
                "target_selector_old": old_s,
                "target_selector_new": new_s,
                "target_assertion_old": None,
                "target_assertion_new": None
            }
        elif ("Current Tier: Elite" in dom_snippet or "Compatibility Rating" in dom_snippet) and ("Top Rank: Elite" in test_code_old or "Match Score: 85%" in test_code_old):
            old_t = "Top Rank: Elite" if "Top Rank: Elite" in test_code_old else "Match Score: 85%"
            new_t = "Current Tier: Elite" if "Current Tier: Elite" in dom_snippet else "Compatibility Rating: 85/100"
            diagnosis = {
                "classification": "ASSERTION_DRIFT",
                "confidence": 0.90,
                "rationale": f"Rank badge text format changed from '{old_t}' to '{new_t}' in DOM (simulating copy update).",
                "target_selector_old": None,
                "target_selector_new": None,
                "target_assertion_old": old_t,
                "target_assertion_new": new_t
            }
        else:
            diagnosis = {
                "classification": "GENUINE_BUG",
                "confidence": 0.70,
                "rationale": "Unrecognized error pattern or ambiguous DOM mismatch.",
                "target_selector_old": None,
                "target_selector_new": None,
                "target_assertion_old": None,
                "target_assertion_new": None
            }

    classification = diagnosis.get("classification")
    confidence = float(diagnosis.get("confidence", 0.0))
    rationale = diagnosis.get("rationale", "")

    print(f"\n[SelfHealer Diagnosis]")
    print(f" |-- Category:   {classification}")
    print(f" |-- Confidence: {confidence*100:.1f}% (Threshold: {CONFIDENCE_THRESHOLD*100:.0f}%)")
    print(f" +-- Rationale:  {rationale}\n")

    # Safeguard check
    if classification in ["SELECTOR_DRIFT", "ASSERTION_DRIFT"] and confidence >= CONFIDENCE_THRESHOLD:
        print("[SelfHealer] Safeguard Passed: Category is patchable and confidence >= 80%. Generating repair patch...")

        test_code_patched = test_code_old

        if classification == "SELECTOR_DRIFT":
            old_sel = diagnosis.get("target_selector_old") or ("#refresh-btn" if "#refresh-btn" in test_code_old else "#analyze-btn")
            new_sel = diagnosis.get("target_selector_new") or "#reload-leaderboard-btn"
            test_code_patched = test_code_patched.replace(old_sel, new_sel)

        elif classification == "ASSERTION_DRIFT":
            old_txt = diagnosis.get("target_assertion_old") or ("Top Rank: Elite" if "Top Rank: Elite" in test_code_old else "Match Score: 85%")
            new_txt = diagnosis.get("target_assertion_new") or "Current Tier: Elite"
            test_code_patched = test_code_patched.replace(old_txt, new_txt)

        # Write candidate patch
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code_patched)

        print("[SelfHealer] Re-running test suite to verify patch...")
        from src.runner import run_test_suite
        verify_results, _ = run_test_suite()

        if verify_results["status"] == "PASSED":
            print("[SelfHealer] Repair VERIFIED! Test suite passed with patch.")
            record_audit_artifacts(timestamp, drift_mode, classification, confidence, rationale, test_code_old, test_code_patched, "PASSED", run_data)
            return True
        else:
            print("[SelfHealer] Patch verification failed. Rolling back test file...")
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_code_old)
            record_audit_artifacts(timestamp, drift_mode, classification, confidence, rationale, test_code_old, test_code_old, "FAILED", run_data)
            return False

    # Human Review Safeguard Branch
    print("[SelfHealer Safeguard Triggered] Declining auto-patch!")
    safeguard_reason = (
        "Application functional bug detected."
        if classification == "GENUINE_BUG"
        else f"Confidence ({confidence*100:.1f}%) below required threshold ({CONFIDENCE_THRESHOLD*100:.0f}%)."
    )
    print(f"Reason: {safeguard_reason}")

    # Restore original test file
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_code_old)

    record_audit_artifacts(timestamp, drift_mode, classification, confidence, rationale, test_code_old, test_code_old, "HUMAN_REVIEW_REQUIRED", run_data)
    return False

if __name__ == "__main__":
    heal_last_run()

if __name__ == "__main__":
    heal_last_run()
