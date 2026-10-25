# CrisisSense AI — GitHub Repository Guide & Tech Stack Reference

This guide gives you everything you need to set up, describe, and explain your GitHub repository with complete technical authority.

---

## 1. 📌 GitHub Repository Details (Copy & Paste Ready)

### Repository Name:
```text
CrisisSense-AI
```

### GitHub "About" Description (Under 350 chars):
```text
Continuous online Bayesian decision-support engine for municipal duty officers during the first 10 minutes of an emerging urban crisis. Balances detection delay against cry-wolf false alarms using optimal stopping, causal foresight, and OASIS CAP v1.2 alerts.
```

### GitHub Topics / Tags:
```text
bayesian-filter, decision-support, disaster-response, emergency-management, optimal-stopping, causal-inference, cap-v12, changepoint-detection, stream-processing, streamlit, fastapi, python
```

---

## 2. 🌐 Complete Language & Technology Stack Breakdown

| Architectural Layer | Language | Framework / Tool | Exact Role & Location |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | **Python 3.10+** + **HTML5/CSS3** | `Streamlit`, `Plotly Graph Objects` | Interactive Operations Cockpit, time scrubber slider, Twin Test dual pane, Causal Sandbox, and hover tooltips (`.hover-term`). Defined in `dashboard/app.py`. |
| **EOC Authentication** | **Python 3.10+** | `Streamlit`, Custom CSS3 | Municipal Emergency Operations Center login portal with 1-click role profiles (`Duty Officer`, `Commander`, `Auditor`). Defined in `dashboard/login.py`. |
| **Backend REST & SSE API** | **Python 3.10+** | `FastAPI`, `Uvicorn`, `sse-starlette` | High-throughput asynchronous endpoints with Server-Sent Events (`GET /stream`) for minute-by-minute telemetry push. Defined in `src/api/server.py`. |
| **Data Validation & Schemas** | **Python 3.10+** | `Pydantic v2` | Strict data contracts for `StreamEvent`, `MinuteStatePayload`, and `CAPAlert`. Defined in `src/schemas.py`. |
| **Probabilistic Core & Math** | **Python 3.10+** | `NumPy`, `SciPy` (Tensor Algebra) | Discrete 128-state Bayesian forward filter, Kronecker transition matrix $T$, Dong et al. dependence clustering, and online temperature calibration. Zero LLM dependency in the decision loop (<5ms execution). Defined in `src/engine/`. |
| **Optimal Stopping & Utility** | **Python 3.10+** | Pure Python + `NumPy` | Asymmetric cost matrix, Shiryaev change detection, cry-wolf fatigue $W(F_c)$, and 200-draw Monte Carlo lookahead. Defined in `src/engine/decision.py`. |
| **Causal Foresight** | **Python 3.10+** | `SciPy` (Gamma Distributions) | Physical propagation DAG with 80% confidence arrival windows and counterfactual `do()` clamping API. Defined in `src/engine/foresight.py`. |
| **Emergency Standards** | **XML** & **JSON** | OASIS / WMO CAP v1.2 Standard | Standardized digital alerts for emergency sirens, radio, and mobile gateways marked strictly as `status="Exercise"`. Defined in `src/engine/cap.py`. |
| **Event Simulator & Chaos Suite**| **Python 3.10+** | Pure Python standard library | Deterministic 30-minute episode generator, twin pairs, arrival shuffles, duplicate floods, and gateway dropouts. Defined in `src/simulator/`. |
| **Automated Testing Suite** | **Python 3.10+** | `pytest` | 12/12 automated acceptance tests (T1–T12) enforcing mathematical guarantees in 1.6 seconds. Defined in `tests/test_acceptance_t1_t12.py`. |
| **Benchmark & Validation** | **Python 3.10+** | `pandas`, `scikit-learn` | 500-episode Monte Carlo evaluation against 3 baselines and 5-way ablations. Defined in `src/evaluation/`. |

---

## 3. 🚀 Quick Commands to Push to GitHub

If you are publishing this project to your GitHub account:

```bash
# 1. Initialize git (if not already done)
git init

# 2. Stage all files
git add .

# 3. Commit the production codebase
git commit -m "feat: complete production CrisisSense AI v3.0 with Bayesian filter, UI tooltips, and CAP v1.2"

# 4. Set branch to main
git branch -M main

# 5. Add your remote repository URL (replace with your actual GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/CrisisSense-AI.git

# 6. Push to GitHub
git push -u origin main
```
