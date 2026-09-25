# Sentinel: Self-Healing AI Test-Automation Agent for Live Ops & QC Workflows

**Sentinel** is an agentic, self-healing test automation CLI tool designed for QA/QC engineering workflows in live-service applications (such as AAA game titles and live match stats services). It converts plain-English feature specifications into automated Playwright test suites, observes execution failures, autonomously diagnoses and repairs selector/assertion drift, enforces a **Human Review Safeguard** on genuine backend regressions, and records visual before/after edit audit trails.

---

## ⚡Pitch: Why This Matters for Live-Service QA (

In fast-paced live-service game development, developers constantly push minor UI tweaks—renaming button IDs, updating tier label copy, or tweaking layout elements. Traditional automated test suites break immediately on these harmless cosmetic changes, triggering false-positive alerts that force QA engineers to manually fix broken locators dozens of times a week.

**Sentinel eliminates this maintenance tax:**
1. **Auto-Heals Cosmetic Drift**: Detects renamed IDs or updated copy with $\ge 80\%$ confidence, updates test locators, and verifies the fix automatically.
2. **Refuses Fake Fixes on Real Bugs**: If a backend API throws an HTTP 500 error or a feature genuinely fails, Sentinel **refuses to modify the test** and logs an actionable incident report with visual screenshots.

---

## 📊 Verification Summary Across Drift Modes

| Mode | Target App Behavior | AI Diagnostic Classification | Confidence | Sentinel Action & Safeguard | Test Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SELECTOR_DRIFT`** | Button ID changed `#refresh-btn` $\rightarrow$ `#reload-leaderboard-btn` | `SELECTOR_DRIFT` (Cosmetic) | 92.0% | **Auto-Patched**: Updated selector in test code | **PASSED** (Verified) |
| **`ASSERTION_DRIFT`** | Badge label copy changed `"Top Rank: Elite"` $\rightarrow$ `"Current Tier: Elite"` | `ASSERTION_DRIFT` (Cosmetic) | 90.0% | **Auto-Patched**: Updated assertion text in test code | **PASSED** (Verified) |
| **`REAL_BUG`** | `#export-btn` endpoint returns `HTTP 500 Internal Server Error` | `GENUINE_BUG` (Backend Fault) | 90.0% | **Safeguard Triggered**: Declined auto-patch, logged human-review note | **PASSED** (Safeguard held) |
| **`NORMAL`** | Target app running baseline UI and server logic | None (Clean run) | N/A | No repairs needed | **PASSED** (Baseline) |

---

## 🌐 Live Demo & Repository Structure

- **Target App**: Live Leaderboard & Match Stats Dashboard ([`target-app/views/index.html`](file:///d:/Projects/sentinel-qc/target-app/views/index.html))
- **Feature Spec**: Plain-English Leaderboard Spec ([`specs/leaderboard_spec.md`](file:///d:/Projects/sentinel-qc/specs/leaderboard_spec.md))
- **Visual Audit Logs**: Timestamped Before/After Screenshots & Diffs ([`artifacts/repairs/`](file:///d:/Projects/sentinel-qc/artifacts/repairs/))
- **Master Audit Index**: [`artifacts/AUDIT_LOG.md`](file:///d:/Projects/sentinel-qc/artifacts/AUDIT_LOG.md)

---

## 🏗️ Core Architecture & Workflow

```
┌─────────────────────────┐
│ Plain-English Spec      │ (specs/leaderboard_spec.md)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Spec-to-Test Generator  │ (src/generator.py)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐      Fails      ┌─────────────────────────────────┐
│ Playwright Test Runner  ├────────────────►│ Self-Healing & Diagnostic Loop  │
└───────────┬─────────────┘                 └────────────────┬────────────────┘
            │ Passes                                         │
            ▼                                                ▼
┌─────────────────────────┐                        ┌──────────────────┐
│ Verified Execution Log  │                        │ Confidence >= 80%│
└─────────────────────────┘                        │ & Drift Detected │
                                                   └─────────┬────────┘
                                               Yes           │            No (Real Bug)
                                         ┌───────────────────┴───────────────────┐
                                         ▼                                       ▼
                              ┌────────────────────┐                 ┌───────────────────────┐
                              │ Auto-Patch & Verify│                 │ Human Review Safeguard│
                              │ (artifacts/repairs)│                 │ (Declined Patch Log)  │
                              └────────────────────┘                 └───────────────────────┘
```

---

## 💻 CLI Usage

| Command | Description |
| :--- | :--- |
| `python src/cli.py generate` | Parses `specs/leaderboard_spec.md` and generates Playwright tests in `tests/test_leaderboard.py`. |
| `python src/cli.py run` | Runs Playwright suite headlessly, captures full DOM & screenshots, and logs run JSON. |
| `python src/cli.py drift <mode>` | Simulates live ops drift: `NORMAL`, `SELECTOR_DRIFT`, `ASSERTION_DRIFT`, `REAL_BUG`. |
| `python src/cli.py heal` | Runs AI visual/DOM reasoning, applies verified code patch or triggers Human Review Safeguard. |
| `python src/cli.py ask "<query>"` | Queries RAG knowledge assistant over feature specs, code, and execution run logs. |

---

## 🎯 Alignment with Ubisoft QC & QA Automation R&D

| Ubisoft Requirement | Sentinel Implementation |
| :--- | :--- |
| **Develop/integrate automation tools improving test efficiency** | Spec-to-test generator + Playwright automated execution pipeline (`src/generator.py`, `src/runner.py`). |
| **Early AI/ML-driven tools reducing manual maintenance** | Vision & LLM-backed self-healing diagnostic engine classifying UI drift (`src/selfHealer.py`). |
| **Maintain test suite integrity & avoid bad patches** | Safeguard threshold requiring $\ge 80\%$ confidence and refusing auto-patches on backend errors. |
| **Auditability & Traceability** | Visual before/after screenshot pairing and unified diffs in `artifacts/repairs/` & `AUDIT_LOG.md`. |
