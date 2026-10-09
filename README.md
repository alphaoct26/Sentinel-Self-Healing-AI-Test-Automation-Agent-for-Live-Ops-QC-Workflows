<div align="center">

# 🛡️ Sentinel

### Self-Healing AI Test-Automation Agent for Live Ops & QC Workflows

*Sentinel watches your tests, diagnoses failures with multimodal AI, and heals cosmetic drift — automatically.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.63.0-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![Pytest](https://img.shields.io/badge/Pytest-9.1.1-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA_NIM-LLaMA_3.2-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](./LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/features/actions)

</div>

---

## 🎯 What is Sentinel?

**Sentinel** is an autonomous, self-healing test automation CLI agent built for QA/QC teams in fast-paced live-service environments — AAA games, real-time dashboards, and SaaS platforms.

It solves **one of the biggest pains in QA**: tests that break every week because a developer renamed a button ID, changed some copy, or tweaked a layout — all harmless changes, but enough to cause 10+ false-positive alerts and hours of manual locator fixes.

**Sentinel handles that automatically:**

| Without Sentinel | With Sentinel |
|:---|:---|
| Button ID renamed → test fails → engineer manually fixes locator | Button ID renamed → Sentinel detects drift → AI diagnoses → patch verified → test passes ✅ |
| Copy text updated → assertion fails → CI blocked | Copy text updated → Sentinel classifies assertion drift → auto-patch → CI green ✅ |
| Real backend HTTP 500 → test fails → someone silences it | Real HTTP 500 → Sentinel refuses to auto-patch → flags for human review 🚨 |

---

## ⚡ How It Works — Animated Workflow

```
╔══════════════════════════════════════════════════════════════════════╗
║                      🛡️  SENTINEL PIPELINE                          ║
╚══════════════════════════════════════════════════════════════════════╝

  📝 Plain-English Spec
       leaderboard_spec.md
             │
             ▼  [STEP 1] Generate
  ┌────────────────────────┐
  │   🤖 Test Generator    │  ← src/generator.py
  │   LLM → Playwright     │    Uses: NVIDIA NIM / Gemini
  └──────────┬─────────────┘
             │  Writes: tests/test_leaderboard.py
             ▼  [STEP 2] Execute
  ┌────────────────────────┐
  │  🎭 Playwright Runner  │  ← src/runner.py
  │  Headless Chromium     │    Captures: DOM + Screenshots
  └────────┬───────────────┘
           │
     ┌─────┴──────┐
     │            │
   PASS ✅      FAIL ❌
     │            │
     ▼            ▼  [STEP 3] Diagnose
   📊 Log    ┌────────────────────────┐
   & Done    │   🧠 Self-Healer AI    │  ← src/selfHealer.py
             │   Multimodal LLM +     │    Reads: DOM diff
             │   Rule Heuristics      │    Reads: Screenshot
             └──────────┬─────────────┘    Reads: Failure trace
                        │
           ┌────────────┴────────────┐
           │                         │
   COSMETIC DRIFT               REAL BUG / UNCERTAIN
   Confidence ≥ 80%             (HTTP 500/403, timeout,
           │                    malformed data, <80%)
           ▼  [STEP 4] Heal          ▼  [STEP 5] Safeguard
  ┌────────────────────┐    ┌────────────────────────────┐
  │  🔧 Auto-Patch     │    │  🚨 Human Review Safeguard │
  │  Apply code fix    │    │  Decline auto-patch         │
  │  to temp test file │    │  Write incident report      │
  └────────┬───────────┘    │  Attach before/after shots  │
           │                └────────────────────────────┘
           ▼  [STEP 6] Verify
  ┌────────────────────┐
  │  ✅ Re-run Test    │  ← Live app verification
  │                    │
  │  PASSES → Commit   │  Patch is real and works
  │  FAILS  → Rollback │  Discard patch, stay safe
  └────────────────────┘

  🛡️  DOUBLE SAFETY NET: Confidence Gate + Live Verification
      = Dual verification safeguards against silent test breaks
```

---

## 🔑 The 3 Core Pillars

### 1. 📝 Spec-to-Test Generation
Write requirements in plain English. Sentinel converts them to full Playwright test scripts using LLM reasoning — no manual test authoring needed.

```bash
python src/cli.py generate
# Reads:  specs/leaderboard_spec.md
# Writes: tests/test_leaderboard.py
```

### 2. 🔧 Autonomous Self-Healing with Dual Safety
When a test fails, Sentinel:
1. Captures full DOM snapshot + screenshot
2. Diagnoses root cause via multimodal AI (LLaMA 3.2 Vision → Gemini fallback)
3. Applies a code patch **only if confidence ≥ 80%** and classification is cosmetic
4. **Re-runs the test against the live app** — if it still fails, the patch is discarded (rollback)

### 3. 🚨 Human Review Safeguard (Anti-Fake-Fix)
On genuine backend regressions (HTTP 500, HTTP 403, timeouts, malformed data), Sentinel **strictly refuses to modify the test**. It logs an incident report with visual evidence for human review.

> **This safeguard prevents Sentinel from silently masking real bugs.** The double-check (confidence threshold + live verification) ensures candidate patches are verified against the running application before acceptance.

---

## 📊 Benchmark: 23 Mutation Scenarios

Tested across every major failure class — Selector Drift, Assertion Drift, DOM Restructuring, Backend Regressions, and Compound failures. Raw run outputs: [`benchmark_results_llm.json`](./artifacts/benchmark_results_llm.json) (online run with LLM keys) and [`benchmark_results_offline.json`](./artifacts/benchmark_results_offline.json) (offline heuristic baseline).

### Results at a Glance (measured with LLM keys configured)

| Metric | Result |
|:---|:---:|
| 🎯 Heal Precision (committed patches) | **100.0%** (10/10 committed patches were correct; 10 of 14 candidate patches were correct, 4 were discarded by live verification) |
| 🩹 Cosmetic Drift Healing Rate | **90.9%** (10/11 healed; 1 compound rolled back) |
| 🚫 False-Heal Rate | **0.0%** (0/8 bad patches committed; 4 real bugs blocked by the classifier, 3 rolled back by live verification, 1 (BUG_SERVER_TIMEOUT) not detected by the test because the client tolerates the delay) |
| 🔄 Live Verification Rollback | 4/4 unverified candidate patches safely discarded |

*(Note: In offline mode without LLM keys: 23 scenarios, 0 true heals (0/11), 0 false heals (0/8), 6 of 8 real bugs held directly (75.0%), precision N/A with 0 patches attempted. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.)*

<details>
<summary>📋 Click to expand — All 23 Scenarios (measured with LLM keys configured)</summary>

<br/>

| # | Scenario | Category | Ground Truth | AI Classification | Confidence | Action | Result |
|:-:|:---|:---|:---|:---|:-:|:---|:---:|
| 01 | `NORMAL` | Baseline | Clean | None | — | Baseline / Locator Robust | ✅ PASSED |
| 02 | `SELECTOR_RENAME_BTN` | Selector Drift | Cosmetic | `SELECTOR_DRIFT` | 80.0% | Auto-Patched & Verified | ✅ HEALED |
| 03 | `SELECTOR_PREFIX_CHANGE` | Selector Drift | Cosmetic | `SELECTOR_DRIFT` | 80.0% | Auto-Patched & Verified | ✅ HEALED |
| 04 | `SELECTOR_RENAME_CONTAINER` | Selector Drift | Cosmetic | `SELECTOR_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 05 | `SELECTOR_RENAME_BADGE` | Selector Drift | Cosmetic | `SELECTOR_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 06 | `SELECTOR_RENAME_EXPORT` | Selector Drift | Cosmetic | `SELECTOR_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 07 | `MOVED_ELEMENT_NESTED` | DOM Structure | DOM Reorg | None | — | Baseline / Locator Robust | ✅ PASSED |
| 08 | `MOVED_BUTTON_CONTAINER` | DOM Structure | DOM Reorg | None | — | Baseline / Locator Robust | ✅ PASSED |
| 09 | `SLOW_INITIAL_RENDER` | Timing | Latency | None | — | Baseline / Locator Robust | ✅ PASSED |
| 10 | `COPY_RANK_TIER_LABEL` | Assertion Drift | Cosmetic | `ASSERTION_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 11 | `COPY_CASE_CHANGE` | Assertion Drift | Cosmetic | `ASSERTION_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 12 | `COPY_PUNCTUATION_CHANGE` | Assertion Drift | Cosmetic | `ASSERTION_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 13 | `COPY_EXPANDED_PHRASE` | Assertion Drift | Cosmetic | `ASSERTION_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 14 | `COPY_LOCALIZED_SYNONYM` | Assertion Drift | Cosmetic | `SELECTOR_DRIFT` | 90.0% | Auto-Patched & Verified | ✅ HEALED |
| 15 | `BUG_HTTP_500` | Backend Bug | Real Bug | `GENUINE_BUG` | 90.0% | 🚨 Human Review Safeguard | 🛡️ HELD |
| 16 | `BUG_HTTP_403_FORBIDDEN` | Backend Bug | Real Bug | `GENUINE_BUG` | 90.0% | 🚨 Human Review Safeguard | 🛡️ HELD |
| 17 | `BUG_MALFORMED_JSON` | Backend Bug | Real Bug | `GENUINE_BUG` | 80.0% | 🚨 Human Review Safeguard | 🛡️ HELD |
| 18 | `BUG_SERVER_TIMEOUT` | Backend Bug | Real Bug | None | — | Baseline / Locator Robust | ✅ PASSED |
| 19 | `BUG_MISSING_PAYLOAD_FIELD` | Backend Bug | Real Bug | `ASSERTION_DRIFT` | 80.0% | Verification Failed (Rolled Back) | 🛡️ SAFE (Rollback) |
| 20 | `INTERMITTENT_EXPORT_FAILURE` | Backend Bug | Real Bug | `GENUINE_BUG` | 80.0% | 🚨 Human Review Safeguard | 🛡️ HELD |
| 21 | `COMPOUND_SELECTOR_AND_500` | Compound Drift | Real Bug | `SELECTOR_DRIFT` | 80.0% | Verification Failed (Rolled Back) | 🛡️ SAFE (Rollback) |
| 22 | `COMPOUND_COPY_AND_403` | Compound Drift | Real Bug | `ASSERTION_DRIFT` | 80.0% | Verification Failed (Rolled Back) | 🛡️ SAFE (Rollback) |
| 23 | `COMPOUND_SELECTOR_AND_COPY` | Compound Drift | Cosmetic | `SELECTOR_DRIFT` | 80.0% | Verification Failed (Rolled Back) | 🛡️ SAFE (Rollback) |

</details>

---

## 🏗️ Project Structure

```
sentinel-qc/
│
├── 📁 src/                          # Core engine
│   ├── cli.py                       # Entry point — all CLI commands
│   ├── generator.py                 # Plain-English spec → Playwright test
│   ├── liveEditor.py                # Live AI code-editor for UI changes with unified diff & backups
│   ├── runner.py                    # Playwright execution + artifact capture
│   ├── selfHealer.py                # AI diagnosis, patching, rollback logic
│   └── ragEngine.py                 # In-memory RAG over specs/logs/code
│
├── 📁 specs/                        # Plain-English feature specifications
│   └── leaderboard_spec.md          # Leaderboard & match stats feature spec
│
├── 📁 tests/                        # Generated Playwright test suites
│   └── test_leaderboard.py          # Auto-generated from leaderboard spec
│
├── 📁 target-app/                   # Live drift-simulation app (localhost:3001)
│   ├── server.py                    # 23-mode mutation API server
│   └── views/index.html             # Leaderboard UI with drift templates
│
├── 📁 artifacts/                    # Audit trail output (auto-generated)
│   ├── edits/                       # Backups and patch diffs from live edit sessions
│   ├── repairs/                     # Before/after screenshots + unified diffs
│   └── AUDIT_LOG.md                 # Unified repair audit index
│
├── 📁 docs/                         # Deep-dive documentation
│   ├── SENTINEL_MASTER_OVERVIEW.md  # Full architecture + PPT guide
│   └── confidence-scoring.md        # Confidence methodology transparency
│
├── 📁 scripts/                      # Tooling & automation
│   └── benchmark_runner.py          # Runs all 23 mutation scenarios
│
├── 📁 .github/workflows/
│   └── test.yml                     # CI/CD — auto-runs on every push/PR
│
├── requirements.txt                 # Pinned Python dependencies
├── pytest.ini                       # Pytest configuration
├── sentinel.bat                     # Windows quick-launch shortcut
└── .env                             # API keys (not committed)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for the target app)
- An NVIDIA NIM API key **or** a Google Gemini API key

### Step 1 — Clone & Install

```bash
git clone https://github.com/alphaoct26/Sentinel-Self-Healing-AI-Test-Automation-Agent-for-Live-Ops-QC-Workflows.git
cd sentinel-qc

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### Step 2 — Configure API Keys

```bash
# Windows
echo NVIDIA_API_KEY=your_nvidia_key_here > .env
echo GEMINI_API_KEY=your_gemini_key_here >> .env
```

> Get a free NVIDIA NIM key at [build.nvidia.com](https://build.nvidia.com) · Get Gemini key at [aistudio.google.com](https://aistudio.google.com)

### Step 3 — Start the Target App

```bash
# In Terminal 1: start the live drift-simulation server
python target-app/server.py
# Serving at http://localhost:3001
```

### Step 4 — Run the Full Pipeline

```bash
# In Terminal 2: run Sentinel
python src/cli.py generate        # Generate tests from spec
python src/cli.py run             # Execute tests + capture artifacts
python src/cli.py heal            # AI diagnosis + auto-heal
```

---

## 💻 CLI Reference

```
python src/cli.py <command> [options]
```

| Command | What it does |
|:---|:---|
| `generate` | Reads `specs/leaderboard_spec.md` → writes `tests/test_leaderboard.py` using LLM |
| `run` | Executes Playwright tests headlessly, captures DOM snapshots + full-page screenshots |
| `drift <MODE>` | Activates a specific mutation on the target app (e.g. `SELECTOR_RENAME_BTN`) |
| `edit "<instruction>"` | **Live AI Code-Editor** — applies unscripted UI modifications to `target-app/views/` with unified diff preview, `[y/N]` confirmation, and automated backup to `artifacts/edits/` |
| `heal` | AI diagnoses last failure, proposes a patch, live-verifies it, then commits or rolls back |
| `ask "<query>"` | RAG assistant — ask natural-language questions about the spec, test code, or run logs |

### 🛠️ Live AI Code-Editing (Unscripted Drift Injection)

Want to demo or test Sentinel against unscripted, spontaneous changes rather than pre-set drift modes? Use the `edit` command:

```bash
# Apply a live cosmetic or locator change in plain English
python src/cli.py edit "In index.html, change {{RANK_BADGE_TEXT}} to 'Season 1: Grandmaster'"

# Sentinel previews a unified diff in your console:
# ========================================================================
# --- a/target-app/views/index.html
# +++ b/target-app/views/index.html
# @@ -294,7 +294,7 @@
# - <div class="score-value" id="{{RANK_BADGE_ID}}">{{RANK_BADGE_TEXT}}</div>
# + <div class="score-value" id="{{RANK_BADGE_ID}}">Season 1: Grandmaster</div>
# ========================================================================
# Apply this change to 'target-app/views/index.html'? [y/N]: y
```
- **Safe by Default**: Automatically creates a backup in `artifacts/edits/<timestamp>/`.
- **Live Proof**: Re-run `python src/cli.py run` → fails against your exact wording → `python src/cli.py heal` diagnoses and adapts your test suite to match.

**Available drift modes:**
```
NORMAL                   SELECTOR_RENAME_BTN       SELECTOR_PREFIX_CHANGE
SELECTOR_RENAME_CONTAINER SELECTOR_RENAME_BADGE     SELECTOR_RENAME_EXPORT
MOVED_ELEMENT_NESTED     MOVED_BUTTON_CONTAINER     SLOW_INITIAL_RENDER
COPY_RANK_TIER_LABEL     COPY_CASE_CHANGE           COPY_PUNCTUATION_CHANGE
COPY_EXPANDED_PHRASE     COPY_LOCALIZED_SYNONYM     BUG_HTTP_500
BUG_HTTP_403_FORBIDDEN   BUG_MALFORMED_JSON         BUG_SERVER_TIMEOUT
BUG_MISSING_PAYLOAD_FIELD INTERMITTENT_EXPORT_FAILURE COMPOUND_SELECTOR_AND_500
COMPOUND_COPY_AND_403    COMPOUND_SELECTOR_AND_COPY
```

---

## 🧠 Tech Stack

| Layer | Technology | Version | Role |
|:---|:---|:---:|:---|
| Core Runtime | Python | 3.11+ | Engine, CLI, heuristics |
| Browser Automation | Playwright | 1.63.0 | Headless Chromium, DOM snapshots, screenshots |
| Test Framework | Pytest | 9.1.1 | Test discovery, assertions, CI runner |
| AI Client | OpenAI SDK | 2.32.0 | Interface to LLM providers |
| Primary AI | NVIDIA NIM | LLaMA-3.2-11b-Vision | Multimodal diagnosis, confidence scoring |
| Fallback AI | Google Gemini | 2.5 Flash | Auto-fallback when primary is unavailable |
| Local Heuristics | Python stdlib | `re`, `difflib`, `ast` | Offline regex/keyword classifier (Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.) |
| Knowledge Engine | Custom RAG | In-memory TF-IDF | TF-IDF keyword retrieval over specs, tests and run artifacts |
| Target App | Python http.server | — | Live drift-simulation app |
| Environment | python-dotenv | 1.2.2 | API key loading from `.env` |
| HTTP | Requests | 2.33.1 | CLI ↔ target app drift API calls |
| CI/CD | GitHub Actions & Jenkins | Ubuntu / Docker | GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server. |

---

## 🔒 Safety Architecture: Why Sentinel Can't Break Your Tests

Sentinel uses a **double safety net** — two independent checks must both pass before any code change is committed:

```
     LLM Diagnosis Result
             │
   ┌─────────▼──────────┐
   │  GATE 1: Confidence │  ← Must be ≥ 80% AND classified as cosmetic drift
   │  Threshold Check    │    If not → Human Review, no patch applied
   └─────────┬───────────┘
             │ Passed Gate 1
   ┌─────────▼──────────┐
   │  Apply Patch to    │  ← Patch written to a TEMPORARY copy of the test file
   │  Temp Test File    │    Original is untouched at this stage
   └─────────┬───────────┘
             │
   ┌─────────▼──────────┐
   │  GATE 2: Live      │  ← Re-run test against the live running app
   │  Verification      │    Passes → patch committed to real file
   └─────────┬───────────┘    Fails  → patch discarded, rollback complete
             │ Passed Gate 2
   ┌─────────▼──────────┐
   │  Commit Patch ✅   │  ← Audit trail written to artifacts/repairs/
   └────────────────────┘
```

**Even if the AI produces a wrong fix, Gate 2 catches it.** No patch ever lands without live proof.

---

## 🧪 Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# Run the 23-scenario mutation benchmark
python scripts/benchmark_runner.py
```

GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server.

---

## 🚀 CI/CD Pipelines

Sentinel includes CI/CD automation: GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server:

### 1. GitHub Actions (`.github/workflows/test.yml`)
- **Trigger**: Every `push` and `pull_request` targeting `main`.
- **Environment**: Hosted `ubuntu-latest` with Python 3.11 and Playwright Chromium.
- **Workflow**:
  1. Checks out repository (`actions/checkout@v4`).
  2. Sets up Python 3.11 with `pip` cache (`actions/setup-python@v5`).
  3. Installs dependencies from `requirements.txt` and Chromium via `playwright install --with-deps chromium`.
  4. Launches `target-app/server.py` in the background on port `3001` with a 30-iteration `curl` readiness health check.
  5. Executes Sentinel test suite via CLI runner (`python src/cli.py run`).
  6. Executes Pytest suite (`pytest -v`).
  7. Uploads test run artifacts (`artifacts/runs/`) on every run (`actions/upload-artifact@v4`).

### 2. Jenkins Declarative Pipeline (`Jenkinsfile`)
- **Agent**: Docker container using the official Playwright Python image pinned to `mcr.microsoft.com/playwright/python:v1.63.0-noble` with `--ipc=host`.
- **Pipeline Options**: Configured with `timeout(30m)`, `timestamps()`, `disableConcurrentBuilds()`, and `buildDiscarder(logRotator(numToKeepStr: '20'))`.
- **Stages**:
  1. **Checkout**: Retrieves source code from SCM.
  2. **Setup**: Injects optional AI credentials, provisions Python virtual environment (`.venv`), installs `requirements.txt`, and ensures Chromium binaries and dependencies are present.
  3. **Start Target App**: Spawns `target-app/server.py` on port `3001` in the background and polls `http://localhost:3001` until healthy (fails if not ready within 30s timeout).
  4. **Test**: Executes Sentinel CLI runner (`python src/cli.py run`) and Pytest with JUnit XML output (`pytest -v --junitxml=artifacts/junit-report.xml`).
  5. **Benchmark**: Runs the 23-scenario mutation benchmark (`python scripts/benchmark_runner.py`) and evaluates the quality gate against `artifacts/benchmark_results.json`. When AI provider credentials are configured, the pipeline strictly enforces `summary.heal_precision_pct >= 100%` and `summary.false_heal_rate_pct == 0%` (measured with LLM keys configured). When running in offline fallback mode without API keys, it logs the benchmark summary and safeguard enforcement metrics without failing the build. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.
  6. **Archive and Report**: Publishes JUnit test reports (`artifacts/junit-report.xml`) and archives all build artifacts (`artifacts/**`, including `benchmark_results.json`, screenshots, and `AUDIT_LOG.md`).
  7. **Post-Build Cleanup**: Automatically terminates the background target app server (via stored PID) and cleans up lingering processes.
- *Verification Status*: Jenkinsfile written and reviewed; not yet run on a live Jenkins server.

### 3. CI/CD Credentials (All Optional)
Neither pipeline requires secret API keys to succeed. If no credentials are configured, Sentinel automatically falls back to its deterministic offline local-heuristics engine (Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.):
- `NIM_API_KEY` (or `NVIDIA_API_KEY`): Optional credential ID in Jenkins for NVIDIA NIM LLaMA-3.2 multimodal diagnosis.
- `GEMINI_API_KEY`: Optional credential ID in Jenkins for Google Gemini 2.5 Flash fallback diagnosis.

*Quality Gate Behavior*: When AI credentials are provided, the benchmark quality gate strictly requires 100% heal precision and 0% false heals (measured with LLM keys configured). When running offline with no keys configured, the benchmark logs all metrics and passes without failing the build as long as safeguards protect the suite from false heals. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.

### 4. Running the Pipeline Locally with Docker
You can reproduce the exact pipeline environment locally using Docker without needing a Jenkins server:

```bash
docker run --rm -it --ipc=host -v "${PWD}:/workspace" -w /workspace mcr.microsoft.com/playwright/python:v1.63.0-noble bash -c "
  python3 -m venv .venv && \
  . .venv/bin/activate && \
  pip install --upgrade pip && \
  pip install -r requirements.txt && \
  playwright install --with-deps chromium && \
  python target-app/server.py > target_app.log 2>&1 & \
  for i in \$(seq 1 30); do curl -s -f http://localhost:3001 > /dev/null 2>&1 && break || sleep 1; done && \
  python src/cli.py run && \
  pytest -v --junitxml=artifacts/junit-report.xml && \
  python scripts/benchmark_runner.py
"
```

### 5. Running Jenkins Locally with Docker Agent
To run this pipeline on a local Jenkins instance with Docker agents:
- The **Docker Pipeline plugin** (`docker-workflow`) is required in Jenkins.
- The Jenkins controller container needs access to the host Docker engine, typically configured by mounting `/var/run/docker.sock` from the host and ensuring the `docker` CLI binary is available inside the Jenkins container.
- *Verification Note*: Running Jenkins locally with this Docker-out-of-Docker setup has not been tested in this environment.
---

## 📁 Documentation

| Document | Description |
|:---|:---|
| [`docs/SENTINEL_MASTER_OVERVIEW.md`](./docs/SENTINEL_MASTER_OVERVIEW.md) | Full architecture deep-dive, component breakdown, PPT slide guide, AI context primer |
| [`docs/confidence-scoring.md`](./docs/confidence-scoring.md) | How confidence scoring works — honest about what it is and isn't |
| [`artifacts/AUDIT_LOG.md`](./artifacts/AUDIT_LOG.md) | Unified repair audit index with before/after screenshot links |
| [`scripts/benchmark_runner.py`](./scripts/benchmark_runner.py) | Run the full 23-scenario mutation benchmark yourself |

---

## 🎖️ Designed For

This project demonstrates applied AI in production QA engineering, with direct relevance to:

- **Live-service game QA** (leaderboards, match stats, live events — e.g. Ubisoft)
- **QA Automation R&D** teams building self-healing test infrastructure
- **Any team** where UI cosmetic drift causes high test-maintenance overhead

---

<div align="center">

**Built with 🧠 AI + 🎭 Playwright + 🛡️ Safety-First Design**

[📖 Full Docs](./docs/SENTINEL_MASTER_OVERVIEW.md) · [🔬 Benchmark](./scripts/benchmark_runner.py) · [📊 Audit Log](./artifacts/AUDIT_LOG.md)

</div>
