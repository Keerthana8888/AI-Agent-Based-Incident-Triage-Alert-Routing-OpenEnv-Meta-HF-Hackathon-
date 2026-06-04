"""
models.py — Pydantic v2 data models for Incident Triage (Module 1)
Defines the typed contracts between environment, agent, and grader.
"""

from pydantic import BaseModel
from typing import List, Dict, Literal


class Alert(BaseModel):
    """A single production monitoring alert sent to the agent."""
    alert_id: str
    service: str          # e.g. 'api-server', 'postgres-primary'
    metric: str           # e.g. 'cpu_utilisation', 'db_query_time_ms'
    value: float          # current metric value
    threshold: float      # threshold that triggered the alert
    duration_s: int       # how long the alert has been firing (seconds)
    is_noise: bool = False  # HIDDEN from agent — used by grader only


class AlertObservation(BaseModel):
    """Everything the agent can observe at each step."""
    alerts: List[Alert]
    services_map: Dict[str, str]   # service -> team mapping
    step: int
    max_steps: int
    task_id: str


class TriageAction(BaseModel):
    """The agent's response: severity + team + reasoning."""
    severity: Literal['P1', 'P2', 'P3', 'P4']
    team: Literal['sre', 'database', 'network', 'app']
    root_cause: str                # free-text explanation
    suppressed: List[str] = []     # alert_ids the agent thinks are noise (Task 3 only)


class TriageReward(BaseModel):
    """Reward signal returned after each env.step()."""
    score: float                   # 0.0 to 1.0 — main reward signal
    severity_correct: bool
    team_correct: bool
    root_cause_score: float        # 0.0 to 1.0 based on keyword match
    reason: str                    # human-readable explanation
