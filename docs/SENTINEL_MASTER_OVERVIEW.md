# Sentinel: Complete System Architecture, Tech Stack & Knowledge Base

> **Document Purpose**: This document serves as the single source of truth for Sentinel. It contains an exhaustive, end-to-end breakdown of what the software does, its exact technology stack, internal component architecture, operational workflows, empirical benchmark results, boundaries (what it does and does not do), and a ready-to-present slide-by-slide deck structure for PPT creation and AI context injection.

---

## 📑 Table of Contents
1. [Executive Summary & Value Proposition](#1-executive-summary--value-proposition)
2. [Complete Technology Stack](#2-complete-technology-stack)
3. [Full Repository Directory Map](#3-full-repository-directory-map)
4. [Component-by-Component Deep Dive](#4-component-by-component-deep-dive)
5. [End-to-End Execution Workflows (with Mermaid Diagrams)](#5-end-to-end-execution-workflows)
6. [Drift Modes & 23-Scenario Mutation Benchmark](#6-drift-modes--23-scenario-mutation-benchmark)
7. [Confidence Scoring & The Double-Layer Safety Net](#7-confidence-scoring--the-double-layer-safety-net)
8. [Explicit System Boundaries: What Sentinel DOES NOT Do](#8-explicit-system-boundaries-what-sentinel-does-not-do)
9. [CLI Command Reference & Usage](#9-cli-command-reference--usage)
10. [Presentation Deck Outline (Slide-by-Slide PPT Guide)](#10-presentation-deck-outline-slide-by-slide-ppt-guide)
11. [AI Assistant Context Primer (for Claude / Gemini)](#11-ai-assistant-context-primer)

---

## 1. Executive Summary & Value Proposition

### What is Sentinel?
**Sentinel** is an autonomous, self-healing test automation agent engineered for Quality Control (QC) and Live-Ops QA teams in fast-paced software development (e.g., live-service gaming like Ubisoft, real-time dashboards, SaaS).

### The Problem It Solves: The "Maintenance Tax"
In live-service web applications, front-end developers frequently push minor cosmetic tweaks:
- Renaming element IDs (`#refresh-btn` $\rightarrow$ `#reload-leaderboard-btn`)
- Updating copy wording (`"Top Rank: Elite"` $\rightarrow$ `"Current Tier: Elite"`)
- Refactoring DOM layouts (nesting buttons inside new containers or toolbars)

**Traditional test frameworks (Selenium, Cypress, vanilla Playwright) fail immediately on these harmless cosmetic changes.** This triggers false-positive alerts, blocks CI/CD pipelines, and forces QA engineers to manually fix broken locators dozens of times each week.

### The Sentinel Solution
1. **Autonomous Spec-to-Test Generation**: Converts plain-English feature requirements directly into executable Playwright test scripts.
2. **Autonomous Self-Healing with Safeguards**: When a test fails, Sentinel captures the full DOM snapshot and failure screenshots, diagnoses the root cause using multimodal LLMs, patches cosmetic locator or copy drift, and **verifies the patch against the live running app** before committing.
3. **The Human Review Safeguard**: If an application error is a genuine backend regression (e.g., HTTP 500, HTTP 403, timeout, malformed data), Sentinel **strictly refuses to modify the test**. Instead, it halts auto-patching and logs an incident report with visual before/after audit trails.

---

## 2. Complete Technology Stack

| Layer | Technologies Used | Exact Version / Spec | Role in Sentinel |
| :--- | :--- | :--- | :--- |
| **Core Runtime** | Python | `3.11+` / `3.14` | Core engine, CLI, test execution, heuristics |
| **Browser Automation** | Microsoft Playwright | `playwright==1.63.0` | Headless Chromium execution, DOM snapshot extraction, full-page screenshots |
| **Test Framework** | Pytest | `pytest==9.1.1` | Native test discovery, assertions, and test runner |
| **AI Diagnosis & LLMs** | OpenAI Python SDK | `openai==2.32.0` | Client interface connecting to LLM providers |
| **Primary AI Provider** | NVIDIA NIM API | Model: `meta/llama-3.2-11b-vision-instruct` | Multimodal diagnostic reasoning, DOM analysis, and confidence scoring |
| **Secondary AI Provider** | Google Gemini API | Model: `gemini-2.5-flash` | Automatic fallback provider for diagnosis and test generation |
| **Local Heuristics** | Python Standard Library | `re`, `difflib`, `json`, `ast` | Fallback classifier when offline. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys. |
| **Knowledge Engine** | Custom RAG Engine | In-Memory TF-IDF Vectorizer | TF-IDF keyword retrieval over specs, tests and run artifacts |
| **Target Application** | Node.js & Python | `Python http.server` + Node Express | Live drift-simulation target app (`http://localhost:3001`) |
| **Environment Mgmt** | python-dotenv | `python-dotenv==1.2.2` | Loading `.env` keys (`NVIDIA_API_KEY`, `GEMINI_API_KEY`) |
| **HTTP Networking** | Requests | `requests==2.33.1` | CLI communication with target app drift endpoints |
| **CI/CD Automation** | GitHub Actions & Jenkins | Ubuntu / Docker | GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server. |

---

## 3. Full Repository Directory Map

```text
sentinel-qc/
├── .github/
│   └── workflows/
│       └── test.yml             # GitHub Actions CI workflow (spins up target app, runs suite)
├── artifacts/                   # Output directory for runtime logs and audits
│   ├── AUDIT_LOG.md             # Master audit trail tracking all AI diagnostic actions
│   ├── benchmark_results.json   # 23-scenario empirical benchmark execution output
│   ├── edits/                   # Automated backups and diff patches from live AI edit sessions
│   ├── repairs/                 # Timestamped folders with diffs, before.png, after.png, edit_log.json
│   └── runs/                    # Execution logs (run_<timestamp>.json) and failure screenshots
├── docs/
│   ├── confidence-scoring.md    # Transparent technical documentation of confidence logic
│   └── SENTINEL_MASTER_OVERVIEW.md # THIS MASTER SPECIFICATION FILE
├── scripts/
│   └── benchmark_runner.py      # Automated benchmark harness executing 23 mutation scenarios
├── specs/
│   └── leaderboard_spec.md      # Plain-English Gherkin-style specification of the target app
├── src/
│   ├── cli.py                   # Central CLI tool: generate, run, heal, drift, edit, ask
│   ├── config.py                # Environment configs, file paths, and AI provider routing
│   ├── generator.py             # Spec-to-Playwright AI test suite generator
│   ├── liveEditor.py            # Live AI code editor for UI views with diff preview and backup
│   ├── ragEngine.py             # RAG knowledge assistant over repository specs and logs
│   ├── runner.py                # Playwright execution harness, DOM scraper, screenshot capture
│   └── selfHealer.py            # AI diagnostic engine, safeguard check, and verification loop
├── target-app/                  # Live target application for testing drift and healing
│   ├── views/
│   │   ├── dashboard.html       # Interactive visual demo control panel with confidence meters
│   │   ├── decoy.html           # Standalone single-page AI self-healing showcase
│   │   └── index.html           # Live leaderboard app with template mutation placeholders
│   ├── server.py                # Python multi-threaded HTTP server simulating 23 drift modes
│   ├── server.js                # Node Express equivalent server
│   ├── package.json             # Target app metadata
│   ├── Dockerfile               # Containerization definition
│   ├── render.yaml              # Render deployment configuration
│   └── railway.json             # Railway deployment configuration
├── tests/
│   ├── test_leaderboard.py      # Primary Playwright test suite for leaderboard spec
│   └── test_resume_ats.py       # Secondary test suite for decoy ATS spec
├── .env                         # Local API credentials (gitignored)
├── .gitignore                   # Ignores venvs, cache, logs, artifacts (preserves AUDIT_LOG.md)
├── LICENSE                      # MIT License
├── pytest.ini                   # Pytest configuration pointing to active suite
├── requirements.txt             # Pinned dependency requirements
└── sentinel.bat                 # Windows execution helper wrapper
```

---

## 4. Component-by-Component Deep Dive

### 1. Spec-to-Test Generator (`src/generator.py`)
- **Function**: Takes a human-readable feature specification (`specs/leaderboard_spec.md`) and compiles it into an executable Playwright Python test file (`tests/test_leaderboard.py`).
- **Prompt Engineering**: Enforces `page.locator("#id")` selectors, explicit assertions (`expect().to_be_visible()`, `expect().to_have_text()`), and synchronous execution wrappers.
- **Fail-Safe Fallback**: If no AI API key is configured, it falls back to a deterministic template generator that emits the verified baseline Playwright test.

### 2. Test Execution Runner (`src/runner.py`)
- **Function**: Executes Playwright tests headlessly against `http://localhost:3001`.
- **Telemetry & Artifacts**:
  - Automatically captures full-page screenshot of the application state before and after runs.
  - On failure, captures the full HTML DOM snapshot (`pg.content()`) and exact point-of-failure screenshot.
  - Logs execution status, elapsed timestamps, and complete tracebacks to `artifacts/runs/run_<timestamp>.json`.

### 3. Self-Healing & Diagnostic Engine (`src/selfHealer.py`)
- **Function**: The brain of Sentinel. It diagnoses why a test failed, determines if repair is permissible, generates a candidate patch, and rigorously validates the repair.
- **Classification Categories**:
  - `SELECTOR_DRIFT`: Element locator changed in UI (e.g. ID renamed, button label changed).
  - `ASSERTION_DRIFT`: Displayed copy changed while functionality works.
  - `GENUINE_BUG`: Backend crash (500), permission failure (403), timeout, or broken functional workflow.
- **Verification Gate**: Any candidate patch is written to test code temporarily and **immediately re-tested against the live app**. If the test passes, the patch is accepted and logged; if it fails, it is **instantly rolled back**.

### 4. Live AI Code Editor (`src/liveEditor.py`)
- **Function**: Enables ad-hoc, unscripted live modifications to target application views (`target-app/views/`) via plain-English instructions.
- **AI-Powered Code Mutation**: Passes view code and user instruction to the primary LLM (or heuristic fallback) to produce minimal, surgical HTML changes without affecting unrelated structure or script logic.
- **Terminal Unified Diff & Confirmation**: Renders a standardized unified diff preview (`difflib.unified_diff`) and strictly requires explicit interactive `[y/N]` confirmation before writing to disk (with optional `-y` bypass).
- **Automated Pre-Write Backup**: Automatically archives the original file, generated patch, and metadata to `artifacts/edits/<timestamp>/` prior to modifying disk state.

### 5. RAG Knowledge Assistant (`src/ragEngine.py`)
- **Function**: TF-IDF keyword retrieval over specs, tests and run artifacts for natural-language Q&A assistance.
- **Data Ingestion**: Parses feature specs (`specs/`), active test code (`tests/`), and execution run history (`artifacts/runs/`).
- **Query Loop**: Allows engineers to run `python src/cli.py ask "Why did the last run fail?"` or `python src/cli.py ask "What selectors are used in the leaderboard spec?"`.

### 6. Central CLI Interface (`src/cli.py`)
- Provides unified developer ergonomics:
  - `python src/cli.py generate` $\rightarrow$ Generates tests from spec.
  - `python src/cli.py run` $\rightarrow$ Runs test suite (exits with code 1 on failure for CI).
  - `python src/cli.py heal` $\rightarrow$ Triggers diagnosis, patch verification, or safeguard.
  - `python src/cli.py drift <mode>` $\rightarrow$ Sets target app drift state.
  - `python src/cli.py edit "<instruction>"` $\rightarrow$ Applies live AI code modification with diff confirmation.
  - `python src/cli.py ask "<query>"` $\rightarrow$ Queries RAG assistant.

### 7. Target Application Server (`target-app/server.py`)
- Python multi-threaded HTTP server running on port `3001`.
- Exposes REST endpoints:
  - `GET /`: Renders `views/index.html` with dynamic template substitutions based on active mutation.
  - `POST /api/drift`: Dynamically switches application behavior to any of the 23 mutation scenarios.
  - `POST /api/export-pdf`: Simulates backend report exports (returns 200, 500, 403, timeouts, or corrupted payloads).
  - `POST /api/run-test`: Executes test runner from localhost.
  - `POST /api/heal`: Executes healing agent from localhost.
  - `GET /dashboard.html`: Serves rich dark-mode QC demo control panel.

---

## 5. End-to-End Execution Workflows

### Master System Architecture

```mermaid
flowchart TD
    Spec["Plain-English Feature Spec<br/>(specs/leaderboard_spec.md)"] --> Generator["AI Spec-to-Test Generator<br/>(src/generator.py)"]
    Generator --> TestFile["Playwright Test Suite<br/>(tests/test_leaderboard.py)"]
    
    TestFile --> Runner["Playwright Test Runner<br/>(src/runner.py)"]
    TargetApp["Live Target App<br/>(http://localhost:3001)"] <--> Runner
    
    Runner -->|Passes| GreenLog["Verified Execution Log<br/>(artifacts/runs/)"]
    Runner -->|Fails| Diagnostics["Self-Healing Diagnostic Engine<br/>(src/selfHealer.py)"]
    
    subgraph DiagnosticLoop["AI Diagnostic & Safeguard Enforcement"]
        Diagnostics --> Context["Aggregate Context:<br/>• Spec Requirements<br/>• Full DOM Snapshot<br/>• Error Traceback<br/>• Failure Screenshot"]
        Context --> LLM["Multimodal LLM / Heuristic Classifier<br/>(meta/llama-3.2-11b-vision-instruct)"]
        LLM --> Decision{"Classification &<br/>Confidence Score?"}
        
        Decision -->|"GENUINE_BUG or<br/>Confidence < 80%"| Safeguard["Human Review Safeguard<br/>(Declines Patch, Escalates)"]
        Decision -->|"SELECTOR / ASSERTION DRIFT<br/>& Confidence >= 80%"| CandidatePatch["Generate Candidate Code Patch"]
    end
    
    CandidatePatch --> LiveVerify["Execute Live Verification Test<br/>(runner.run_test_suite())"]
    
    LiveVerify -->|Tests Pass| CommitPatch["Accept Patch & Commit Audit<br/>(artifacts/repairs/ & AUDIT_LOG.md)"]
    LiveVerify -->|Tests Still Fail| Rollback["Immediate Rollback to Baseline<br/>(Safe Failure State)"]
    
    Safeguard --> AuditReport["Visual Incident Audit Report<br/>(before.png + error details)"]
```

---

## 6. Drift Modes & 23-Scenario Mutation Benchmark

Sentinel was benchmarked across **23 real, distinct mutation scenarios** running against live application logic.

### Benchmark Summary Metrics
- **Total Scenarios Evaluated**: 23
- **Heal Precision**: **`100.0%`** (10/10 committed patches were correct; 10 of 14 candidate patches were correct, 4 were discarded by live verification)
- **Cosmetic Drift Healing Rate**: **`90.9%`** (10 / 11 cosmetic scenarios healed; 1 compound drift safely rolled back)
- **False-Heal Rate & Safeguard Enforcement**: **`0.0%`** (0/8 bad patches committed; 4 real bugs blocked by the classifier, 3 rolled back by live verification, 1 (BUG_SERVER_TIMEOUT) not detected by the test because the client tolerates the delay)
- **Pass-through / Robust Locators**: 4 scenarios passed without repair needed, confirming Playwright ID locators remain resilient across structural DOM nesting and minor latency.
- **Offline Mode Baseline**: In offline mode without LLM keys: 23 scenarios, 0 true heals (0/11), 0 false heals (0/8), 6 of 8 real bugs held directly (75.0%), precision N/A with 0 patches attempted. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.

### Full Empirical Results Matrix

| # | Scenario ID | Category | Target App Mutation Behavior | Ground Truth | AI Classification & Confidence | Sentinel Action & Safeguard | Verification Result |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | **`NORMAL`** | Baseline | Stable baseline UI locators & server API | Baseline | None (Clean run) | None needed (Baseline pass) | **PASSED** (Baseline) |
| 02 | **`SELECTOR_RENAME_BTN`** | Selector Drift | Renamed button ID `#refresh-btn` $\rightarrow$ `#reload-leaderboard-btn` | Cosmetic Drift | `SELECTOR_DRIFT` (80.0%) | **Auto-Patched**: Updated element selector | **PASSED** (Verified) |
| 03 | **`SELECTOR_PREFIX_CHANGE`** | Selector Drift | Prefix changed `#refresh-btn` $\rightarrow$ `#btn-refresh-stats` | Cosmetic Drift | `SELECTOR_DRIFT` (80.0%) | **Auto-Patched**: Updated element selector | **PASSED** (Verified) |
| 04 | **`SELECTOR_RENAME_CONTAINER`** | Selector Drift | Container renamed `#results-section` $\rightarrow$ `#match-results-wrapper` | Cosmetic Drift | `SELECTOR_DRIFT` (90.0%) | **Auto-Patched**: Updated element selector | **PASSED** (Verified) |
| 05 | **`SELECTOR_RENAME_BADGE`** | Selector Drift | Badge renamed `#rank-badge` $\rightarrow$ `#tier-pill` | Cosmetic Drift | `SELECTOR_DRIFT` (90.0%) | **Auto-Patched**: Updated element selector | **PASSED** (Verified) |
| 06 | **`SELECTOR_RENAME_EXPORT`** | Selector Drift | Export button renamed `#export-btn` $\rightarrow$ `#download-report-btn` | Cosmetic Drift | `SELECTOR_DRIFT` (90.0%) | **Auto-Patched**: Updated element selector | **PASSED** (Verified) |
| 07 | **`MOVED_ELEMENT_NESTED`** | DOM Structure | `#rank-badge` nested in sub-card div wrapper | DOM Reorg | None (Locator robust) | None needed (ID locator resilient) | **PASSED** (Resilient) |
| 08 | **`MOVED_BUTTON_CONTAINER`** | DOM Structure | `#export-btn` nested in action toolbar wrapper | DOM Reorg | None (Locator robust) | None needed (ID locator resilient) | **PASSED** (Resilient) |
| 09 | **`SLOW_INITIAL_RENDER`** | Timing | Page response delayed by 1200ms | Latency | None (Within timeout) | None needed (Within 3000ms window) | **PASSED** (Tolerant) |
| 10 | **`COPY_RANK_TIER_LABEL`** | Assertion Drift | Badge text changed `"Top Rank: Elite"` $\rightarrow$ `"Current Tier: Elite"` | Cosmetic Drift | `ASSERTION_DRIFT` (90.0%) | **Auto-Patched**: Updated expected text | **PASSED** (Verified) |
| 11 | **`COPY_CASE_CHANGE`** | Assertion Drift | Uppercase formatting `"TOP RANK: ELITE"` | Cosmetic Drift | `ASSERTION_DRIFT` (90.0%) | **Auto-Patched**: Updated expected text | **PASSED** (Verified) |
| 12 | **`COPY_PUNCTUATION_CHANGE`** | Assertion Drift | Separator updated `"Top Rank - Elite"` | Cosmetic Drift | `ASSERTION_DRIFT` (90.0%) | **Auto-Patched**: Updated expected text | **PASSED** (Verified) |
| 13 | **`COPY_EXPANDED_PHRASE`** | Assertion Drift | Extended copy `"Season Top Rank: Elite Tier"` | Cosmetic Drift | `ASSERTION_DRIFT` (90.0%) | **Auto-Patched**: Updated expected text | **PASSED** (Verified) |
| 14 | **`COPY_LOCALIZED_SYNONYM`** | Assertion Drift | Alternate wording `"Highest Rank: Elite"` | Cosmetic Drift | `SELECTOR_DRIFT` (90.0%) | **Auto-Patched**: Updated expected text | **PASSED** (Verified) |
| 15 | **`BUG_HTTP_500`** | Backend Bug | `/api/export-pdf` returns `HTTP 500 Internal Server Error` | Real Bug | `GENUINE_BUG` (90.0%) | **Safeguard Triggered**: Declined auto-patch | **HELD** (Human Review) |
| 16 | **`BUG_HTTP_403_FORBIDDEN`** | Backend Bug | `/api/export-pdf` returns `HTTP 403 Forbidden` | Real Bug | `GENUINE_BUG` (90.0%) | **Safeguard Triggered**: Declined auto-patch | **HELD** (Human Review) |
| 17 | **`BUG_MALFORMED_JSON`** | Backend Bug | `/api/export-pdf` returns corrupted non-JSON stream | Real Bug | `GENUINE_BUG` (80.0%) | **Safeguard Triggered**: Declined auto-patch | **HELD** (Human Review) |
| 18 | **`BUG_SERVER_TIMEOUT`** | Backend Bug | `/api/export-pdf` delays 4.0s (exceeds client timeout) | Real Bug | None (Async tolerance) | Baseline / Locator Robust | **PASSED** (Timing pass) |
| 19 | **`BUG_MISSING_PAYLOAD_FIELD`** | Backend Bug | `/api/export-pdf` returns `{}` missing `pdf_url` | Real Bug | `ASSERTION_DRIFT` (80.0%) | Patch Verification Failed (Rolled Back) | **SAFE** (Rollback held) |
| 20 | **`INTERMITTENT_EXPORT_FAILURE`** | Backend Bug | First call returns HTTP 500 transient failure | Real Bug | `GENUINE_BUG` (80.0%) | **Safeguard Triggered**: Declined auto-patch | **HELD** (Human Review) |
| 21 | **`COMPOUND_SELECTOR_AND_500`** | Compound Drift | Renamed button `#refresh-btn` AND HTTP 500 export failure | Real Bug | `SELECTOR_DRIFT` (80.0%) | Patch Verification Failed (Rolled Back) | **SAFE** (Rollback held) |
| 22 | **`COMPOUND_COPY_AND_403`** | Compound Drift | Changed tier copy AND HTTP 403 Forbidden | Real Bug | `ASSERTION_DRIFT` (80.0%) | Patch Verification Failed (Rolled Back) | **SAFE** (Rollback held) |
| 23 | **`COMPOUND_SELECTOR_AND_COPY`** | Compound Drift | Renamed `#refresh-btn` AND changed tier copy | Cosmetic Drift | `SELECTOR_DRIFT` (80.0%) | Patch Verification Failed (Rolled Back) | **SAFE** (Rollback held) |

---

## 7. Confidence Scoring & The Double-Layer Safety Net

### How Confidence is Evaluated
As documented in [`docs/confidence-scoring.md`](confidence-scoring.md):
1. **Primary AI Pipeline**: The confidence score is **purely LLM-self-reported** (the model outputs `"confidence": 0.90` in its JSON payload). It does **not** perform an algorithmic Tree Edit Distance or string metric in code.
2. **Offline Fallback Pipeline**: Uses static constants (`0.95` for backend 500/403/timeout, `0.92` for selector drift, `0.90` for copy drift, `0.70` for ambiguous errors). Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys. (Note: the timeout keyword rule matches first in Playwright failure summaries, so SELECTOR_DRIFT and ASSERTION_DRIFT heuristic rules are not reachable offline in the current implementation).
3. **Threshold Check**: Must meet or exceed `CONFIDENCE_THRESHOLD = 0.80` (80%).

### Why Sentinel's Safety Does Not Rely on LLM Trust
Because LLM self-reported confidence can be miscalibrated, Sentinel employs a **Double-Layer Safety Net**:
1. **Layer 1: Category & Confidence Filter**: If the failure is classified as `GENUINE_BUG` or confidence is `< 80%`, the patch is declined before code is ever touched.
2. **Layer 2: Live Execution Verification & Rollback**: Even if the LLM is 90% confident, Sentinel writes the patch to a staging buffer and **re-executes the actual Playwright test suite against the running app**. If the test fails, Sentinel **immediately rolls back to the clean baseline**. A patch is only permanently committed if the test suite turns green.

---

## 8. Explicit System Boundaries: What Sentinel DOES NOT Do

To maintain integrity when explaining Sentinel to stakeholders or prompting AI assistants, keep these explicit boundaries in mind:

| What Sentinel DOES | What Sentinel DOES NOT Do (Non-Goals) |
| :--- | :--- |
| ✅ Auto-repairs broken element selectors (IDs, button labels). | ❌ **Does NOT alter feature specs or expected business outcomes**. It repairs tests to match specs, not specs to match bugs. |
| ✅ Auto-updates minor copy changes that match UI intent. | ❌ **Does NOT blindly suppress failures**. If an API fails, it does not comment out an assertion or catch exceptions silently. |
| ✅ Distinguishes cosmetic drift from backend crashes. | ❌ **Does NOT auto-patch backend code or application servers**. It only patches test locators and assertions. |
| ✅ Enforces live verification before accepting any edit. | ❌ **Does NOT accept unverified edits**. If a proposed repair fails execution, it is rolled back instantly. |
| ✅ Records visual before/after screenshots and unified diffs. | ❌ **Does NOT disguise LLM confidence as a mathematical metric**. It is explicitly acknowledged as self-reported. |
| ✅ Runs headlessly in CI/CD (GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server). | ❌ **Does NOT require proprietary cloud runners or vendor lock-in**. Runs locally on standard Python + Playwright. |

---

## 9. CLI Command Reference & Usage

```bash
# 1. Spec-to-Test Generation
python src/cli.py generate
# Generates tests/test_leaderboard.py from specs/leaderboard_spec.md

# 2. Automated Test Execution
python src/cli.py run
# Runs headless Playwright suite, logs artifacts/runs/run_<timestamp>.json (exits 1 on failure)

# 3. Simulate UI / Backend Drift
python src/cli.py drift NORMAL
python src/cli.py drift SELECTOR_DRIFT
python src/cli.py drift ASSERTION_DRIFT
python src/cli.py drift REAL_BUG
python src/cli.py drift BUG_HTTP_403_FORBIDDEN
# Sets target app drift state dynamically

# 4. Trigger Self-Healing Diagnostic Engine
python src/cli.py heal
# Analyzes last failed run, checks safeguard, applies verified patch or escalates

# 5. Live AI Code Editor (Unscripted Drift Injection)
python src/cli.py edit "In index.html, change {{RANK_BADGE_TEXT}} to 'Season 1: Grandmaster'"
# Interactively previews unified diff, requests [y/N] confirmation, backs up to artifacts/edits/
# Optional: --file <view-file>, -y (auto-confirm)

# 6. Natural Language RAG Assistant
python src/cli.py ask "What happened during the last failed test run?"
python src/cli.py ask "Which selectors are validated in the leaderboard spec?"

# 7. Execute Full 23-Scenario Mutation Benchmark
python scripts/benchmark_runner.py
# Runs end-to-end benchmark across all 23 scenarios and outputs metrics
```

---

## 10. Presentation Deck Outline (Slide-by-Slide PPT Guide)

Use this slide outline to create a high-impact presentation deck for management, technical leads, or QC teams:

### Slide 1: Title & Hook
- **Title**: Sentinel: Self-Healing AI Test-Automation Agent for Live-Ops QC
- **Subtitle**: Eliminating the Maintenance Tax in Continuous Live-Service Delivery
- **Presenter**: QA Automation & QC Engineering

### Slide 2: The Core Problem (The Maintenance Tax)
- **Bullet 1**: Live-service applications undergo constant cosmetic UI changes (renamed button IDs, updated copy, refactored DOM).
- **Bullet 2**: Traditional automated test suites break continuously on these harmless changes.
- **Bullet 3**: Result: High false-positive rates, alert fatigue, blocked release pipelines, and dozens of manual test fixes per engineer weekly.

### Slide 3: The Solution — Sentinel's Three Pillars
- **Pillar 1: Spec-to-Test Generation**: Plain-English requirements $\rightarrow$ clean Playwright suites.
- **Pillar 2: Autonomous Cosmetic Healing**: Automatic detection and repair of renamed locators and copy drift.
- **Pillar 3: The Human Review Safeguard**: Refusal to apply unverified fixes to genuine backend regressions.

### Slide 4: System Architecture & Workflow
- *Embed the Mermaid architecture diagram from Section 5.*
- Key highlight: Spec $\rightarrow$ Playwright Runner $\rightarrow$ Multimodal LLM Diagnosis $\rightarrow$ Live Re-Verification $\rightarrow$ Visual Audit Trail.

### Slide 5: The Diagnostic Engine & Double-Layer Safety Net
- **Layer 1: Multimodal AI Classification**: Evaluates DOM snapshot, error log, and spec ($\ge 80\%$ confidence required).
- **Layer 2: Live Execution Verification**: Candidate patches are executed against the running target app. If the test fails, Sentinel rolls back immediately.
- **Transparency Note**: Diagnostic confidence is LLM-self-reported, backed by deterministic test execution verification.

### Slide 6: Benchmark Results Across 23 Mutation Scenarios
- **Key Metrics Highlight (measured with LLM keys configured)**:
  - **`100.0%` Heal Precision**: 10/10 committed patches were correct; 10 of 14 candidate patches were correct, 4 were discarded by live verification.
  - **`0.0%` False-Heal Rate**: 0/8 bad patches committed; 4 real bugs blocked by the classifier, 3 rolled back by live verification, 1 (BUG_SERVER_TIMEOUT) not detected by the test because the client tolerates the delay.
  - **Offline Mode**: Blocks failures and routes them to human review; does not heal.

### Slide 7: Live Target App & Demo Walkthrough
- Showcase `target-app/views/dashboard.html` with real-time drift toggles and visual repair before/after diffs.
- Demonstrate unscripted live mutations via `python src/cli.py edit` — proving Sentinel heals real, spontaneous code changes (not just pre-scripted modes).
- Showcase `artifacts/AUDIT_LOG.md` master traceability index and automated backups in `artifacts/edits/`.

### Slide 8: CI/CD Integration & Enterprise Readiness
- CI/CD Automation: GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server.
- Zero vendor lock-in: Built on standard Python, Playwright, Pytest, and REST.

### Slide 9: Roadmap & Future Innovations
- Moving from LLM-self-reported confidence to a multi-factor hybrid score (Tree Edit Distance + Vector Embeddings + Logprob Calibration).
- Multi-browser cross-platform self-healing (Chromium, Firefox, WebKit).

### Slide 10: Conclusion & Q&A
- Summary: Sentinel turns test automation from a brittle maintenance burden into a self-resilient, trustworthy live-ops safety net.

---

## 11. AI Assistant Context Primer

> **How to use this**: Copy-paste the block below into any conversation with Claude, ChatGPT, or Gemini when you want the AI assistant to work on or extend Sentinel with full context.

```text
You are an expert pair-programmer assisting with the "Sentinel" codebase.
Sentinel is a self-healing AI test-automation agent for live-ops QC web applications.

KEY CONTEXT:
1. Core Tech Stack: Python 3.11+, Playwright (Chromium headless), Pytest, OpenAI SDK (NVIDIA NIM meta/llama-3.2-11b-vision-instruct, fallback to Gemini gemini-2.5-flash).
2. Key Files:
   - specs/leaderboard_spec.md: The plain-English spec for the live target app.
   - src/generator.py: Converts specs to Playwright tests in tests/test_leaderboard.py.
   - src/runner.py: Headless test runner, captures DOM snapshots and before/after screenshots to artifacts/runs/.
   - src/selfHealer.py: AI diagnostic agent (SELECTOR_DRIFT, ASSERTION_DRIFT, GENUINE_BUG). Threshold is 80%. Validates candidate patches by re-executing runner.run_test_suite() and rolling back if tests fail.
   - src/ragEngine.py: TF-IDF keyword retrieval over specs, tests and run artifacts.
   - src/cli.py: Main CLI tool (generate, run, heal, drift, ask).
   - target-app/server.py: Multi-threaded Python HTTP server simulating 23 drift mutation scenarios.
   - scripts/benchmark_runner.py: Harness executing 23 mutation scenarios (100% precision, 0% false heals, measured with LLM keys configured; offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys).
   - .github/workflows/test.yml: CI/CD test runner workflow (GitHub Actions workflow runs on push/PR; the Jenkinsfile is written and reviewed but not yet run on a live Jenkins server).
3. Critical Operational Rules:
   - Does not suppress genuine bugs. If backend returns 500, 403, or timeout, Sentinel triggers Human Review Safeguard.
   - Confidence scoring is LLM-self-reported (not an algorithmic metric); offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys. Safety is guaranteed by live test verification rollback.
   - Preserves conventional commit hygiene.
```
