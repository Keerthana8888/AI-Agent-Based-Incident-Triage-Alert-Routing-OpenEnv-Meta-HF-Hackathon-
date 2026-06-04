"""
environment.py — Core OpenEnv environment (Modules 2 & 3)

Supports: task_easy | task_medium | task_hard
Easy + Medium pick a random scenario variant on each reset().
Hard generates a seeded alert set with noise.

OpenEnv contract:
  reset()  -> AlertObservation
  step()   -> (AlertObservation, float, bool, dict)
  state()  -> dict
"""

import random
from typing import Tuple, Dict, Any, Optional

from models import Alert, AlertObservation, TriageAction, TriageReward
from tasks import pick_random_task, GRADERS, SERVICES_MAP, TaskDefinition


class IncidentTriageEnv:
    MAX_STEPS = {"task_easy": 3, "task_medium": 3, "task_hard": 5}

    def __init__(self, task_id: str = "task_easy", seed: Optional[int] = None):
        if task_id not in self.MAX_STEPS:
            raise ValueError(f"Unknown task_id '{task_id}'. Supported: {list(self.MAX_STEPS)}")
        self.task_id = task_id
        self._seed   = seed
        self._task: TaskDefinition = pick_random_task(task_id, seed=seed)
        self._grader = GRADERS[task_id]
        self._step   = 0
        self._done   = False
        self._last_reward: Optional[TriageReward] = None

    # ── OpenEnv contract ────────────────────────────────────────────────────

    def reset(self) -> AlertObservation:
        """Pick a fresh random scenario and return initial observation."""
        self._task  = pick_random_task(self.task_id, seed=self._seed)
        self._step  = 0
        self._done  = False
        self._last_reward = None
        return self._make_obs()

    def step(self, action: TriageAction) -> Tuple[AlertObservation, float, bool, Dict[str, Any]]:
        if self._done:
            raise RuntimeError("Episode done — call reset() first.")

        reward_obj = self._grader(action, self._task)
        self._last_reward = reward_obj
        self._step += 1
        self._done = reward_obj.score >= 0.99 or self._step >= self.MAX_STEPS[self.task_id]

        info = {
            "final_score":      reward_obj.score,
            "severity_correct": reward_obj.severity_correct,
            "team_correct":     reward_obj.team_correct,
            "root_cause_score": reward_obj.root_cause_score,
            "reason":           reward_obj.reason,
            "step":             self._step,
            "task_id":          self.task_id,
            "scenario_label":   self._task.scenario_label,
            # For hard task: expose noise ids so UI can highlight them
            "noise_ids":        self._task.ground_truth.get("noise_ids", []),
            "ground_truth": {
                "severity": self._task.ground_truth["severity"],
                "team":     self._task.ground_truth["team"],
            },
        }
        return self._make_obs(), reward_obj.score, self._done, info

    def state(self) -> Dict[str, Any]:
        return {
            "task_id":        self.task_id,
            "scenario_label": self._task.scenario_label,
            "step":           self._step,
            "max_steps":      self.MAX_STEPS[self.task_id],
            "done":           self._done,
            "last_reward":    self._last_reward.model_dump() if self._last_reward else None,
            "alerts":         [a.model_dump() for a in self._task.alerts],
            "services_map":   SERVICES_MAP,
            "ground_truth": {
                "severity": self._task.ground_truth["severity"],
                "team":     self._task.ground_truth["team"],
            },
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _make_obs(self) -> AlertObservation:
        safe = [
            Alert(
                alert_id=a.alert_id, service=a.service,
                metric=a.metric, value=a.value,
                threshold=a.threshold, duration_s=a.duration_s,
                is_noise=False,   # hidden from agent
            )
            for a in self._task.alerts
        ]
        return AlertObservation(
            alerts=safe,
            services_map=SERVICES_MAP,
            step=self._step,
            max_steps=self.MAX_STEPS[self.task_id],
            task_id=self.task_id,
        )
