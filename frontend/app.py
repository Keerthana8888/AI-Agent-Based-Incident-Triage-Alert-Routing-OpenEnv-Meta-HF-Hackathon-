"""
app.py — Streamlit UI for Modules 2 & 3 (fixed text visibility + all features)
"""

import streamlit as st
import requests, json, os, re

BACKEND = "http://localhost:7860"

st.set_page_config(page_title="Incident Triage", page_icon="🚨", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# CSS  — every text element has an explicit, high-contrast color
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global base ── */
html, body, [data-testid="stAppViewContainer"] { font-family: 'Segoe UI', sans-serif; }

/* ── Page header ── */
.page-header {
    background: linear-gradient(135deg, #1a1f3a 0%, #2d3561 100%);
    color: #ffffff;
    padding: 20px 28px; border-radius: 12px; margin-bottom: 20px;
}
.page-header h1 { margin: 0; font-size: 1.8rem; color: #ffffff; }
.page-header p  { margin: 4px 0 0; font-size: 0.9rem; color: #c5cae9; }

/* ── Alert cards ── */
.alert-card {
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
    border-left: 5px solid;
}
.alert-p1    { border-color: #e53935; background: #fff5f5; color: #212121; }
.alert-p2    { border-color: #fb8c00; background: #fff8f0; color: #212121; }
.alert-p3    { border-color: #f9a825; background: #fffde7; color: #212121; }
.alert-p4    { border-color: #43a047; background: #f1f8f1; color: #212121; }
.alert-noise { border-color: #9e9e9e; background: #f5f5f5; color: #616161; }

.alert-card strong  { color: #1a1a2e; }
.alert-card code    { color: #37474f; background: #eceff1; padding: 1px 5px; border-radius: 3px; }

/* ── Team chips ── */
.route-chip {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; color: #ffffff; margin-left: 6px;
}
.chip-sre      { background: #3949ab; }
.chip-database { background: #6d4c41; }
.chip-network  { background: #00838f; }
.chip-app      { background: #2e7d32; }
.chip-unknown  { background: #757575; }

/* ── Score boxes ── */
.score-box { border-radius: 10px; padding: 14px; text-align: center; margin-bottom: 10px; }
.score-perfect { background: #e8f5e9; border: 2px solid #43a047; color: #1b5e20; }
.score-partial { background: #fff8e1; border: 2px solid #f9a825; color: #4e3600; }
.score-low     { background: #ffebee; border: 2px solid #e53935; color: #7f0000; }
.score-box div { color: inherit; }

/* ── Routing table ── */
.routing-table { width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; }
.routing-table th {
    background: #1a1f3a; color: #ffffff;
    padding: 9px 12px; text-align: left; font-size: 0.85rem;
}
.routing-table td { padding: 8px 12px; border-bottom: 1px solid #e0e0e0; font-size: 0.85rem; color: #212121; }
.routing-table tr:hover td { background: #e8eaf6; }

/* ── Step dots ── */
.step-indicator { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; }
.step-dot { width: 12px; height: 12px; border-radius: 50%; background: #bdbdbd; }
.step-dot.done    { background: #43a047; }
.step-dot.current { background: #fb8c00; }
.step-label { font-size: 0.82rem; color: #37474f; margin-left: 6px; font-weight: 600; }

/* ── History bar ── */
.hist-bar { font-family: monospace; font-size: 0.82rem; margin: 3px 0; color: #212121; }
.hist-bar .bar-perfect { color: #2e7d32; }
.hist-bar .bar-partial { color: #e65100; }
.hist-bar .bar-low     { color: #c62828; }

/* ── Noise tag ── */
.noise-tag { color: #616161; font-size: 0.75rem; font-style: italic; }

/* ── Misc text fixes ── */
.firing-time  { font-size: 0.82rem; color: #37474f; font-weight: 600; }
.threshold-val { color: #546e7a; }
.over-pct     { color: #c62828; font-weight: 700; }
.score-sub    { font-size: 0.9rem; color: #424242; }
.suppressed-label { color: #616161; font-style: italic; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_defaults = {
    "obs": None, "result": None, "episode_done": False,
    "last_action": None, "history": [],
    "selected_suppress": [],
    "step_log": [],
    "scenario_label": "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SEV_ICON     = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
SEV_CLASS    = {"P1": "alert-p1", "P2": "alert-p2", "P3": "alert-p3", "P4": "alert-p4"}
SEV_PRIORITY = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}

TEAM_CHIP = {
    "sre":      '<span class="route-chip chip-sre">SRE</span>',
    "database": '<span class="route-chip chip-database">DATABASE</span>',
    "network":  '<span class="route-chip chip-network">NETWORK</span>',
    "app":      '<span class="route-chip chip-app">APP</span>',
}

METRIC_META = {
    "cpu_utilisation":    {"label": "CPU Utilisation",  "unit": "%",    "sev_team": ("P2","sre")},
    "db_query_time_ms":   {"label": "DB Query Time",    "unit": "ms",   "sev_team": ("P1","database")},
    "http_5xx_rate":      {"label": "HTTP 5xx Rate",    "unit": "%",    "sev_team": ("P2","app")},
    "p99_latency_ms":     {"label": "p99 Latency",      "unit": "ms",   "sev_team": ("P2","network")},
    "memory_usage_pct":   {"label": "Memory Usage",     "unit": "%",    "sev_team": ("P2","app")},
    "response_time_ms":   {"label": "Response Time",    "unit": "ms",   "sev_team": ("P2","app")},
    "dns_error_rate":     {"label": "DNS Error Rate",   "unit": "%",    "sev_team": ("P2","network")},
    "replication_lag_ms": {"label": "Replication Lag",  "unit": "ms",   "sev_team": ("P1","database")},
    "disk_io_mbps":       {"label": "Disk I/O",         "unit": "MB/s", "sev_team": ("P3","sre")},
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def backend_reset(task_id):
    try:
        r = requests.post(f"{BACKEND}/reset", json={"task_id": task_id}, timeout=10)
        r.raise_for_status(); return r.json()
    except Exception as e:
        st.error(f"❌ /reset failed: {e}"); return None

def backend_step(action: dict):
    try:
        r = requests.post(f"{BACKEND}/step", json=action, timeout=30)
        r.raise_for_status(); return r.json()
    except Exception as e:
        st.error(f"❌ /step failed: {e}"); return None

def backend_state():
    try:
        r = requests.get(f"{BACKEND}/state", timeout=5)
        r.raise_for_status(); return r.json()
    except:
        return {}

def guess_severity(alert: dict) -> str:
    pct = (alert["value"] - alert["threshold"]) / alert["threshold"]
    if pct > 3.0:  return "P1"
    if pct > 1.5:  return "P2"
    if pct > 0.5:  return "P3"
    return "P4"

def guess_team(alert: dict) -> str:
    return METRIC_META.get(alert["metric"], {}).get("sev_team", ("P2","sre"))[1]

def mlabel(metric: str) -> str:
    return METRIC_META.get(metric, {}).get("label", metric.replace("_"," ").title())

def munit(metric: str) -> str:
    return METRIC_META.get(metric, {}).get("unit", "")


# ─────────────────────────────────────────────────────────────────────────────
# AI DECISION LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def rule_based(alerts: list, suppressed_ids: list = []) -> dict:
    active  = [a for a in alerts if a["alert_id"] not in suppressed_ids]
    metrics = [a["metric"] for a in active]
    svcs    = [a["service"] for a in active]

    if "replication_lag_ms" in metrics or (
        "db_query_time_ms" in metrics and
        ("http_5xx_rate" in metrics or "p99_latency_ms" in metrics)
    ):
        return {"severity":"P1","team":"database",
                "root_cause":"Database overload — query timeouts and replication lag causing downstream 5xx errors and latency spikes.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "db_query_time_ms" in metrics:
        return {"severity":"P1","team":"database",
                "root_cause":"Database query timeout indicating postgres overload or connection pool exhaustion.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "dns_error_rate" in metrics and "p99_latency_ms" in metrics:
        return {"severity":"P1","team":"network",
                "root_cause":"Network partition — DNS resolution errors causing latency spikes and downstream failures.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "memory_usage_pct" in metrics and "http_5xx_rate" in metrics:
        return {"severity":"P1","team":"app",
                "root_cause":"Application memory leak causing OOM pressure and elevated 5xx errors.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if metrics.count("cpu_utilisation") >= 2:
        return {"severity":"P1","team":"sre",
                "root_cause":"CPU saturation across multiple API servers — infrastructure capacity exhausted.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "cpu_utilisation" in metrics:
        return {"severity":"P2","team":"sre",
                "root_cause":"High CPU utilisation spike on API server indicating infrastructure overload.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "http_5xx_rate" in metrics:
        return {"severity":"P2","team":"app",
                "root_cause":"Elevated HTTP 5xx error rate from application-level errors.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    if "p99_latency_ms" in metrics:
        return {"severity":"P2","team":"network",
                "root_cause":"Network p99 latency spike between services.",
                "suppressed":suppressed_ids,"source":"rule-based"}
    return {"severity":"P2","team":"sre",
            "root_cause":f"Anomaly detected on {svcs[0] if svcs else 'unknown service'}.",
            "suppressed":suppressed_ids,"source":"rule-based"}


def call_llm(obs: dict, suppressed_ids: list = []) -> dict:
    api_base = os.getenv("API_BASE_URL","")
    hf_token = os.getenv("HF_TOKEN","")
    model    = os.getenv("MODEL_NAME","meta-llama/Llama-3.3-70B-Instruct")
    alerts   = obs.get("alerts",[])
    smap     = obs.get("services_map",{})
    if not api_base or not hf_token:
        return rule_based(alerts, suppressed_ids)
    try:
        from openai import OpenAI
        client = OpenAI(base_url=api_base, api_key=hf_token)
        lines = []
        for i, a in enumerate(alerts,1):
            pct = (a["value"]-a["threshold"])/a["threshold"]*100
            hint = " [SHORT — possible noise]" if a["duration_s"] < 60 else ""
            lines.append(
                f"Alert {i} [{a['alert_id']}]{hint}\n"
                f"  Service: {a['service']} | Metric: {a['metric']}\n"
                f"  Value: {a['value']} (threshold {a['threshold']}, {pct:+.1f}% over)\n"
                f"  Firing: {a['duration_s']//60}m {a['duration_s']%60}s"
            )
        system = (
            "You are a senior SRE performing incident triage. Analyse ALL alerts.\n"
            "Noise alerts: duration<60s and barely over threshold — suppress these.\n"
            "Find the single root cause from real alerts.\n"
            "P1=Critical P2=High P3=Medium P4=Low | Teams: sre database network app\n"
            "Respond ONLY with JSON (no markdown):\n"
            '{"severity":"P1","team":"database","root_cause":"...","suppressed":["alert-007"]}'
        )
        user = "ALERTS:\n"+"\n".join(lines)+"\nSERVICES:\n"+\
               "\n".join(f"  {s}→{t}" for s,t in smap.items())+"\nReturn JSON."
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=300, temperature=0.1,
        )
        raw  = re.sub(r"```(?:json)?","",resp.choices[0].message.content.strip()).strip()
        data = json.loads(raw)
        return {"severity":data.get("severity","P2"),"team":data.get("team","sre"),
                "root_cause":data.get("root_cause","LLM decision"),
                "suppressed":data.get("suppressed",[]),"source":"llm"}
    except Exception as e:
        st.warning(f"LLM failed ({e}), using rule-based fallback.")
        return rule_based(alerts, suppressed_ids)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────
def render_alert_card(a, sev, team, is_noise=False, routed=False, r_sev="", r_team=""):
    css   = "alert-noise" if is_noise else SEV_CLASS.get(sev, "alert-p3")
    unit  = munit(a["metric"])
    pct   = (a["value"] - a["threshold"]) / a["threshold"] * 100
    mins, secs = a["duration_s"] // 60, a["duration_s"] % 60
    chip  = TEAM_CHIP.get(r_team if routed and not is_noise else team,
                          '<span class="route-chip chip-unknown">?</span>')
    disp_sev = r_sev if routed else sev
    noise_tag = '<span class="noise-tag"> [noise — suppressed]</span>' if is_noise else ""

    st.markdown(f"""
    <div class="{css} alert-card">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <strong style="color:#1a1a2e">{SEV_ICON.get(disp_sev,'')} {a['alert_id']}</strong>
          &nbsp;<span style="color:#37474f">{a['service']}</span>{noise_tag}{chip if not is_noise else ''}
        </div>
        <span class="firing-time">{mins}m {secs}s firing</span>
      </div>
      <div style="margin-top:8px;font-size:0.88rem;color:#212121">
        <strong>{mlabel(a['metric'])}:</strong>
        &nbsp;<span style="font-size:1.1rem;font-weight:700;color:#1a1a2e">{a['value']:,.1f}{unit}</span>
        &nbsp;<span class="threshold-val">/ threshold {a['threshold']:,.1f}{unit}</span>
        &nbsp;<span class="over-pct">{pct:+.1f}% over</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_routing_table(alerts, decision, noise_ids=[]):
    suppressed = set(decision.get("suppressed", []))
    rows = []
    for a in alerts:
        is_noise = a["alert_id"] in suppressed
        sev  = "NOISE" if is_noise else guess_severity(a)
        team = "—"     if is_noise else guess_team(a)
        rows.append((SEV_PRIORITY.get(sev, 99), sev, team, a))
    rows.sort(key=lambda x: x[0])

    sev_bg    = {"P1":"#ffebee","P2":"#fff3e0","P3":"#fffde7","P4":"#f1f8f1","NOISE":"#f5f5f5"}
    sev_color = {"P1":"#c62828","P2":"#bf360c","P3":"#f57f17","P4":"#1b5e20","NOISE":"#616161"}

    rows_html = ""
    for _, sev, team, a in rows:
        pct  = (a["value"] - a["threshold"]) / a["threshold"] * 100
        unit = munit(a["metric"])
        chip = TEAM_CHIP.get(team,"") if team != "—" else \
               '<span class="suppressed-label">suppressed</span>'
        rows_html += f"""
        <tr style="background:{sev_bg.get(sev,'#fff')}">
          <td><strong style="color:{sev_color.get(sev,'#212121')}">{SEV_ICON.get(sev,'🔘')} {sev}</strong></td>
          <td style="color:#212121">{a['alert_id']}</td>
          <td style="color:#212121">{a['service']}</td>
          <td style="color:#212121">{mlabel(a['metric'])}</td>
          <td><strong style="color:#1a1a2e">{a['value']:,.1f}{unit}</strong>
              <span style="color:#546e7a"> / {a['threshold']:,.1f}</span></td>
          <td style="color:#c62828;font-weight:600">{pct:+.1f}%</td>
          <td>{chip}</td>
        </tr>"""

    st.markdown(f"""
    <table class="routing-table">
      <thead><tr>
        <th>Priority</th><th>Alert ID</th><th>Service</th>
        <th>Metric</th><th>Value</th><th>% Over</th><th>Routed To</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render_score_breakdown(info, task_id):
    score = info.get("final_score", 0)
    cls   = "score-perfect" if score >= 0.9 else ("score-partial" if score >= 0.5 else "score-low")
    emoji = "✅" if score >= 0.9 else ("⚠️" if score >= 0.5 else "❌")
    label = "Perfect!" if score >= 0.9 else ("Partial credit" if score >= 0.5 else "Needs improvement")

    st.markdown(f"""
    <div class="score-box {cls}">
      <div style="font-size:2.4rem;font-weight:900">{emoji} {score:.3f}</div>
      <div class="score-sub">{label} &nbsp;·&nbsp; out of 1.000</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(score)

    sev_ok  = info.get("severity_correct", False)
    team_ok = info.get("team_correct", False)
    rc      = info.get("root_cause_score", 0.0)

    if task_id == "task_easy":
        components = [("Severity", sev_ok, 0.5, None),
                      ("Team",     team_ok, 0.5, None)]
    elif task_id == "task_medium":
        components = [("Severity",   sev_ok,  0.35, None),
                      ("Team",       team_ok, 0.35, None),
                      ("Root Cause", None,    0.30, rc)]
    else:
        components = [("Severity",          sev_ok,  0.25, None),
                      ("Team",              team_ok, 0.25, None),
                      ("Root Cause",        None,    0.30, rc),
                      ("Noise Suppression", None,    0.20, None)]

    for comp_label, ok, weight, frac in components:
        if frac is not None:
            pts  = frac * weight
            icon = "✅" if frac >= 0.6 else ("⚠️" if frac >= 0.3 else "❌")
            pbar = frac
        else:
            pts  = weight if ok else 0.0
            icon = "✅" if ok else "❌"
            pbar = 1.0 if ok else 0.0

        st.markdown(
            f'<div style="color:#212121;font-weight:600;margin-top:6px">'
            f'{icon} {comp_label} &nbsp;'
            f'<span style="color:#546e7a;font-weight:400">{pts:.2f} / {weight:.2f} pts</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.progress(pbar)


def render_history():
    history = st.session_state.history
    if not history:
        st.info("No runs yet. Start a task and run the AI agent.")
        return
    for i, h in enumerate(history[-10:]):
        filled = int(h["score"] * 20)
        bar_ok  = "█" * filled
        bar_gap = "░" * (20 - filled)
        bar_cls = "bar-perfect" if h["score"]>=0.9 else ("bar-partial" if h["score"]>=0.5 else "bar-low")
        sev = "✅" if h.get("severity_ok") else "❌"
        tm  = "✅" if h.get("team_ok")     else "❌"
        st.markdown(
            f'<div class="hist-bar">'
            f'<span class="{bar_cls}">{bar_ok}</span>'
            f'<span style="color:#bdbdbd">{bar_gap}</span>'
            f' <strong style="color:#212121">{h["score"]:.3f}</strong>'
            f' <span style="color:#546e7a">| {h["task"]} | Sev{sev} Team{tm}'
            f' | <em>{h.get("source","?")}</em></span>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.history = []
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h1>🚨 Incident Triage &amp; Alert Routing</h1>
  <p>AI-Powered SRE Simulation &nbsp;·&nbsp; FastAPI + Streamlit &nbsp;·&nbsp; Meta × Hugging Face Hackathon</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    task_options = {
        "task_easy":   "🟢 Easy — Single Alert",
        "task_medium": "🟠 Medium — Correlated Alerts",
        "task_hard":   "🔥 Hard — Noisy Alerts",
    }
    selected_task = st.selectbox(
        "Task", options=list(task_options.keys()),
        format_func=lambda x: task_options[x]
    )

    task_desc = {
        "task_easy":   "1 alert, unambiguous root cause. Scored: severity(0.5) + team(0.5).",
        "task_medium": "3 correlated alerts with a shared root cause. Scored: severity(0.35) + team(0.35) + root_cause(0.30).",
        "task_hard":   "10–15 alerts including noise. Scored: noise(0.20) + severity(0.25) + team(0.25) + root_cause(0.30).",
    }
    st.caption(task_desc[selected_task])

    ai_mode = st.radio(
        "AI Mode",
        ["📏 Rule-Based (offline)", "🤖 LLM Agent (API keys required)"],
        index=0,
    )

    api_set = bool(os.getenv("API_BASE_URL") and os.getenv("HF_TOKEN"))
    if "LLM" in ai_mode:
        if api_set:
            st.success("✅ API keys detected")
        else:
            st.warning("⚠️ No API keys — will fall back to rule-based.\nSet API_BASE_URL, MODEL_NAME, HF_TOKEN in your .env")

    st.divider()

    if st.button("▶ Start Task", type="primary", use_container_width=True):
        obs = backend_reset(selected_task)
        if obs:
            state_data = backend_state()
            st.session_state.obs           = obs
            st.session_state.result        = None
            st.session_state.episode_done  = False
            st.session_state.last_action   = None
            st.session_state.selected_suppress = []
            st.session_state.step_log      = []
            st.session_state.scenario_label = state_data.get("scenario_label","")
            st.success("✅ Environment reset!")
            st.rerun()

    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — guard
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.obs:
    st.info("👈 Select a task and click **▶ Start Task** in the sidebar to begin.")
    st.stop()

obs          = st.session_state.obs
alerts       = obs.get("alerts", [])
task_id      = obs.get("task_id", "task_easy")
services_map = obs.get("services_map", {})
suppressed_set = set(st.session_state.selected_suppress)

tab_alerts, tab_results, tab_history = st.tabs(["📡 Alerts & Routing", "📊 AI Decision", "📈 History"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Alerts & Routing
# ─────────────────────────────────────────────────────────────────────────────
with tab_alerts:
    label = st.session_state.scenario_label
    if label:
        st.markdown(f'<div style="color:#1a1f3a;font-weight:700;font-size:1rem;margin-bottom:8px">📌 Scenario: {label}</div>', unsafe_allow_html=True)

    # Step progress dots
    step_n   = obs.get("step", 0)
    max_step = obs.get("max_steps", 3)
    dots = "".join(
        f'<div class="step-dot {"done" if i < step_n else "current" if i == step_n else ""}"></div>'
        for i in range(max_step)
    )
    st.markdown(
        f'<div class="step-indicator">{dots}'
        f'<span class="step-label">Step {step_n} / {max_step}</span></div>',
        unsafe_allow_html=True
    )

    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        st.subheader(f"📡 Incoming Alerts ({len(alerts)})")

        # Hard mode: suppression multiselect
        if task_id == "task_hard" and not st.session_state.episode_done:
            all_ids = [a["alert_id"] for a in alerts]
            st.session_state.selected_suppress = st.multiselect(
                "🔇 Mark alerts as noise (suppress):",
                options=all_ids,
                default=st.session_state.selected_suppress,
                help="Alerts with short duration and barely above threshold are likely noise.",
            )
            suppressed_set = set(st.session_state.selected_suppress)

        # Sort by severity then render each card
        sorted_alerts = sorted(
            alerts,
            key=lambda a: SEV_PRIORITY.get(
                "NOISE" if a["alert_id"] in suppressed_set else guess_severity(a), 99
            )
        )
        for a in sorted_alerts:
            is_n = a["alert_id"] in suppressed_set
            sev  = guess_severity(a)
            team = guess_team(a)
            act  = st.session_state.last_action
            if act:
                render_alert_card(a, sev, team, is_n,
                                  routed=True,
                                  r_sev=act["severity"],
                                  r_team=act["team"] if not is_n else "")
            else:
                render_alert_card(a, sev, team, is_n)

    with right_col:
        st.subheader("🗺️ Service → Team Map")
        for svc, team in services_map.items():
            chip = TEAM_CHIP.get(team,"")
            st.markdown(
                f'<div style="margin:4px 0;color:#212121"><code style="color:#37474f">{svc}</code> {chip}</div>',
                unsafe_allow_html=True
            )

        st.divider()

        if not st.session_state.episode_done:
            btn_label = "🔄 Run Again" if st.session_state.result else "🤖 Run AI Agent"
            if st.button(btn_label, type="primary", use_container_width=True):
                with st.spinner("AI analysing alerts…"):
                    use_llm = "LLM" in ai_mode and api_set
                    sup_ids = list(suppressed_set)
                    decision = call_llm(obs, sup_ids) if use_llm else rule_based(alerts, sup_ids)
                    decision["source"] = decision.get("source","rule-based")
                    st.session_state.last_action = decision

                    result = backend_step({
                        "severity":   decision["severity"],
                        "team":       decision["team"],
                        "root_cause": decision["root_cause"],
                        "suppressed": decision.get("suppressed",[]),
                    })
                    if result:
                        st.session_state.result = result
                        st.session_state.episode_done = result.get("done", False)
                        info = result.get("info",{})
                        st.session_state.step_log.append({
                            "step":   step_n+1, "score": info.get("final_score",0),
                            "action": decision,  "reason": info.get("reason",""),
                        })
                        st.session_state.history.append({
                            "task":        task_id,
                            "score":       info.get("final_score",0),
                            "severity_ok": info.get("severity_correct",False),
                            "team_ok":     info.get("team_correct",False),
                            "rc_score":    info.get("root_cause_score",0),
                            "source":      decision.get("source","?"),
                        })
                    st.rerun()
        else:
            st.success("✅ Episode complete!")
            st.caption("Click **▶ Start Task** in the sidebar to start a new episode.")

    # Full routing table — shown after AI runs
    if st.session_state.last_action:
        st.divider()
        st.subheader("📋 Full Alert Routing Table — Sorted by Priority")
        noise_ids = st.session_state.result.get("info",{}).get("noise_ids",[]) \
                    if st.session_state.result else []
        render_routing_table(alerts, st.session_state.last_action, noise_ids)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — AI Decision Results
# ─────────────────────────────────────────────────────────────────────────────
with tab_results:
    if not st.session_state.result or not st.session_state.last_action:
        st.info("Run the AI agent first (go to **📡 Alerts & Routing** tab).")
    else:
        result = st.session_state.result
        info   = result.get("info",{})
        action = st.session_state.last_action

        col_score, col_decision = st.columns([1, 2], gap="large")

        with col_score:
            st.subheader("🎯 Score")
            render_score_breakdown(info, task_id)

        with col_decision:
            st.subheader("🤖 AI Triage Decision")
            d1, d2 = st.columns(2)

            with d1:
                sev = action["severity"]
                ok  = info.get("severity_correct", False)
                gt_sev = info.get("ground_truth",{}).get("severity","?")
                st.markdown(f'<div style="color:#212121;font-weight:700">Severity {"✅" if ok else "❌"}</div>', unsafe_allow_html=True)
                color = "#2e7d32" if ok else "#c62828"
                st.markdown(
                    f'<div style="font-size:2rem;font-weight:900;color:{color}">'
                    f'{SEV_ICON.get(sev,"")} {sev}</div>',
                    unsafe_allow_html=True
                )
                if not ok:
                    st.markdown(f'<div style="color:#546e7a;font-size:0.82rem">Expected: {gt_sev}</div>', unsafe_allow_html=True)

            with d2:
                team = action["team"]
                ok   = info.get("team_correct", False)
                gt_team = info.get("ground_truth",{}).get("team","?")
                st.markdown(f'<div style="color:#212121;font-weight:700">Routed To {"✅" if ok else "❌"}</div>', unsafe_allow_html=True)
                chip = TEAM_CHIP.get(team,"")
                st.markdown(f'<div style="margin-top:8px">{chip}</div>', unsafe_allow_html=True)
                if not ok:
                    st.markdown(f'<div style="color:#546e7a;font-size:0.82rem">Expected: {gt_team}</div>', unsafe_allow_html=True)

            st.divider()
            st.markdown('<div style="color:#212121;font-weight:700">🔍 Root Cause Analysis</div>', unsafe_allow_html=True)
            st.info(action.get("root_cause","N/A"))

            if task_id == "task_hard" and action.get("suppressed"):
                sup_list = ", ".join(action["suppressed"])
                st.markdown(f'<div style="color:#616161;font-size:0.88rem">🔇 Suppressed: <code style="color:#37474f">{sup_list}</code></div>', unsafe_allow_html=True)

            src = action.get("source","?")
            st.markdown(
                f'<div style="color:#546e7a;font-size:0.82rem;margin-top:8px">'
                f'{"🤖 LLM Agent" if src=="llm" else "📏 Rule-Based Agent"}</div>',
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown(f'<div style="color:#37474f;font-size:0.85rem"><strong>Grader feedback:</strong> {info.get("reason","N/A")}</div>', unsafe_allow_html=True)

        # Hard task step log
        if task_id == "task_hard" and st.session_state.step_log:
            st.divider()
            st.subheader("📜 Step-by-Step Log")
            for entry in st.session_state.step_log:
                with st.expander(f"Step {entry['step']} — Score: {entry['score']:.3f}"):
                    st.markdown(f'<div style="color:#212121"><strong>Severity:</strong> {entry["action"]["severity"]} &nbsp;|&nbsp; <strong>Team:</strong> {entry["action"]["team"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="color:#212121"><strong>Root Cause:</strong> {entry["action"]["root_cause"]}</div>', unsafe_allow_html=True)
                    if entry["action"].get("suppressed"):
                        st.markdown(f'<div style="color:#616161"><strong>Suppressed:</strong> {entry["action"]["suppressed"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="color:#546e7a;font-size:0.85rem">{entry["reason"]}</div>', unsafe_allow_html=True)

        with st.expander("📋 Raw API Response"):
            st.json(result)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — History
# ─────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.subheader("📈 Run History")
    render_history()


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.caption("🚨 Incident Triage AI")
c2.caption("Meta × HuggingFace Hackathon")
c3.caption("FastAPI + Streamlit + OpenAI")
c4.caption(f"Task: `{task_id}` · Backend: `{BACKEND}`")
