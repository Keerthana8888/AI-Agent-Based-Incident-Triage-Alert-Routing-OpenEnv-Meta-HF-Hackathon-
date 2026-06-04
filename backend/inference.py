"""
inference.py — LLM-powered triage agent (Modules 2 & 3)

MANDATORY hackathon rules:
  - OpenAI client only (not Anthropic SDK)
  - Credentials from env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN
  - Runtime < 20 minutes

Run:
    export API_BASE_URL=https://router.huggingface.co/v1
    export MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct
    export HF_TOKEN=your_hf_token_here
    python inference.py
"""

import os, json, re
from openai import OpenAI
from environment import IncidentTriageEnv
from models import TriageAction

client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
    api_key=os.getenv("HF_TOKEN", ""),
)
MODEL = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")


def build_prompt(obs, task_id: str) -> list:
    alert_lines = []
    for i, a in enumerate(obs.alerts, 1):
        pct = (a.value - a.threshold) / a.threshold * 100
        noise_hint = " ⚠️ SHORT DURATION — possible noise" if a.duration_s < 60 else ""
        alert_lines.append(
            f"  Alert {i} [{a.alert_id}]{noise_hint}\n"
            f"    Service : {a.service}\n"
            f"    Metric  : {a.metric}\n"
            f"    Value   : {a.value}  (threshold {a.threshold}, {pct:+.1f}% over)\n"
            f"    Firing  : {a.duration_s//60}m {a.duration_s%60}s"
        )
    svc_text = "\n".join(f"    {s} → {t}" for s,t in obs.services_map.items())

    hard_addendum = ""
    if task_id == "task_hard":
        hard_addendum = (
            "\n\nSUPPRESSION RULES (task_hard):\n"
            "  - Noise alerts: duration < 60s AND value barely over threshold (<10% over) — suppress these.\n"
            "  - List noise alert_ids in the 'suppressed' array.\n"
            "  - Focus on the remaining real alerts to find the root cause.\n"
            "  - DO NOT suppress real alerts (long duration, significantly over threshold)."
        )

    system = (
        "You are a senior Site Reliability Engineer performing incident triage.\n"
        "Severity: P1=Critical (revenue impact), P2=High (users affected), "
        "P3=Medium (degraded, no user impact), P4=Low (informational)\n"
        "Teams: sre=infrastructure, database=DB/connections, "
        "network=latency/DNS, app=application bugs/memory\n"
        "When multiple alerts fire together, find the SINGLE root cause.\n"
        f"{hard_addendum}\n\n"
        "Respond ONLY with valid JSON (no markdown, no explanation):\n"
        '{"severity":"P1","team":"database","root_cause":"one sentence","suppressed":[]}'
    )
    user = (
        f"=== ALERTS (task={obs.task_id}, step={obs.step}/{obs.max_steps}) ===\n"
        + "\n".join(alert_lines)
        + f"\n\n=== SERVICES MAP ===\n{svc_text}\n\n"
        "Provide your triage JSON decision."
    )
    return [{"role":"system","content":system}, {"role":"user","content":user}]


def parse_action(response) -> TriageAction:
    raw = re.sub(r"```(?:json)?", "", response.choices[0].message.content.strip()).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*?\}', raw, re.DOTALL)
        data = json.loads(m.group()) if m else {}

    sev  = data.get("severity","P2")
    team = data.get("team","sre")
    if sev  not in {"P1","P2","P3","P4"}:  sev  = "P2"
    if team not in {"sre","database","network","app"}: team = "sre"

    return TriageAction(
        severity=sev, team=team,
        root_cause=str(data.get("root_cause","unknown")),
        suppressed=data.get("suppressed",[]),
    )


def run_task(task_id: str) -> float:
    print(f"\n{'='*55}\n  TASK: {task_id}\n{'='*55}")
    env  = IncidentTriageEnv(task_id=task_id, seed=42)
    obs  = env.reset()
    done = False; final_score = 0.0

    while not done:
        print(f"\n  Step {obs.step+1} — {len(obs.alerts)} alert(s) | scenario: {env._task.scenario_label}")
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_prompt(obs, task_id),
            max_tokens=300, temperature=0.1,
        )
        action = parse_action(response)
        print(f"  → severity={action.severity}, team={action.team}")
        print(f"  → root_cause: {action.root_cause}")
        if action.suppressed:
            print(f"  → suppressed: {action.suppressed}")

        obs, reward, done, info = env.step(action)
        final_score = info["final_score"]
        print(f"  → score={reward:.3f} | {info['reason']}")

    print(f"\n  FINAL [{task_id}]: {final_score:.3f}")
    return final_score


if __name__ == "__main__":
    print(f"\n🚨 Incident Triage Agent\n   Model: {MODEL}\n   API  : {os.getenv('API_BASE_URL','NOT SET')}")
    scores = {}
    for tid in ["task_easy","task_medium","task_hard"]:
        scores[tid] = run_task(tid)

    print(f"\n{'='*55}\n  SUMMARY\n{'='*55}")
    for tid, sc in scores.items():
        bar = "█"*int(sc*20) + "░"*(20-int(sc*20))
        print(f"  {tid:<15} {bar}  {sc:.3f}")
