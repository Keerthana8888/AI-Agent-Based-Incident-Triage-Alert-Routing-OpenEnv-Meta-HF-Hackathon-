"""
tasks.py — All task definitions + graders for Modules 2 & 3

EASY   : 1 alert — randomly chosen from 4 scenarios (one per team)
MEDIUM : 3 correlated alerts — randomly chosen from 4 root-cause scenarios
HARD   : 10–15 alerts — real + noise, must suppress noise & find root cause
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Optional
from models import Alert, TriageAction, TriageReward


# ─────────────────────────────────────────────────────────────────────────────
# SERVICES MAP
# ─────────────────────────────────────────────────────────────────────────────
SERVICES_MAP: Dict[str, str] = {
    "api-server-03":       "sre",
    "api-server-07":       "sre",
    "postgres-primary":    "database",
    "postgres-replica":    "database",
    "checkout-service":    "app",
    "payment-service":     "app",
    "load-balancer-01":    "network",
    "cdn-edge-02":         "network",
    "redis-cache-01":      "sre",
    "auth-service":        "app",
    "reporting-service":   "app",
    "dns-resolver-01":     "network",
}


# ─────────────────────────────────────────────────────────────────────────────
# TASK DEFINITION DATACLASS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TaskDefinition:
    task_id: str
    name: str
    difficulty: str
    description: str
    alerts: List[Alert]
    ground_truth: Dict
    scenario_label: str = ""   # human-readable label for UI display


# ─────────────────────────────────────────────────────────────────────────────
# EASY TASK — 4 scenarios, one per team
# ─────────────────────────────────────────────────────────────────────────────
EASY_SCENARIOS: List[TaskDefinition] = [

    TaskDefinition(
        task_id="task_easy",
        name="Single Alert — CPU Spike",
        difficulty="easy",
        scenario_label="🔴 SRE — CPU Spike",
        description="CPU utilisation on api-server-03 is 98% for 5 minutes. Route to SRE.",
        alerts=[Alert(
            alert_id="alert-001", service="api-server-03",
            metric="cpu_utilisation", value=98.0, threshold=85.0,
            duration_s=300, is_noise=False,
        )],
        ground_truth={
            "severity": "P2", "team": "sre",
            "root_cause_keywords": ["cpu", "utilisation", "spike", "high", "api-server"],
        },
    ),

    TaskDefinition(
        task_id="task_easy",
        name="Single Alert — DB Query Timeout",
        difficulty="easy",
        scenario_label="🟠 Database — Query Timeout",
        description="postgres-primary query time hit 5 200 ms (threshold 1 000 ms). Route to Database.",
        alerts=[Alert(
            alert_id="alert-001", service="postgres-primary",
            metric="db_query_time_ms", value=5200.0, threshold=1000.0,
            duration_s=180, is_noise=False,
        )],
        ground_truth={
            "severity": "P1", "team": "database",
            "root_cause_keywords": ["database", "db", "query", "timeout", "postgres", "slow"],
        },
    ),

    TaskDefinition(
        task_id="task_easy",
        name="Single Alert — Network Latency",
        difficulty="easy",
        scenario_label="🟡 Network — p99 Latency Spike",
        description="p99 latency on load-balancer-01 hit 3 400 ms (threshold 800 ms). Route to Network.",
        alerts=[Alert(
            alert_id="alert-001", service="load-balancer-01",
            metric="p99_latency_ms", value=3400.0, threshold=800.0,
            duration_s=240, is_noise=False,
        )],
        ground_truth={
            "severity": "P2", "team": "network",
            "root_cause_keywords": ["network", "latency", "p99", "load-balancer", "spike"],
        },
    ),

    TaskDefinition(
        task_id="task_easy",
        name="Single Alert — 5xx Error Rate",
        difficulty="easy",
        scenario_label="🟢 App — HTTP 5xx Spike",
        description="checkout-service HTTP 5xx error rate hit 31% (threshold 5%). Route to App team.",
        alerts=[Alert(
            alert_id="alert-001", service="checkout-service",
            metric="http_5xx_rate", value=31.0, threshold=5.0,
            duration_s=210, is_noise=False,
        )],
        ground_truth={
            "severity": "P2", "team": "app",
            "root_cause_keywords": ["http", "5xx", "error", "checkout", "application", "spike"],
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM TASK — 4 scenarios (3 alerts each, correlated root cause)
# ─────────────────────────────────────────────────────────────────────────────
MEDIUM_SCENARIOS: List[TaskDefinition] = [

    TaskDefinition(
        task_id="task_medium",
        name="3 Correlated Alerts — Database Overload",
        difficulty="medium",
        scenario_label="🟠 Database Overload",
        description="DB timeout + 5xx on checkout + p99 latency spike. Root cause = database overload.",
        alerts=[
            Alert(alert_id="alert-001", service="postgres-primary",
                  metric="db_query_time_ms", value=4800.0, threshold=1000.0,
                  duration_s=420, is_noise=False),
            Alert(alert_id="alert-002", service="checkout-service",
                  metric="http_5xx_rate", value=23.5, threshold=5.0,
                  duration_s=390, is_noise=False),
            Alert(alert_id="alert-003", service="load-balancer-01",
                  metric="p99_latency_ms", value=3200.0, threshold=800.0,
                  duration_s=400, is_noise=False),
        ],
        ground_truth={
            "severity": "P1", "team": "database",
            "root_cause_keywords": ["database","db","overload","query","timeout","slow","postgres","connection"],
        },
    ),

    TaskDefinition(
        task_id="task_medium",
        name="3 Correlated Alerts — Network Partition",
        difficulty="medium",
        scenario_label="🔵 Network Partition",
        description="DNS errors + latency spike + 5xx on payment. Root cause = network partition.",
        alerts=[
            Alert(alert_id="alert-001", service="dns-resolver-01",
                  metric="dns_error_rate", value=18.0, threshold=2.0,
                  duration_s=300, is_noise=False),
            Alert(alert_id="alert-002", service="cdn-edge-02",
                  metric="p99_latency_ms", value=4100.0, threshold=800.0,
                  duration_s=280, is_noise=False),
            Alert(alert_id="alert-003", service="payment-service",
                  metric="http_5xx_rate", value=14.0, threshold=5.0,
                  duration_s=260, is_noise=False),
        ],
        ground_truth={
            "severity": "P1", "team": "network",
            "root_cause_keywords": ["network","dns","partition","latency","cdn","routing","connectivity"],
        },
    ),

    TaskDefinition(
        task_id="task_medium",
        name="3 Correlated Alerts — App Memory Leak",
        difficulty="medium",
        scenario_label="🟢 App Memory Leak",
        description="Memory usage spike + 5xx errors + slow response on auth-service. Root cause = memory leak.",
        alerts=[
            Alert(alert_id="alert-001", service="auth-service",
                  metric="memory_usage_pct", value=94.0, threshold=80.0,
                  duration_s=600, is_noise=False),
            Alert(alert_id="alert-002", service="auth-service",
                  metric="http_5xx_rate", value=9.2, threshold=5.0,
                  duration_s=540, is_noise=False),
            Alert(alert_id="alert-003", service="checkout-service",
                  metric="response_time_ms", value=6800.0, threshold=2000.0,
                  duration_s=510, is_noise=False),
        ],
        ground_truth={
            "severity": "P1", "team": "app",
            "root_cause_keywords": ["memory","leak","auth","application","heap","oom","usage"],
        },
    ),

    TaskDefinition(
        task_id="task_medium",
        name="3 Correlated Alerts — Infrastructure CPU Saturation",
        difficulty="medium",
        scenario_label="🔴 Infrastructure CPU Saturation",
        description="CPU saturation on 2 API servers + elevated 5xx. Root cause = under-provisioned infra.",
        alerts=[
            Alert(alert_id="alert-001", service="api-server-03",
                  metric="cpu_utilisation", value=99.0, threshold=85.0,
                  duration_s=480, is_noise=False),
            Alert(alert_id="alert-002", service="api-server-07",
                  metric="cpu_utilisation", value=97.5, threshold=85.0,
                  duration_s=460, is_noise=False),
            Alert(alert_id="alert-003", service="checkout-service",
                  metric="http_5xx_rate", value=17.0, threshold=5.0,
                  duration_s=440, is_noise=False),
        ],
        ground_truth={
            "severity": "P1", "team": "sre",
            "root_cause_keywords": ["cpu","saturation","infrastructure","capacity","api-server","overload"],
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# HARD TASK — 10–15 alerts (noise mixed in), single root cause
# ─────────────────────────────────────────────────────────────────────────────
def _make_hard_task(seed: int = 42) -> TaskDefinition:
    """
    Generate a hard task: 6 real alerts (database outage root cause)
    + 5 noise alerts (flapping / self-resolving).
    Seeded for reproducibility.
    """
    rng = random.Random(seed)

    real_alerts = [
        Alert(alert_id="alert-001", service="postgres-primary",
              metric="db_query_time_ms",
              value=round(rng.uniform(6000, 9000), 1), threshold=1000.0,
              duration_s=rng.randint(480, 720), is_noise=False),
        Alert(alert_id="alert-002", service="postgres-replica",
              metric="replication_lag_ms",
              value=round(rng.uniform(12000, 20000), 1), threshold=500.0,
              duration_s=rng.randint(400, 600), is_noise=False),
        Alert(alert_id="alert-003", service="checkout-service",
              metric="http_5xx_rate",
              value=round(rng.uniform(28, 45), 1), threshold=5.0,
              duration_s=rng.randint(420, 650), is_noise=False),
        Alert(alert_id="alert-004", service="payment-service",
              metric="http_5xx_rate",
              value=round(rng.uniform(20, 35), 1), threshold=5.0,
              duration_s=rng.randint(380, 580), is_noise=False),
        Alert(alert_id="alert-005", service="load-balancer-01",
              metric="p99_latency_ms",
              value=round(rng.uniform(3500, 5500), 1), threshold=800.0,
              duration_s=rng.randint(360, 560), is_noise=False),
        Alert(alert_id="alert-006", service="auth-service",
              metric="response_time_ms",
              value=round(rng.uniform(5000, 8000), 1), threshold=2000.0,
              duration_s=rng.randint(300, 500), is_noise=False),
    ]

    noise_alerts = [
        Alert(alert_id="alert-007", service="redis-cache-01",
              metric="cpu_utilisation",
              value=round(rng.uniform(82, 88), 1), threshold=80.0,
              duration_s=rng.randint(30, 90), is_noise=True),   # short → flapping
        Alert(alert_id="alert-008", service="reporting-service",
              metric="memory_usage_pct",
              value=round(rng.uniform(81, 86), 1), threshold=80.0,
              duration_s=rng.randint(20, 60), is_noise=True),
        Alert(alert_id="alert-009", service="api-server-07",
              metric="disk_io_mbps",
              value=round(rng.uniform(195, 210), 1), threshold=190.0,
              duration_s=rng.randint(15, 45), is_noise=True),
        Alert(alert_id="alert-010", service="cdn-edge-02",
              metric="p99_latency_ms",
              value=round(rng.uniform(820, 860), 1), threshold=800.0,
              duration_s=rng.randint(10, 40), is_noise=True),
        Alert(alert_id="alert-011", service="dns-resolver-01",
              metric="dns_error_rate",
              value=round(rng.uniform(2.1, 2.8), 1), threshold=2.0,
              duration_s=rng.randint(8, 30), is_noise=True),
    ]

    # Shuffle so noise is not always at the end
    all_alerts = real_alerts + noise_alerts
    rng.shuffle(all_alerts)

    noise_ids = {a.alert_id for a in noise_alerts}

    return TaskDefinition(
        task_id="task_hard",
        name="10+ Noisy Alerts — Suppress & Escalate",
        difficulty="hard",
        scenario_label="🔥 Database Outage + Noise",
        description=(
            f"{len(all_alerts)} alerts: {len(real_alerts)} real (database outage) + "
            f"{len(noise_alerts)} noise (flapping/self-resolving). "
            "Suppress noise, identify root cause, assign P1 to Database team."
        ),
        alerts=all_alerts,
        ground_truth={
            "severity": "P1",
            "team": "database",
            "root_cause_keywords": [
                "database", "db", "postgres", "overload", "query", "timeout",
                "replication", "lag", "outage", "connection",
            ],
            "noise_ids": list(noise_ids),
        },
    )


TASK_HARD = _make_hard_task(seed=42)

# ─────────────────────────────────────────────────────────────────────────────
# TASK REGISTRY (static defaults used by environment)
# ─────────────────────────────────────────────────────────────────────────────
ALL_TASKS: Dict[str, TaskDefinition] = {
    "task_easy":   EASY_SCENARIOS[0],   # replaced at reset by random picker
    "task_medium": MEDIUM_SCENARIOS[0], # replaced at reset by random picker
    "task_hard":   TASK_HARD,
}


def pick_random_task(task_id: str, seed: Optional[int] = None) -> TaskDefinition:
    """Return a random scenario variant for easy/medium, or the fixed hard task."""
    if seed is not None:
        random.seed(seed)
    if task_id == "task_easy":
        t = random.choice(EASY_SCENARIOS)
        return t
    elif task_id == "task_medium":
        t = random.choice(MEDIUM_SCENARIOS)
        return t
    elif task_id == "task_hard":
        return _make_hard_task(seed=seed or 42)
    raise ValueError(f"Unknown task_id: {task_id}")


# ─────────────────────────────────────────────────────────────────────────────
# GRADERS
# ─────────────────────────────────────────────────────────────────────────────

def _keyword_score(root_cause: str, keywords: List[str]) -> float:
    rc = root_cause.lower()
    matched = sum(1 for kw in keywords if kw in rc)
    return round(min(matched / len(keywords), 1.0), 4)


def grade_easy(action: TriageAction, task: TaskDefinition) -> TriageReward:
    """severity(0.5) + team(0.5)"""
    gt = task.ground_truth
    sev_ok  = action.severity == gt["severity"]
    team_ok = action.team     == gt["team"]
    rc_score = _keyword_score(action.root_cause, gt["root_cause_keywords"])
    score = (0.5 if sev_ok else 0.0) + (0.5 if team_ok else 0.0)
    return TriageReward(
        score=round(score, 4), severity_correct=sev_ok, team_correct=team_ok,
        root_cause_score=rc_score,
        reason=(
            f"Severity {'✓' if sev_ok else '✗'} (expected {gt['severity']}, got {action.severity}) | "
            f"Team {'✓' if team_ok else '✗'} (expected {gt['team']}, got {action.team}) | "
            f"Root-cause keywords: {rc_score:.0%}"
        ),
    )


def grade_medium(action: TriageAction, task: TaskDefinition) -> TriageReward:
    """severity(0.35) + team(0.35) + root_cause(0.30)"""
    gt = task.ground_truth
    sev_ok  = action.severity == gt["severity"]
    team_ok = action.team     == gt["team"]
    rc_score = _keyword_score(action.root_cause, gt["root_cause_keywords"])
    score = (0.35 if sev_ok else 0.0) + (0.35 if team_ok else 0.0) + (0.30 * rc_score)
    return TriageReward(
        score=round(score, 4), severity_correct=sev_ok, team_correct=team_ok,
        root_cause_score=rc_score,
        reason=(
            f"Severity {'✓' if sev_ok else '✗'} (expected {gt['severity']}, got {action.severity}) | "
            f"Team {'✓' if team_ok else '✗'} (expected {gt['team']}, got {action.team}) | "
            f"Root-cause: {rc_score:.0%}"
        ),
    )


def grade_hard(action: TriageAction, task: TaskDefinition) -> TriageReward:
    """
    noise_suppressed(0.20) + severity(0.25) + team(0.25) + root_cause(0.30)
    Over-suppression (real alerts marked noise) → -0.2 penalty per real alert suppressed.
    """
    gt = task.ground_truth
    noise_ids = set(gt.get("noise_ids", []))
    real_ids  = {a.alert_id for a in task.alerts} - noise_ids
    suppressed_set = set(action.suppressed)

    # Noise correctly suppressed
    correct_suppressed = suppressed_set & noise_ids
    # Real alerts wrongly suppressed
    wrong_suppressed = suppressed_set & real_ids

    noise_score = 0.0
    if noise_ids:
        recall    = len(correct_suppressed) / len(noise_ids)
        precision = len(correct_suppressed) / max(len(suppressed_set), 1)
        noise_score = round((recall + precision) / 2, 4) if suppressed_set else 0.0

    # Penalty for over-suppression
    over_suppress_penalty = 0.2 * len(wrong_suppressed)

    sev_ok   = action.severity == gt["severity"]
    team_ok  = action.team     == gt["team"]
    rc_score = _keyword_score(action.root_cause, gt["root_cause_keywords"])

    score = max(0.0, (
        (0.20 * noise_score) +
        (0.25 if sev_ok  else 0.0) +
        (0.25 if team_ok else 0.0) +
        (0.30 * rc_score) -
        over_suppress_penalty
    ))

    return TriageReward(
        score=round(score, 4), severity_correct=sev_ok, team_correct=team_ok,
        root_cause_score=rc_score,
        reason=(
            f"Noise suppression: {noise_score:.0%} ({len(correct_suppressed)}/{len(noise_ids)} correct"
            f"{f', -{over_suppress_penalty:.1f} over-suppress penalty' if wrong_suppressed else ''}) | "
            f"Severity {'✓' if sev_ok else '✗'} (expected {gt['severity']}, got {action.severity}) | "
            f"Team {'✓' if team_ok else '✗'} (expected {gt['team']}, got {action.team}) | "
            f"Root-cause: {rc_score:.0%}"
        ),
    )


GRADERS = {
    "task_easy":   grade_easy,
    "task_medium": grade_medium,
    "task_hard":   grade_hard,
}
