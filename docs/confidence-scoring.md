# Confidence Scoring Methodology & Technical Transparency

This document details the exact mechanism by which diagnostic confidence scores are generated, evaluated, and enforced within Sentinel's self-healing engine ([`src/selfHealer.py`](../src/selfHealer.py)).

---

## 🔍 Plain Statement on Current Methodology

> [!WARNING]
> **Current Classification**: The confidence score in Sentinel's primary AI diagnostic pipeline is **purely LLM-self-reported**, with an offline fallback to **static rule-based constants**. Confidence is LLM self-reported, not an algorithmic metric. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.
>
> It does **NOT** currently compute a mathematical DOM tree-edit distance, Levenshtein string distance, or embedding similarity vector in the Python code (the RAG engine uses in-memory TF-IDF keyword retrieval over specs, tests and run artifacts).

---

## 📐 How Confidence is Computed (Code Walkthrough)

The self-healing diagnostic pipeline runs in two distinct modes depending on environment configuration:

### 1. Primary AI Diagnostic Path (API Enabled)

When an AI provider API key is present (`NVIDIA_API_KEY` or `GEMINI_API_KEY`), [`src/selfHealer.py`](../src/selfHealer.py) sends a structured prompt to the multimodal LLM:

```python
# src/selfHealer.py (lines 120-137)
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
  ...
}
"""
```

The confidence score is parsed directly from the model's textual JSON response:
```python
# src/selfHealer.py (line 272)
confidence = float(diagnosis.get("confidence", 0.0))
```

- **Nature of the Metric**: The value (e.g., `0.90` or `0.80`) is generated token-by-token by the language model reflecting its internal parametric text generation.
- **No Algorithmic Normalization**: There is no statistical calibration layer, temperature scaling, or DOM diff metric applied to this number.

### 2. Offline Fallback Heuristic Path (No API / Failure Fallback)

If the AI API call times out, encounters rate limits, or is unconfigured, [`src/selfHealer.py`](../src/selfHealer.py) falls back to pattern-matching heuristics with **hardcoded static constants**. Offline mode blocks failures and routes them to human review; it does not heal. Healing requires the LLM keys.

| Matched Pattern in Error Summary / DOM | Assigned Classification | Hardcoded Confidence | Offline Reachability |
| :--- | :--- | :--- | :--- |
| HTTP Status `500`, `403`, `timeout`, `SyntaxError`, or `Error exporting report` | `GENUINE_BUG` | `0.95` (95%) | Active (matches Playwright timeout error text first) |
| Missing locator in error + Renamed ID candidate detected in DOM | `SELECTOR_DRIFT` | `0.92` (92%) | not reachable offline in the current implementation (the timeout keyword rule matches first). |
| Text assertion mismatch in error + Alternate copy candidate in DOM | `ASSERTION_DRIFT` | `0.90` (90%) | not reachable offline in the current implementation (the timeout keyword rule matches first). |
| Ambiguous / Unrecognized error pattern | `GENUINE_BUG` | `0.70` (70%) | Active |

---

## 🚦 Safeguard Threshold Enforcement

Sentinel defines a strict threshold in [`src/config.py`](../src/config.py):
```python
CONFIDENCE_THRESHOLD = 0.80  # 80% minimum confidence
```

In [`src/selfHealer.py`](../src/selfHealer.py), auto-patching is strictly conditional:
```python
if classification in ["SELECTOR_DRIFT", "ASSERTION_DRIFT"] and confidence >= CONFIDENCE_THRESHOLD:
    # Generate candidate code patch and re-verify
    ...
else:
    # Trigger Human Review Safeguard; decline code modification
    ...
```

If the classification is `GENUINE_BUG` **or** if `confidence < 0.80`, Sentinel refuses to touch the test file and logs a `HUMAN_REVIEW_REQUIRED` audit entry.

---

## ⚠️ Known Limitations of Purely Self-Reported Confidence

1. **Miscalibration Tendency**: Large language models are susceptible to overconfidence or heuristic clustering (frequently returning round numbers like `0.80` or `0.90` regardless of edge-case subtleties).
2. **Lack of Deterministic Reproducibility**: Different foundation models or slight prompt variations can produce varying confidence values for the exact same DOM failure state.
3. **Absence of Ground-Truth Metric Distance**: A self-reported score cannot tell you how many DOM hops or character edits separate the old element from the candidate replacement.

---

## 🛡️ Sentinel's Real Operational Safeguard: The Verification Loop

Given that LLM-self-reported confidence is not an absolute mathematical guarantee, **why did Sentinel achieve 100.0% Heal Precision (10/10 permanent repairs verified) and 0.0% False-Heal Rate (0/8 real bugs patched) in empirical testing (measured with LLM keys configured)?**

Because Sentinel **does not rely on the confidence score alone**. The operational safety net is the **Post-Patch Verification Loop**:

```
┌─────────────────────────────────┐
│ LLM Proposes Candidate Patch    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Write Candidate Patch to Test   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Re-Run Full Playwright Suite    │
│ (src/runner.py)                 │
└────────────────┬────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
     [PASSED]          [FAILED]
        │                 │
        ▼                 ▼
 ┌──────────────┐  ┌─────────────────────────┐
 │ Keep Patch & │  │ Rollback Original Code  │
 │ Commit Audit │  │ & Escalate Incident Log │
 └──────────────┘  └─────────────────────────┘
```

1. Even if an LLM hallucinates an invalid locator with 95% confidence, Sentinel applies the patch to a staging buffer and **re-executes the test against the live target app**.
2. If the re-run fails, Sentinel **immediately rolls back the patch** to the clean baseline.
3. The patch is **only committed** if the suite actually turns green upon live execution.

---

## 🚀 Future Roadmap: Towards a Hybrid Scoring Architecture

To elevate confidence scoring from subjective LLM self-reporting to a rigorous quantitative metric, the planned architecture incorporates a multi-factor hybrid formula:

$$C_{\text{final}} = w_1 \cdot S_{\text{DOM}} + w_2 \cdot S_{\text{Semantic}} + w_3 \cdot C_{\text{LLM}}$$

Where:
- $S_{\text{DOM}}$: Deterministic Tree Edit Distance (Zhang-Shasha algorithm) and attribute Levenshtein similarity between the old selector node and the candidate node.
- $S_{\text{Semantic}}$: Cosine similarity of local text embeddings (e.g. button labels and surrounding ARIA roles).
- $C_{\text{LLM}}$: Calibrated token log-probabilities extracted from the model's classification logits rather than generated text.
