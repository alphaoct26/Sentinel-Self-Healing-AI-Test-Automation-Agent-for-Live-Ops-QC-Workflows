import os
import sys
import json
import datetime
import traceback
import importlib.util
from pathlib import Path
from playwright.sync_api import sync_playwright
from src.config import TESTS_DIR, RUNS_DIR, TARGET_APP_URL

def run_test_suite():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_path = RUNS_DIR / f"run_{timestamp}.json"

    screenshots_dir = RUNS_DIR / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # Detect current drift mode
    drift_mode = os.getenv("DRIFT_MODE", "NORMAL")
    try:
        import requests
        r = requests.get(f"{TARGET_APP_URL}/api/drift-mode", timeout=2)
        if r.status_code == 200:
            drift_mode = r.json().get("mode", drift_mode)
    except Exception:
        pass

    full_screenshot_path = screenshots_dir / f"{drift_mode}_{timestamp}.png"
    failure_screenshot_path = screenshots_dir / f"failure_{drift_mode}_{timestamp}.png"

    # Capture full-page screenshot of current target app state regardless of pass/fail
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page()
            pg.goto(TARGET_APP_URL)
            pg.screenshot(path=str(full_screenshot_path), full_page=True)
            b.close()
    except Exception:
        pass

    results = {
        "timestamp": timestamp,
        "drift_mode": drift_mode,
        "status": "PASSED",
        "target_url": TARGET_APP_URL,
        "tests": [],
        "dom_snapshot": "",
        "full_screenshot": str(full_screenshot_path) if full_screenshot_path.exists() else "",
        "screenshot": str(full_screenshot_path) if full_screenshot_path.exists() else "",
        "error_summary": ""
    }

    test_file = TESTS_DIR / "test_leaderboard.py"
    if not test_file.exists():
        test_file = TESTS_DIR / "test_resume_ats.py"

    if not test_file.exists():
        results["status"] = "FAILED"
        results["error_summary"] = f"Test file not found at {test_file}"
        with open(run_log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[Runner] Execution failed: {results['error_summary']}")
        return results, run_log_path

    print(f"[Runner] Executing Playwright test suite against {TARGET_APP_URL}...")
    
    # Import the test file dynamically to execute its actual current code
    spec = importlib.util.spec_from_file_location("test_resume_ats_dynamic", str(test_file))
    test_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_module)

    # Find test functions in test_module
    test_funcs = [name for name in dir(test_module) if name.startswith("test_")]

    overall_passed = True
    dom_snapshot = ""

    for func_name in test_funcs:
        func = getattr(test_module, func_name)
        t_res = {"name": func_name, "status": "PASSED", "error": "", "traceback": ""}
        try:
            func()
        except Exception as e:
            t_res["status"] = "FAILED"
            t_res["error"] = str(e)
            t_res["traceback"] = traceback.format_exc()
            overall_passed = False
            
            # Capture DOM & failure screenshot at point of failure
            try:
                with sync_playwright() as p:
                    b = p.chromium.launch(headless=True)
                    pg = b.new_page()
                    pg.goto(TARGET_APP_URL)
                    dom_snapshot = pg.content()
                    pg.screenshot(path=str(failure_screenshot_path), full_page=True)
                    results["screenshot"] = str(failure_screenshot_path)
                    b.close()
            except Exception:
                pass

        results["tests"].append(t_res)

    results["status"] = "PASSED" if overall_passed else "FAILED"
    results["dom_snapshot"] = dom_snapshot

    if not overall_passed:
        failed_tests = [t for t in results["tests"] if t["status"] == "FAILED"]
        results["error_summary"] = "\n".join([f"{t['name']}: {t['error']}" for t in failed_tests])

    with open(run_log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    status_symbol = "[PASSED]" if overall_passed else "[FAILED]"
    print(f"[Runner] Suite execution finished: {status_symbol}")
    print(f"[Runner] Execution artifact saved to {run_log_path}")

    return results, run_log_path

if __name__ == "__main__":
    run_test_suite()
