from pathlib import Path
from playwright.sync_api import sync_playwright

html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {
            background-color: #090d16;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            margin: 0;
        }
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        .header h1 {
            font-size: 26px;
            margin: 0 0 8px 0;
            color: #ffffff;
            letter-spacing: -0.5px;
        }
        .header p {
            font-size: 14px;
            color: #94a3b8;
            margin: 0;
        }
        .diagram-container {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 32px 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Sentinel QC — Master System Architecture</h1>
        <p>Autonomous Self-Healing AI Pipeline with Dual-Gate Safety Net & Live Verification</p>
    </div>
    <div class="diagram-container">
        <pre class="mermaid">
flowchart TD
    Spec["Plain-English Feature Spec<br/>(specs/leaderboard_spec.md)"] --> Generator["AI Spec-to-Test Generator<br/>(src/generator.py)"]
    Generator --> TestFile["Playwright Test Suite<br/>(tests/test_leaderboard.py)"]
    
    TestFile --> Runner["Playwright Test Runner<br/>(src/runner.py)"]
    TargetApp["Live Target App<br/>(http://localhost:3001)"] <--> Runner
    
    Runner -->|Passes| GreenLog["Verified Execution Log<br/>(artifacts/runs/)"]
    Runner -->|Fails| Diagnostics["Self-Healing Diagnostic Engine<br/>(src/selfHealer.py)"]
    
    subgraph DiagnosticLoop["AI Diagnostic and Safeguard Enforcement"]
        Diagnostics --> Context["Multimodal Context:<br/>- Spec Requirements<br/>- Full DOM Snapshot<br/>- Error Traceback<br/>- Failure Screenshot"]
        Context --> LLM["Multimodal LLM / Heuristic Classifier<br/>(NVIDIA NIM / LLaMA 3.2 Vision / Gemini)"]
        LLM --> Decision{"Classification and<br/>Confidence Score?"}
        
        Decision -->|"GENUINE_BUG or Confidence &lt; 80%"| Safeguard["Human Review Safeguard<br/>(Decline Auto-Patch, Write Incident Report)"]
        Decision -->|"COSMETIC_DRIFT and Confidence &ge; 80%"| CandidatePatch["Generate Candidate Code Patch"]
    end
    
    CandidatePatch --> LiveVerify["Live Verification Test<br/>(Re-run against target app)"]
    
    LiveVerify -->|Tests Pass| CommitPatch["Commit Patch and Update Audit<br/>(artifacts/repairs/ and AUDIT_LOG.md)"]
    LiveVerify -->|Tests Still Fail| Rollback["Immediate Rollback to Baseline<br/>(Safe Failure State)"]
    
    Safeguard --> AuditReport["Visual Incident Audit Report<br/>(before.png + error details)"]
        </pre>
    </div>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'dark',
            themeVariables: {
                darkMode: true,
                background: '#0f172a',
                primaryColor: '#1e293b',
                primaryBorderColor: '#3b82f6',
                primaryTextColor: '#f8fafc',
                lineColor: '#60a5fa',
                secondaryColor: '#312e81',
                tertiaryColor: '#1e1b4b'
            }
        });
    </script>
</body>
</html>"""

def main():
    temp_html = Path("d:/Projects/sentinel-qc/artifacts/scratch_arch.html")
    temp_html.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1300, "height": 1300}, device_scale_factor=2)
        page.goto(f"file:///{temp_html.resolve()}")
        page.wait_for_selector("svg")
        page.wait_for_timeout(1000)
        out_img = Path("d:/Projects/sentinel-qc/artifacts/sentinel_architecture_diagram.png")
        page.screenshot(path=str(out_img), full_page=True)
        browser.close()

    if temp_html.exists():
        temp_html.unlink()

    print("Architecture diagram successfully saved to:", out_img)

if __name__ == "__main__":
    main()
