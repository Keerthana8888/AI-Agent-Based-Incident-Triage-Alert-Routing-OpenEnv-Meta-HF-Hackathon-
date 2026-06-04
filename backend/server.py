"""
server.py — FastAPI REST API (Modules 2 & 3)

Endpoints:
  GET  /health      — HF Space gate check
  GET  /tasks       — list all tasks
  POST /reset       — start episode (picks random scenario)
  POST /step        — submit TriageAction
  GET  /state       — full env state
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from models import AlertObservation, TriageAction
from environment import IncidentTriageEnv
from tasks import EASY_SCENARIOS, MEDIUM_SCENARIOS, TASK_HARD

app = FastAPI(
    title="Incident Triage Environment — Modules 2 & 3",
    description="OpenEnv: Easy + Medium + Hard tasks with random scenario variants.",
    version="3.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_env: Optional[IncidentTriageEnv] = None


class ResetRequest(BaseModel):
    task_id: str = "task_easy"
    seed: Optional[int] = None   # pass seed for reproducible scenario


class StepResponse(BaseModel):
    observation: AlertObservation
    reward: float
    done: bool
    info: dict


@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "task_id": "task_easy",
                "name": "Single Alert — Obvious Root Cause",
                "difficulty": "easy",
                "num_scenarios": len(EASY_SCENARIOS),
                "scenarios": [s.scenario_label for s in EASY_SCENARIOS],
                "grader": "severity(0.5) + team(0.5)",
                "expected_frontier": "0.9–1.0",
            },
            {
                "task_id": "task_medium",
                "name": "3 Correlated Alerts — Identify Root Cause",
                "difficulty": "medium",
                "num_scenarios": len(MEDIUM_SCENARIOS),
                "scenarios": [s.scenario_label for s in MEDIUM_SCENARIOS],
                "grader": "severity(0.35) + team(0.35) + root_cause(0.30)",
                "expected_frontier": "0.5–0.75",
            },
            {
                "task_id": "task_hard",
                "name": "10+ Noisy Alerts — Suppress & Escalate",
                "difficulty": "hard",
                "num_scenarios": 1,
                "scenarios": [TASK_HARD.scenario_label],
                "grader": "noise(0.20) + severity(0.25) + team(0.25) + root_cause(0.30)",
                "expected_frontier": "0.2–0.45",
            },
        ]
    }


@app.post("/reset", response_model=AlertObservation)
def reset(req: ResetRequest):
    global _env
    try:
        _env = IncidentTriageEnv(task_id=req.task_id, seed=req.seed)
        return _env.reset()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse)
def step(action: TriageAction):
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    try:
        obs, reward, done, info = _env.step(action)
        return StepResponse(observation=obs, reward=reward, done=done, info=info)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
def state():
    global _env
    if _env is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    return _env.state()
