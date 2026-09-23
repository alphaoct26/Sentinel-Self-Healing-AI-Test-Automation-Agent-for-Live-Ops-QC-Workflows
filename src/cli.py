import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import requests
from src.config import TARGET_APP_URL
from src.generator import generate_test_from_spec
from src.runner import run_test_suite
from src.selfHealer import heal_last_run
from src.ragEngine import ask_question

def set_drift_mode(mode_name):
    mode_clean = mode_name.upper()
    valid_modes = ["NORMAL", "SELECTOR_DRIFT", "ASSERTION_DRIFT", "REAL_BUG"]
    if mode_clean not in valid_modes:
        print(f"[CLI Error] Invalid drift mode '{mode_name}'. Valid options: {', '.join(valid_modes)}")
        return False

    try:
        res = requests.post(f"{TARGET_APP_URL}/api/drift", json={"mode": mode_clean}, timeout=3)
        if res.status_code == 200:
            print(f"[CLI] Target App DRIFT_MODE successfully set to: {mode_clean}")
            return True
    except Exception:
        pass

    # Fallback env var setter / query parameter simulation note
    os.environ["DRIFT_MODE"] = mode_clean
    print(f"[CLI] Set environment variable DRIFT_MODE={mode_clean}")
    print(f"[CLI] Target App URL: {TARGET_APP_URL}/?drift={mode_clean}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Sentinel: Self-Healing Test Automation CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: generate
    subparsers.add_parser("generate", help="Generate Playwright test suite from feature spec")

    # Command: run
    subparsers.add_parser("run", help="Run Playwright test suite headlessly")

    # Command: heal
    subparsers.add_parser("heal", help="Diagnose last failed run and execute self-healing repair or safeguard")

    # Command: drift
    drift_parser = subparsers.add_parser("drift", help="Set target app's drift mode")
    drift_parser.add_argument("mode", choices=["NORMAL", "SELECTOR_DRIFT", "ASSERTION_DRIFT", "REAL_BUG"], help="Drift mode state")

    # Command: ask
    ask_parser = subparsers.add_parser("ask", help="Query RAG knowledge assistant over specs and logs")
    ask_parser.add_argument("query", nargs="+", help="Natural language question")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        print("=== [Sentinel] Generating Test Suite from Spec ===")
        generate_test_from_spec()

    elif args.command == "run":
        print("=== [Sentinel] Executing Playwright Test Suite ===")
        run_test_suite()

    elif args.command == "heal":
        print("=== [Sentinel] Running Self-Healing Diagnostic & Safeguard Engine ===")
        heal_last_run()

    elif args.command == "drift":
        print(f"=== [Sentinel] Setting Target App Drift Mode to {args.mode} ===")
        set_drift_mode(args.mode)

    elif args.command == "ask":
        question = " ".join(args.query)
        print(f"=== [Sentinel RAG] Query: '{question}' ===")
        ask_question(question)

if __name__ == "__main__":
    main()
