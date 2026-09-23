import os
import json
import sys
import subprocess
import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PORT = 3001
DRIFT_MODE = "NORMAL"

BASE_DIR = Path(__file__).resolve().parent
VIEWS_DIR = BASE_DIR / "views"
ROOT_DIR = BASE_DIR.parent
RUNS_DIR = ROOT_DIR / "artifacts" / "runs"
REPAIRS_DIR = ROOT_DIR / "artifacts" / "repairs"

class TargetAppHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress verbose HTTP request logging
        return

    def do_GET(self):
        global DRIFT_MODE
        parsed = urlparse(self.path)

        # Dashboard & Decoy UI endpoints
        if parsed.path in ["/dashboard", "/dashboard.html", "/dashboard/"]:
            dash_path = VIEWS_DIR / "dashboard.html"
            if dash_path.exists():
                with open(dash_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return

        if parsed.path in ["/decoy", "/decoy.html", "/decoy/"]:
            decoy_path = VIEWS_DIR / "decoy.html"
            if decoy_path.exists():
                with open(decoy_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return

        # Serve repair artifacts / screenshots statically if requested
        if parsed.path.startswith("/artifacts/repairs/"):
            rel_path = parsed.path.replace("/artifacts/repairs/", "")
            file_path = REPAIRS_DIR / rel_path
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                if file_path.suffix == ".png":
                    self.send_header("Content-Type", "image/png")
                elif file_path.suffix == ".json":
                    self.send_header("Content-Type", "application/json")
                else:
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        if parsed.path == "/api/drift-mode":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"mode": DRIFT_MODE}).encode("utf-8"))
            return

        if parsed.path == "/api/audit-log":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            logs = []
            if REPAIRS_DIR.exists():
                repair_dirs = sorted([d for d in REPAIRS_DIR.glob("*") if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
                for d in repair_dirs:
                    edit_json = d / "edit_log.json"
                    if edit_json.exists():
                        try:
                            with open(edit_json, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                logs.append(data)
                        except Exception:
                            pass

            self.wfile.write(json.dumps(logs).encode("utf-8"))
            return

        # Serve index.html for root or any HTML request
        html_path = VIEWS_DIR / "index.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()

            refresh_btn_id = "reload-leaderboard-btn" if DRIFT_MODE == "SELECTOR_DRIFT" else "refresh-btn"
            rank_badge_text = "Current Tier: Elite" if DRIFT_MODE == "ASSERTION_DRIFT" else "Top Rank: Elite"

            content = content.replace("{{DRIFT_MODE}}", DRIFT_MODE)
            content = content.replace("{{REFRESH_BTN_ID}}", refresh_btn_id)
            content = content.replace("{{RANK_BADGE_TEXT}}", rank_badge_text)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        global DRIFT_MODE
        parsed = urlparse(self.path)

        # Localhost security check for shell execution endpoints
        client_ip = self.client_address[0]
        is_local = client_ip in ["127.0.0.1", "::1", "localhost"] or client_ip.startswith("127.")

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""

        body = {}
        if body_bytes:
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                pass

        if parsed.path in ["/api/drift", "/api/drift-mode"]:
            new_mode = body.get("mode", "").upper()
            if new_mode in ["NORMAL", "SELECTOR_DRIFT", "ASSERTION_DRIFT", "REAL_BUG"]:
                DRIFT_MODE = new_mode
                print(f"[TargetApp Server] DRIFT_MODE set to: {DRIFT_MODE}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "mode": DRIFT_MODE}).encode("utf-8"))
            return

        if parsed.path == "/api/run-test":
            if not is_local:
                self.send_error(403, "Forbidden: Shell execution endpoints only accessible from localhost.")
                return

            print("[TargetApp Server] Executing test suite CLI run via /api/run-test...")
            try:
                res = subprocess.run([sys.executable, str(ROOT_DIR / "src" / "cli.py"), "run"], capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=90)
                run_files = sorted(list(RUNS_DIR.glob("run_*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
                run_data = {}
                if run_files:
                    with open(run_files[0], "r", encoding="utf-8") as f:
                        run_data = json.load(f)

                status = run_data.get("status") or ("PASSED" if res.returncode == 0 else "FAILED")
                error_summary = run_data.get("error_summary") or res.stderr or res.stdout

                resp_payload = {
                    "status": status,
                    "drift_mode": DRIFT_MODE,
                    "timestamp": run_data.get("timestamp") or datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "error_summary": error_summary,
                    "stdout": res.stdout
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
            except subprocess.TimeoutExpired:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "FAILED", "error_summary": "Test execution exceeded 90s timeout."}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "FAILED", "error_summary": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/heal":
            if not is_local:
                self.send_error(403, "Forbidden: Shell execution endpoints only accessible from localhost.")
                return

            print("[TargetApp Server] Running self-healing agent CLI heal via /api/heal...")
            try:
                res = subprocess.run([sys.executable, str(ROOT_DIR / "src" / "cli.py"), "heal"], capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=90)
                repair_dirs = sorted([d for d in REPAIRS_DIR.glob("*") if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
                repair_data = {}
                if repair_dirs:
                    edit_json = repair_dirs[0] / "edit_log.json"
                    if edit_json.exists():
                        with open(edit_json, "r", encoding="utf-8") as f:
                            repair_data = json.load(f)

                resp_payload = {
                    "status": "ok",
                    "classification": repair_data.get("classification") or ("SELECTOR_DRIFT" if "SELECTOR_DRIFT" in res.stdout else ("GENUINE_BUG" if "GENUINE_BUG" in res.stdout else "UNKNOWN")),
                    "confidence": repair_data.get("confidence", 0.90),
                    "verification_result": repair_data.get("verification_result") or ("PASSED" if "VERIFIED" in res.stdout else "HUMAN_REVIEW_REQUIRED"),
                    "rationale": repair_data.get("diagnosis") or repair_data.get("rationale") or res.stdout,
                    "diff": repair_data.get("diff", ""),
                    "stdout": res.stdout
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
            except subprocess.TimeoutExpired:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error_summary": "Heal execution exceeded 90s timeout."}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error_summary": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/export-pdf":
            if DRIFT_MODE == "REAL_BUG":
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Internal Server Error: HTTP 500 PDF generator failed"}).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "pdf_url": "/downloads/resume_report.pdf"}).encode("utf-8"))
            return

        self.send_error(404, "Endpoint Not Found")

def run_server():
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, TargetAppHandler)
    print(f"[TargetApp Server] Running target application at http://localhost:{PORT} (DRIFT_MODE: {DRIFT_MODE})")
    print(f"[TargetApp Server] Demo Control Panel available at: http://localhost:{PORT}/dashboard.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        initial_mode = sys.argv[1].upper()
        if initial_mode in ["NORMAL", "SELECTOR_DRIFT", "ASSERTION_DRIFT", "REAL_BUG"]:
            DRIFT_MODE = initial_mode
    run_server()
