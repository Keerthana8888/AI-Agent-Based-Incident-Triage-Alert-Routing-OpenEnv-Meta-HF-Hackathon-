# 🚨 Incident Triage & Alert Routing — OpenEnv

> **Meta × Hugging Face AI Hackathon | Round 1**  
> An OpenEnv environment for training AI agents to triage production incidents like a senior SRE.

---

## Environment Description

This environment simulates the real-world job of a **Site Reliability Engineer (SRE)** who receives a flood of production alerts and must:

1. Identify the **root cause** from a set of alerts
2. Assign the correct **severity level** (P1–P4)
3. **Route** the incident to the correct on-call team (SRE, Database, Network, or App)
4. *(Hard task only)* **Suppress noise alerts** (flapping/self-resolving false positives)

Every tech company faces alert fatigue. PagerDuty and OpsGenie are billion-dollar products built around this exact problem. Reducing Mean Time To Detection (MTTD) by even 5 minutes has enormous operational value.

---

## Action Space

```python
class TriageAction(BaseModel):
    severity:   Literal['P1', 'P2', 'P3', 'P4']  # Incident severity
    team:       Literal['sre', 'database', 'network', 'app']  # On-call team
    root_cause: str        # Free-text explanation of the root cause
    suppressed: List[str]  # Alert IDs believed to be noise (task_hard only)
```

| Field | Description |
|---|---|
| `severity` | **P1** = Critical (revenue impact), **P2** = High (users affected), **P3** = Medium (degraded), **P4** = Low (informational) |
| `team` | **sre** = infrastructure/capacity, **database** = DB/connections, **network** = latency/DNS, **app** = application bugs |
| `root_cause` | One-sentence explanation. Graded by keyword match against ground truth. |
| `suppressed` | Alert IDs the agent thinks are noise. Only scored in `task_hard`. |

---

## Observation Space

```python
class AlertObservation(BaseModel):
    alerts:       List[Alert]       # Production alerts the agent can see
    services_map: Dict[str, str]    # service -> responsible team mapping
    step:         int               # Current step in the episode
    max_steps:    int               # Maximum steps allowed
    task_id:      str               # Active task identifier
```

Each `Alert` contains: `alert_id`, `service`, `metric`, `value`, `threshold`, `duration_s`.  
The `is_noise` field is **hidden from the agent** — it is only used by the grader.

---

## Reward Function

Rewards are shaped so **partial progress always returns a non-zero signal**.

### task_easy
| Component | Weight | Condition |
|---|---|---|
| Severity correct | 0.50 | `action.severity == ground_truth.severity` |
| Team correct | 0.50 | `action.team == ground_truth.team` |

### task_medium
| Component | Weight | Condition |
|---|---|---|
| Severity correct | 0.35 | exact match |
| Team correct | 0.35 | exact match |
| Root cause | 0.30 | keyword match score (0.0–1.0) |

### task_hard
| Component | Weight | Condition |
|---|---|---|
| Noise suppression | 0.20 | F1 of correctly suppressed noise alerts |
| Severity correct | 0.25 | exact match |
| Team correct | 0.25 | exact match |
| Root cause | 0.30 | keyword match score |
| Over-suppression penalty | −0.20 per real alert wrongly suppressed | |

---

## Task Descriptions

### 🟢 task_easy — Single Alert, Obvious Root Cause
- **Scenario:** 1 alert, randomly chosen from 4 variants (one per team)
- **Examples:** CPU spike → SRE, DB timeout → Database, p99 latency → Network, 5xx rate → App
- **Grader:** severity(0.5) + team(0.5)
- **Expected score (frontier model):** 0.9–1.0
- **Expected score (weak model):** 0.4–0.6

### 🟠 task_medium — 3 Correlated Alerts, Identify Root Cause
- **Scenario:** 3 alerts, randomly chosen from 4 scenario sets
- **Examples:** DB timeout + 5xx + latency → database overload; DNS errors + latency + 5xx → network partition
- **Grader:** severity(0.35) + team(0.35) + root_cause(0.30)
- **Expected score (frontier model):** 0.5–0.75
- **Expected score (weak model):** 0.2–0.4

### 🔥 task_hard — 10–15 Alerts, Suppress Noise & Escalate
- **Scenario:** 6 real alerts (database outage root cause) + 5 noise alerts (short-duration, barely-over-threshold, shuffled)
- **Agent must:** suppress noise, identify root cause (database), assign P1, route to Database team
- **Grader:** noise(0.20) + severity(0.25) + team(0.25) + root_cause(0.30) − over-suppress penalty
- **Expected score (frontier model):** 0.2–0.45
- **Expected score (weak model):** 0.05–0.15

---

## Setup Instructions

### 1. Clone and install
```bash
git clone <your-repo-url>
cd incident-triage-env
pip install -r requirements.txt
```

### 2. Configure environment variables (optional — for LLM agent)
```bash
cp .env.example .env
# Edit .env with your API keys
source .env
```

### 3. Start the FastAPI backend
```bash
cd backend
uvicorn server:app --reload --port 7860
```

### 4. Start the Streamlit UI
```bash
# In a new terminal
cd frontend
streamlit run app.py
# Opens at http://localhost:8501
```

### 5. Run the inference baseline agent
```bash
cd backend
python inference.py
# Requires API_BASE_URL, MODEL_NAME, HF_TOKEN to be set
```

### 6. Validate OpenEnv spec
```bash
openenv validate
```

### 7. Build and test Docker
```bash
docker build -t incident-triage-env .
docker run -p 7860:7860 incident-triage-env
curl -X POST http://localhost:7860/health
```

---

## Baseline Scores

Scores from running `inference.py` with `meta-llama/Llama-3.3-70B-Instruct` via HF inference router:

| Task | Score | Notes |
|---|---|---|
| `task_easy` | ~0.95 | Near-perfect on single alert |
| `task_medium` | ~0.63 | Good severity+team, partial root cause |
| `task_hard` | ~0.31 | Noise suppression is the main challenge |

---

## Project Structure

```
incident-triage-env/
├── backend/
│   ├── models.py         ← Pydantic v2: Alert, AlertObservation, TriageAction, TriageReward
│   ├── tasks.py          ← 3 task definitions (4 easy + 4 medium + 1 hard scenario), graders
│   ├── environment.py    ← OpenEnv core: reset() step() state()
│   ├── server.py         ← FastAPI: /reset /step /state /tasks /health
│   └── inference.py      ← LLM baseline agent (OpenAI client, reads env vars)
├── frontend/
│   └── app.py            ← Streamlit UI: alerts, routing table, score breakdown, history
├── openenv.yaml          ← OpenEnv spec metadata
├── Dockerfile            ← Container for Hugging Face Spaces deployment
├── requirements.txt      ← Pinned Python dependencies
├── .env.example          ← Environment variable template
└── README.md             ← This file
```

---

## Deployment (Hugging Face Spaces)

```bash
# Login to HF
huggingface-cli login

# Create a new Space (Docker type) and push
git remote add space https://huggingface.co/spaces/<your-username>/incident-triage-env
git push space main
```

Set these secrets in your HF Space settings:
- `API_BASE_URL`
- `MODEL_NAME`  
- `HF_TOKEN`

The Space will auto-build from the Dockerfile and expose port 7860.

---

## Deployment Link

🔗 **Live HF Space:** `https://<your-username>.hf.space`

---

*Built for the Meta × Hugging Face AI Hackathon, Round 1. Domain: Incident Triage & Alert Routing.*
