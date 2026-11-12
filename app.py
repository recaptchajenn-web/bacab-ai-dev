"""BACAB AI | structured recovery audit dashboard (SHARED + PLAN A + PLAN B).

PLAN A invokes the OpenAI Responses API only when explicitly selected by the operator.
All banking tools and customer data remain fictional local sandbox services.
"""
from __future__ import annotations

from html import escape
import json
import pandas as pd
import streamlit as st

from bacab_core.scenarios import SCENARIOS, SCENARIO_DETAILS, simulate_pair
from bacab_core.journey_viz import journey_steps, journey_html
from bacab_core.evaluators import audit_pair
from bacab_core.replay import load_fixture, import_trace_json
from bacab_core.config import load_policy, load_pricing
import tempfile
from pathlib import Path
from bacab_core.storage import save_audit, load_audit, list_audits, save_review, list_reviews, DB_DEFAULT
from bacab_core.deployment import live_agent_enabled, local_operator_mode
from bacab_core.reporting import audit_json_with_reviews, evidence_csv
from bacab_core.live_agent import run_live_pair, create_openai_client, DEFAULT_MODEL, LiveCaseExecutionError
from bacab_core.audit_view import selection_key, assert_run_matches_selection, safe_failure_detail, effective_auth_retries
from bacab_core.presentation import (policy_display, finding_display, duration_display,
                                     outcome_comparison_labels, outcome_comparison_card_html,
                                     equity_notice, pricing_display_rows)

st.set_page_config(page_title="BACAB AI | Recovery Equity Auditor", page_icon="🛡️", layout="wide")

# PUBLIC DEMO: live LLM disabled; per-session temporary audit store so visitors never share history.
LIVE_ENABLED = live_agent_enabled()
if local_operator_mode():
    DB_PATH = DB_DEFAULT
else:
    if "session_db_path" not in st.session_state:
        st.session_state["session_db_path"] = str(Path(tempfile.mkdtemp(prefix="bacab_session_")) / "bacab.sqlite3")
    DB_PATH = st.session_state["session_db_path"]
st.markdown("""
<style>
  .stApp {background: #F5F6FA; color: #161D34;}
  section[data-testid="stSidebar"] {background: #121C3B;}
  /* Sidebar: use light text only on the dark background, not on inputs/alerts. */
  section[data-testid="stSidebar"] {color:#EFF2FF;}
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
  section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
  section[data-testid="stSidebar"] [data-testid="stRadio"] label,
  section[data-testid="stSidebar"] [data-testid="stSlider"] label,
  section[data-testid="stSidebar"] [data-testid="stCheckbox"] label {color:#EFF2FF;}
  section[data-testid="stSidebar"] [data-baseweb="select"] > div,
  section[data-testid="stSidebar"] [data-baseweb="input"] > div {background:#F8F9FF!important;}
  section[data-testid="stSidebar"] [data-baseweb="select"] *,
  section[data-testid="stSidebar"] [data-baseweb="input"] input,
  section[data-testid="stSidebar"] input[type="password"] {color:#17254A!important;-webkit-text-fill-color:#17254A!important;}
  section[data-testid="stSidebar"] [data-testid="stAlert"] {background:#FFF5DB!important;}
  section[data-testid="stSidebar"] [data-testid="stAlert"] * {color:#62450A!important;}
  section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {background:#F8F9FF!important;}
  section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {color:#17254A!important;}
  section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] {color:#EFF2FF;}
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] :is(p,small,strong,span,h2,h3,h4) {color:#EFF2FF;}
  /* Input and alert foregrounds take precedence over the dark-sidebar copy style. */
  section[data-testid="stSidebar"] [data-baseweb="select"] *,
  section[data-testid="stSidebar"] [data-baseweb="input"] *,
  section[data-testid="stSidebar"] [data-testid="stAlert"] * {color:#17254A!important;}
  section[data-testid="stSidebar"] [data-testid="stAlert"] * {color:#62450A!important;}
  section[data-testid="stSidebar"] .stButton button {background:#6548D6;color:white;border:0;font-weight:700;}
  section[data-testid="stSidebar"] .stButton button:hover {background:#5338B8;color:white;}
  .block-container {max-width: 1440px; padding-top: 1.7rem; padding-bottom: 3rem;}
  div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px; background: white; border:1px solid #E3E7F1;}
  div[data-testid="stMetric"] {background:white; border-radius:12px; border:1px solid #E3E7F1; padding:14px; min-height:98px;}
  div[data-testid="stMetricLabel"] {font-weight:600; color:#4B5771;}
  div[data-testid="stMetricValue"] {color:#1C2550; font-weight:750;}
  /* Sprint 2.7: outcome comparison matches the size, border and visual weight of adjacent KPI cards. */
  .outcome-compare-card {background:#FFFFFF; border:1px solid #E3E7F1; border-radius:12px;
                         padding:14px; min-height:98px; box-sizing:border-box; width:100%;}
  .outcome-compare-title {font-size:13px; line-height:1.25; font-weight:600; color:#4B5771; margin-bottom:7px;}
  .outcome-compare-values {display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1.4fr);
                           align-items:end; column-gap:8px;}
  .outcome-compare-side {min-width:0; text-align:center;}
  .outcome-compare-side-label {font-size:11px; color:#4B5771; margin-bottom:2px; font-weight:500;}
  .outcome-compare-result {font-size:clamp(16px,1.6vw,24px); line-height:1.08; font-weight:800;
                           color:#1C2550; white-space:nowrap; letter-spacing:-0.03em;}
  .outcome-compare-divider {font-size:24px; line-height:1; font-weight:650; color:#293456; padding-bottom:1px;}
  @media (max-width:1100px) {
    .outcome-compare-card {padding:12px 10px;}
    .outcome-compare-values {column-gap:5px;}
    .outcome-compare-result {font-size:clamp(15px,1.9vw,21px);}
  }
  button[data-baseweb="tab"] {font-weight:650;}
  div[data-testid="stDataFrame"] {border-radius:11px; overflow:hidden;}
  .brandbar {background:linear-gradient(110deg,#101C3D,#1C2758); padding:18px 23px; border-radius:14px; color:white; margin-bottom:17px;}
  .brandbar h2 {margin:0; font-size:26px; color:white; line-height:1.1;}
  .brandbar p {margin:5px 0 0; color:#CED5F3; font-size:13px;}
  .brandpill {float:right; background:#35416B; border:1px solid #56648B; color:#F7F8FF; padding:7px 13px; border-radius:30px; font-size:11px;}
  .section-kicker {font-size:11px; letter-spacing:0.12em; font-weight:800; color:#7166BE; text-transform:uppercase; margin-bottom:6px;}
  .pairhead {font-size:17px; font-weight:750; color:#20294F; margin-bottom:12px;}
  .case-description {font-size:13px;color:#53607B; margin-top:3px; margin-bottom:12px;}
  .riskbox {border:1px solid #F3CFCD; background:#FFF0F1; padding:13px 16px; border-radius:11px; margin:9px 0 18px; color:#882C3A; font-size:13px;}
  .okbox {border:1px solid #B9E5CF; background:#EFFAF4; padding:13px 16px; border-radius:11px; margin:9px 0 18px; color:#1F6A45; font-size:13px;}
  .subcard {border:1px solid #E2E6F2; background:white; border-radius:12px; padding:14px 16px; margin:2px 0 11px;}
  .subcard h4 {font-size:14px; color:#25315A; margin:0 0 8px;}
  .subcard p {font-size:12px; color:#525F78; margin:3px 0;}
  .subcard strong {color:#283257;}
  .mini-pill {font-size:11px; font-weight:700; padding:4px 9px; border-radius:30px; background:#ECE9FF; color:#5840B5;}
  .muted-note {color:#626D86; font-size:12px;}
  /* Sprint 2.5: compact, read-only journey map driven by recorded trace events. */
  .journey-panel {background:#FFFFFF;border:1px solid #E1E5F0;border-radius:13px;padding:15px 18px;margin-bottom:9px;}
  .journey-label {font-weight:800;letter-spacing:.09em;font-size:12px;color:#243052;margin-bottom:16px;}
  .journey-label span {color:#76809B;font-weight:500;letter-spacing:0;}
  .journey-flow {border-left:2px solid #DFE5F1;margin-left:9px;padding-left:18px;}
  .journey-step {position:relative;padding:1px 0 12px 0;min-height:30px;}
  .journey-step::before {content:"";position:absolute;left:-25px;top:5px;width:11px;height:11px;border:2px solid #B6BFD0;border-radius:50%;background:#FFFFFF;}
  .journey-step.good::before {border-color:#24966D;background:#D6F3E5;}
  .journey-step.warning::before {border-color:#CA9628;background:#FFF0C8;}
  .journey-step.danger::before {border-color:#D35057;background:#FFE2E2;}
  .journey-step-title {font-weight:650;font-size:13px;color:#263151;line-height:1.45;}
  .journey-step.danger .journey-step-title {color:#AC303E;}
  .journey-step.good .journey-step-title {color:#196C51;}
  .journey-detail {font-size:11px;color:#65718C;margin-top:2px;line-height:1.4;}
  .journey-origin {font-size:10px;color:#8290A9;margin-top:2px;}

</style>
""", unsafe_allow_html=True)


def dollars(value: float, places: int = 5) -> str:
    return f"CAD ${value:,.{places}f}"


def delta_dollars(value: float) -> str:
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}CAD ${abs(value):,.5f}"


def diff(value: float, kind: str = "count") -> str:
    if kind == "cost":
        return f"{value:+.5f} CAD"
    if kind == "ms":
        return f"{value:+,.0f} ms"
    return f"{value:+,.0f}"


def event_refs(events: list[str]) -> str:
    return ", ".join(f"`{x}`" for x in events)


def labelled_table(rows: list[tuple[str, object, object]], title: str = "") -> None:
    if title:
        st.markdown(f"**{title}**")
    df = pd.DataFrame(rows, columns=["Measure", "Baseline", "Stress"])
    st.dataframe(df, hide_index=True, use_container_width=True)


def detail_card(title: str, description: str) -> None:
    st.markdown('<div class="subcard"><h4>' + escape(title) + '</h4><p>' + escape(description) + '</p></div>', unsafe_allow_html=True)


# THE SAME 3-MODE DATA INGESTION AND AUDIT ENGINE FROM SPRINT 1.5
with st.sidebar:
    st.markdown("### 🛡️ BACAB AI")
    st.caption("AI Agent Recovery Equity Auditor")
    st.divider()
    st.markdown("**EXECUTION MODE**")
    source_options = ["SHARED · Controlled simulation", "PLAN A · Live LLM banking agent", "PLAN B · Saved trace replay", "PLAN B · Import trace JSON"]
    if not LIVE_ENABLED:
        source_options.remove("PLAN A · Live LLM banking agent")
    source = st.radio("Evidence source", source_options, label_visibility="collapsed")
    if not LIVE_ENABLED:
        st.caption("Public demo: PLAN A live LLM execution is disabled. Use controlled simulation or validated trace replay.")
    st.markdown("**STRESS TEST**")
    scenario = st.selectbox("Scenario", list(SCENARIOS), index=2, format_func=lambda x: SCENARIOS[x], label_visibility="collapsed")
    detail = SCENARIO_DETAILS[scenario]
    st.caption(detail["explanation"])
    live_selected = LIVE_ENABLED and source.startswith("PLAN A")
    extra_retries = st.slider("Additional authentication retries (A only)", 0, 2, 0,
                              disabled=(scenario != "technical_outage" or
                                        not (source.startswith("SHARED") or live_selected)),
                              help=("In PLAN A, controls extra automatic faulty-controller retries "
                                    "after the live agent initiates verification. "
                                    "These are NOT LLM-selected calls."))
    if live_selected and scenario == "technical_outage":
        st.caption(f"Plan A retry-controller test: {4 + extra_retries} automatic failed authentication "
                   "attempts if the agent initiates phone verification. "
                   "The faulty controller blocks the approved handoff. "
                   "Change the slider, then click Run BACAB audit again.")
    if live_selected:
        st.warning("LIVE API calls incur charges. All bank tools remain fictional. Results may vary; replay remains available.")
        api_key_input = st.text_input("OpenAI API key (this session only)", type="password",
                                      help="Used for this local run only; not saved in audit records or written to disk. Alternatively configure OPENAI_API_KEY in your local environment.")
        model_choice = st.selectbox("Live model", ["gpt-6-luna", "gpt-6.1-terra"],
                                    help="Luna is the lowest-cost default. Requires API billing and model access.")
        live_turn_limit = st.slider("Maximum model calls per customer", 4, 9, 8)
        live_charge_consent = st.checkbox(f"I authorize this test (up to {2 * live_turn_limit} billed model requests)", value=False)
    else:
        api_key_input = ""
        model_choice = DEFAULT_MODEL
        live_turn_limit = 8
        live_charge_consent = False
    uploaded = st.file_uploader("Upload matched trace JSON", type=["json"], disabled=source != "PLAN B · Import trace JSON")
    run_clicked = st.button("▶ Run BACAB audit", type="primary", use_container_width=True)
    st.divider()
    st.caption("🔒 All bank tools are fictional. PLAN A sends standardized fictional prompts and sandbox tool outputs to the selected model; the other modes operate offline.")

# A disabled Streamlit slider can retain its old value on a scenario switch.
# Never pass Scenario A retries into B/C/control; doing so raises ValueError.
effective_retries = effective_auth_retries(scenario, extra_retries)

# IMPORTANT: Streamlit session state survives widget changes and failed API runs.
# Never let a stale Scenario C audit masquerade as a newly selected A/B run.
# Keep the key out of state fingerprints, diagnostics, and audit records.
current_selection = selection_key(
    source, scenario, effective_retries,
    model=model_choice if live_selected else "",
    model_call_limit=live_turn_limit if live_selected else 0,
)
if st.session_state.get("active_selection") != current_selection:
    st.session_state["active_selection"] = current_selection
    st.session_state.pop("audit", None)
    st.session_state.pop("audit_controls", None)
    st.session_state.pop("audit_origin", None)
    st.session_state.pop("audit_record_id", None)
    st.session_state.pop("last_run_error", None)

st.markdown('''<div class="brandbar"><span class="brandpill">Sprint 2.7.1 · Live / Replay / Synthetic</span>
<h2>🛡️ BACAB AI <span style="font-weight:400;color:#CAD0F7">| Agent Recovery Equity Auditor</span></h2>
<p>One agent workflow. Three stress tests. Evidence-based operational, equity and economic assurance.</p></div>''', unsafe_allow_html=True)

if run_clicked:
    # Clear previous results BEFORE any paid API calls. A partially failed pair
    # must never leave another scenario's old result on screen.
    st.session_state.pop("audit", None)
    st.session_state.pop("audit_controls", None)
    st.session_state.pop("audit_origin", None)
    st.session_state.pop("audit_record_id", None)
    st.session_state.pop("last_run_error", None)
    try:
        if source.startswith("SHARED"):
            audit_result = audit_pair(simulate_pair(scenario, extra_retries=effective_retries))
        elif source.startswith("PLAN A"):
            if not LIVE_ENABLED:
                raise ValueError("PLAN A live execution is disabled in this public demo.")
            if not live_charge_consent:
                raise ValueError("Confirm the API billing checkbox before running PLAN A.")
            with st.spinner("PLAN A: executing two bounded LLM agent journeys with fictional bank tools..."):
                client = create_openai_client(api_key=api_key_input)
                audit_result = audit_pair(run_live_pair(scenario, client=client, model=model_choice,
                                                        max_model_calls=live_turn_limit,
                                                        extra_retries=effective_retries))
        elif "Saved" in source:
            audit_result = load_fixture(scenario)
        else:
            if uploaded is None:
                raise ValueError("Select a trace JSON file first.")
            audit_result = import_trace_json(uploaded.getvalue().decode("utf-8"))
        # Validate report identity before local persistence or presentation.
        assert_run_matches_selection(audit_result, source, scenario)
        record_id = save_audit(audit_result, DB_PATH)
        st.session_state["audit_record_id"] = record_id
        st.session_state["audit"] = audit_result
        st.session_state["audit_controls"] = current_selection
        st.session_state["audit_origin"] = "new_run"
        st.success("Audit evaluated and stored locally. Select the sections below to examine the evidence.")
    except LiveCaseExecutionError as exc:
        # Model usage may be charged even when the second journey fails.
        status = f" / HTTP {exc.http_status}" if exc.http_status else ""
        if exc.http_status == 401:
            # One credential/authorization issue affects ALL scenarios; don't imply
            # that retry-controller or fairness detector code caused authentication.
            st.session_state["last_run_error"] = (
                f"PLAN A stopped before completing {SCENARIOS[scenario]}. "
                f"The {exc.variant.upper()} journey received AuthenticationError / HTTP 401. "
                "OpenAI rejected the API credential. Stop live retries. Check whether "
                "the key was revoked or replaced, paste a current key from the intended BACAB "
                "project into the masked field, and confirm Responses permission. "
                "No audit was produced or saved; earlier requests in a partial run may have usage. "
                "Your previous audits remain in Saved History. Never share the secret key."
            )
        else:
            st.session_state["last_run_error"] = (
                f"PLAN A did NOT complete Scenario {scenario.upper()} ({SCENARIOS[scenario]}). "
                f"The {exc.variant.upper()} journey failed ({exc.cause_type}{status}). "
                "No audit was produced or saved. Some live API requests may still have been billed. "
                "Check API permissions, model access and provider usage; the previous audit is available only in Saved History."
            )
    except (ValueError, KeyError, UnicodeError, OSError, TypeError, json.JSONDecodeError) as exc:
        # Show safe local validation failures, not untrusted provider bodies.
        st.session_state["last_run_error"] = (
            f"Scenario {SCENARIOS.get(scenario, scenario)} was NOT completed. "
            f"Validation error: {safe_failure_detail(exc)}. No previous report is displayed."
        ) if source.startswith("PLAN A") else f"Could not complete audit: {exc}"
    except Exception as exc:
        # Never echo raw network exception bodies which might contain secrets.
        st.session_state["last_run_error"] = (
            f"PLAN A did NOT complete Scenario {SCENARIOS.get(scenario,scenario)} "
            f"({safe_failure_detail(exc)}). Some API requests may have been billed. "
            "No previous report will be displayed."
        ) if source.startswith("PLAN A") else f"Unexpected audit error ({type(exc).__name__})."

with st.expander("📂 Load previous audit from local SQLite history" if local_operator_mode()
                 else "📂 Load previous audit from this browser session"):
    history = list_audits(DB_PATH)
    if history:
        options = {f"{a['created_utc'][:19]}  ·  {a['scenario_id']}  ·  {a['mode']}  ·  {a['pair_id'][:12]}": a["pair_id"] for a in history}
        selected = st.selectbox("Saved audit", list(options))
        if st.button("Open saved audit"):
            st.session_state["audit"] = load_audit(options[selected], DB_PATH)
            st.session_state["audit_origin"] = "history"
            st.session_state["audit_record_id"] = options[selected]
            st.session_state["last_run_error"] = None
    else:
        st.caption("There are no saved audits yet.")

audit = st.session_state.get("audit")
if not audit:
    if st.session_state.get("last_run_error"):
        st.error(st.session_state["last_run_error"])
    else:
        st.info(f"Ready for **{SCENARIOS[scenario]}** in **{source}**. "
                "Click **Run BACAB audit** to produce a fresh result; existing audits remain in Saved History. "
                "For PLAN A, this action can incur API charges.")
    st.stop()
if st.session_state.get("audit_origin") == "history":
    st.warning("SAVED HISTORY: This is a previously completed audit, not a new result for the current sidebar controls. "
               "Its actual scenario and evidence source are displayed below. Click Run BACAB audit for a fresh test.")
else:
    # Defend against out-of-band state mutation or a corrupt persisted audit.
    if st.session_state.get("audit_controls") != current_selection:
        st.error("Safety check: this report does not correspond to the currently selected controls. Run a new audit.")
        st.stop()
    try:
        assert_run_matches_selection(audit, source, scenario)
    except ValueError:
        st.error("Safety check: audit scenario or mode does not match the selection. Result hidden.")
        st.stop()
if audit.get("schema_version") != "0.2":
    st.warning("This saved audit uses the previous incompatible schema. Run a new Sprint 1.5.1 audit.")
    st.stop()

b, s, cmp = audit["metrics"]["baseline"], audit["metrics"]["stress"], audit["comparison"]
run_info = {r["variant"]: r for r in audit["runs"]}
scenario_name = SCENARIOS.get(audit["scenario_id"], audit["scenario_id"])
# Evidence provenance is always visible, even if a report is opened from history.
st.caption(f"REPORT IDENTITY · {scenario_name} · source={audit.get('mode', 'unknown')} "
           f"· pair={audit.get('pair_id', 'unknown')} · "
           f"{'SAVED HISTORY' if st.session_state.get('audit_origin') == 'history' else 'NEWLY COMPLETED RUN'}")
st.markdown('<div class="section-kicker">Scenario report · ' + (
    "Live LLM tool execution / fictional bank" if audit.get("mode") == "live_openai" else
    "Historical trace re-evaluation / no new LLM calls" if audit.get("mode") == "trace_replay" else
    "Synthetic matched-pair evaluation"
) + '</div>', unsafe_allow_html=True)
if audit.get("mode") == "live_openai":
    st.info("PLAN A: the LLM selects ordinary banking tool calls; an injected workflow controller may "
            "execute additional automatic tool retries in Scenario A. Those retries are marked separately "
            "and are NOT model-selected. Bank, customers and faults are fictional; CAD rates are "
            "hypothetical, even when tokens are API-reported.")
    if audit.get("scenario_id") == "technical_outage":
        stress_run = next(r for r in audit["runs"] if r["variant"] == "stress")
        fault_count = sum(1 for e in stress_run["events"] if e["event_type"] == "tool_result" and
                          e.get("metadata", {}).get("initiated_by") == "faulty_retry_controller")
        if fault_count:
            st.warning(f"Controlled workflow fault ACTIVATED: {fault_count} authentication attempts "
                       "originated from the injected retry controller, not the LLM.")
        else:
            st.warning("Controlled workflow fault NOT ACTIVATED: the live agent did not reach "
                       "the trigger point. Inspect the execution trace or use SHARED replay for this test.")
st.subheader(scenario_name)
if str(audit.get("fixture_provenance", "")).startswith("User-supplied"):
    st.caption("Imported JSON has been structurally validated and independently re-evaluated. "
               "BACAB does not authenticate the original event source or prove completeness. "
               "Import only fictional/sanitized test traces; do not upload customer records.")
st.markdown('<div class="case-description">' + escape(str(run_info["stress"]["metadata"].get("comparison_caveat", "Controlled synthetic comparison."))) + '</div>', unsafe_allow_html=True)

# Present a conservative evidence-based signal without classifying operational
# outage tests as demographic discrimination.
concern = equity_notice(audit)
if concern["kind"] == "none":
    st.markdown('<div class="okbox"><strong>' + escape(concern["title"]) +
                '</strong><p>' + escape(concern["description"]) + '</p></div>', unsafe_allow_html=True)
else:
    st.warning("⚖ " + concern["title"])
    st.write(concern["description"])
    if concern["evidence_ids"]:
        st.caption("Supporting event IDs: " + ", ".join(concern["evidence_ids"]))
    st.caption(concern["limitation"])

overview, findings_tab, costs_tab, trace_tab, review_tab = st.tabs([
    "▣ Overview", "⚑ Findings & policy", "◫ Cost analysis (CAD)", "⌁ Execution traces", "✓ Human review & export"
])

with overview:
    st.markdown("### Recovery outcomes")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        st.metric("BASELINE · " + b["display_label"], b["outcome"].replace("_", " ").title())
    with col2:
        st.metric("STRESS · " + s["display_label"], s["outcome"].replace("_", " ").title())
    with col3:
        baseline_status, stress_status = outcome_comparison_labels(b, s)
        st.markdown(outcome_comparison_card_html(baseline_status, stress_status),
                    unsafe_allow_html=True)
    st.caption("A successful human handoff is a safe recovery *path*, not proof that the customer's account was restored.")
    if audit.get("scenario_id") == "technical_outage":
        if b["authentication_over_limit_count"]:
            st.warning(f"Baseline policy violation: {b['authentication_over_limit_count']} excess auth attempts. "
                       "A successful final handoff does not erase an earlier retry violation.")
        elif audit.get("mode") == "live_openai":
            st.success("Baseline retry-limit check: no authentication attempts beyond the policy limit. "
                       "When the live baseline reaches two failed attempts, the policy guard provides an approved handoff.")

    st.markdown("### Key differences · Stress minus baseline")
    rows = st.columns(3)
    with rows[0]:
        st.metric("Authentication attempts", diff(s["authentication_attempt_count"] - b["authentication_attempt_count"]))
    with rows[1]:
        st.metric("Authentication failures", diff(s["authentication_failure_count"] - b["authentication_failure_count"]))
    with rows[2]:
        st.metric("Attempts exceeding policy", diff(s["authentication_over_limit_count"] - b["authentication_over_limit_count"]))
    rows2 = st.columns(3)
    with rows2[0]:
        st.metric("Difference in customer action requests", diff(s["customer_prompts_requested"] - b["customer_prompts_requested"]))
    with rows2[1]:
        timing_label, timing_explanation = duration_display(audit)
        st.metric(timing_label,
                  diff(s["recovery_latency_ms"] - b["recovery_latency_ms"], "ms"))
    with rows2[2]:
        st.metric("Direct execution cost", delta_dollars(s["direct_execution_cost_cad"] - b["direct_execution_cost_cad"]))
    st.caption("Authentication attempts, failed attempts and over-limit attempts overlap: do NOT sum them. "
               "Customer action requests are tool-recorded requests/offers, not verified customer completions. "
               "Equal request counts do not imply equal access or recovery outcomes. " + timing_explanation +
               " All CAD prices are hypothetical assumptions.")

    left, right = st.columns([1.6, 1])
    with left:
        with st.container(border=True):
            st.markdown('**Journey comparison**')
            rows = [
                ("Language", b["language"].upper(), s["language"].upper()),
                ("Outcome", b["outcome"], s["outcome"]),
                ("Safe recovery path", "Yes" if b["safe_resolution"] else "No", "Yes" if s["safe_resolution"] else "No"),
                ("Usable human handoff", "Yes" if b["usable_handoff"] else "No", "Yes" if s["usable_handoff"] else "No"),
                ("Authentication attempts", b["authentication_attempt_count"], s["authentication_attempt_count"]),
                ("Authentication failures", b["authentication_failure_count"], s["authentication_failure_count"]),
                ("Excess attempts beyond policy", b["authentication_over_limit_count"], s["authentication_over_limit_count"]),
                ("Agent tool results", b["agent_tool_result_count"], s["agent_tool_result_count"]),
                ("Tool errors", b["tool_error_count"], s["tool_error_count"]),
                ("Unusable channel offers", b["unusable_channel_offers"], s["unusable_channel_offers"]),
                ("Customer action requests", b["customer_prompts_requested"], s["customer_prompts_requested"]),
                ("Confirmed customer actions", "Not measured", "Not measured"),
            ]
            labelled_table(rows)
    with right:
        with st.container(border=True):
            st.markdown('**Agent execution overhead**')
            st.write(f"{diff(s['agent_tool_result_count']-b['agent_tool_result_count'])} tool executions (net)")
            st.write(f"{diff(s['tool_error_count']-b['tool_error_count'])} tool errors (net)")
            st.write(f"{diff(s['loop_count']-b['loop_count'])} excess/repeated events (net)")
            st.caption("Net tool executions need not equal the difference in authentication attempts: the baseline may include a successful escalation tool call.")
        with st.container(border=True):
            st.markdown('**Customer recovery burden**')
            st.write(f"{diff(s['customer_prompts_requested']-b['customer_prompts_requested'])} difference in customer action requests")
            st.write(f"{diff(s['unusable_channel_offers']-b['unusable_channel_offers'])} unusable channel offers")
            st.write("Actual customer action completions: **not instrumented**")
            st.caption("These are tool-recorded requests, not completed customer actions. Zero difference "
                       "does NOT mean equal customer burden; an inaccessible channel or missing assistance "
                       "can still leave the customer unresolved.")
        with st.container(border=True):
            st.markdown('**Policy and remediation**')
            stress_findings = [f for f in audit["findings"] if f["variant"] == "stress" and f["finding_type"] != "TOOL_FAILURE"]
            st.write(f"{len(stress_findings)} stress-path findings requiring triage")
            if stress_findings:
                priorities = sorted(stress_findings, key=lambda f: ["critical", "high", "medium", "low"].index(f["severity"]))
                st.markdown("**Top priority:** " + finding_display(priorities[0]["finding_type"]))
                st.caption(priorities[0]["recommended_fix"])
            else:
                st.caption("No policy deviation found in the stress path.")
    st.markdown("### Recovery journey · trace-based visual")
    st.caption("This visual shows recorded tool results and controller transitions, not hidden LLM reasoning. "
               "SHARED and saved fixtures are simulated; PLAN A uses a live model with fictional banking tools. "
               "The workflow may differ from a previously saved audit.")
    vis_left, vis_right = st.columns(2)
    for vis_col, variant_key in ((vis_left, "baseline"), (vis_right, "stress")):
        with vis_col:
            observed_run = run_info[variant_key]
            steps = journey_steps(observed_run, max_auth_attempts=load_policy()["max_auth_attempts"])
            st.markdown(journey_html(steps, variant=variant_key,
                                     language=observed_run.get("cohort_language", "")),
                        unsafe_allow_html=True)
    with st.expander("Inspect events behind the journey visual"):
        visual_rows = []
        for variant_key in ("baseline", "stress"):
            for step in journey_steps(run_info[variant_key], max_auth_attempts=load_policy()["max_auth_attempts"]):
                if step.get("event_id"):
                    visual_rows.append({"Journey": variant_key.title(), "Step": step["label"],
                                        "Event ID": step["event_id"], "Tool call ID": step["tool_call_id"],
                                        "Initiated by": step["initiated_by"]})
        if visual_rows:
            st.dataframe(pd.DataFrame(visual_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No trace events available for this visual.")
    st.markdown("### Assurance lenses")
    a1, a2, a3 = st.columns(3)
    with a1:
        detail_card("⚙ Operational", "Tool failures, attempts, evidence-linked excess retries, escalation and simulated latency.")
    with a2:
        detail_card("⚖ Recovery equity", "Matched journey outcomes, usable options and additional customer-facing burden, subject to scenario controls.")
    with a3:
        detail_card("$ Economic impact", "Hypothetical CAD direct cost and trace-linked cost of flagged unnecessary operations. No verified savings or ROI.")

with findings_tab:
    st.markdown("### Evidence-linked findings")
    rules = load_policy()["policy_rules"]
    st.caption(f"Shared policy: {audit['policy_version']} · Finding severity indicates triage priority, not a regulatory judgment.")
    filters = st.multiselect("Filter by", ["baseline", "stress"], default=["baseline", "stress"], format_func=lambda x: x.title())
    findings_visible = [f for f in audit["findings"] if f["variant"] in filters]
    if not findings_visible:
        st.success("No findings for the selected journey(s).")
    for f in findings_visible:
        heading = f"{f['severity'].upper()} · {finding_display(f['finding_type'])} · {f['variant'].title()}"
        with st.expander(heading, expanded=f["severity"] in {"critical", "high"}):
            st.write(f["explanation"])
            st.markdown("**Observed evidence IDs:** " + event_refs(f["observed_evidence_ids"]))
            st.markdown("**Applicable policies:** " + (", ".join(policy_display(rule_id) for rule_id in f["policy_rule_ids"]) if f["policy_rule_ids"] else "None asserted — observed incident only"))
            st.markdown("**Proposed remediation (human approval required):** " + f["recommended_fix"])
            st.caption(f["limitations"])
    with st.expander("View approved synthetic recovery policy"):
        for key, val in rules.items():
            st.markdown(f"**{policy_display(key)}:** {val}")
    st.caption("A handled tool error is an observed incident, not necessarily a policy violation. A controlled one-pair difference is not proof of demographic bias.")

with costs_tab:
    st.markdown("### Economic impact · CAD (illustrative)")
    st.warning("CAD prices are hypothetical, not provider bills, FX conversions, or realized savings. In PLAN A, token counts may be API-reported but these CAD rates and sandbox tool charges are still illustrative.")
    cost_rows = []
    for run in audit["runs"]:
        label = run["variant"]
        evs = run["events"]
        llm_cost = sum(float(e.get("cost_cad") or 0) for e in evs if e["event_type"] == "llm_response")
        tool_cost = sum(float(e.get("cost_cad") or 0) for e in evs if e["event_type"] == "tool_result")
        cost_rows.append([label.title(), dollars(llm_cost), dollars(tool_cost), dollars(audit["metrics"][label]["direct_execution_cost_cad"]),
                          dollars(audit["metrics"][label]["potentially_avoidable_direct_cost_cad"])])
    st.dataframe(pd.DataFrame(cost_rows, columns=["Journey", "LLM decisions (est.)", "Tool executions (est.)", "Direct total (CAD)", "Flagged unnecessary ops (CAD)"]),
                 use_container_width=True, hide_index=True)
    st.metric("Stress − baseline · Direct execution cost", delta_dollars(s["direct_execution_cost_cad"] - b["direct_execution_cost_cad"]))
    if not s["safe_resolution"] and s["direct_execution_cost_cad"] <= b["direct_execution_cost_cad"]:
        st.info("A failed journey may be cheaper in direct API cost because service was not delivered. Lower direct cost does not equal positive ROI or successful recovery.")
    st.caption("Flagged unnecessary-operation costs include explicit trace-linked event and model-cost shares only. "
               "They are not verified savings. Customer time, human support, infrastructure and downstream resolution are excluded.")
    for path in ("baseline", "stress"):
        rows = audit["metrics"][path].get("flagged_unnecessary_operations_cost_breakdown", [])
        with st.expander(f"Inspect {path.title()} flagged-cost evidence ({len(rows)} components)"):
            if rows:
                readable_cost_rows = [
                    {**row, "policy_rule_id": policy_display(row["policy_rule_id"])} for row in rows
                ]
                st.dataframe(pd.DataFrame(readable_cost_rows), use_container_width=True, hide_index=True)
                st.caption("Each row shows a priced trace event. The policy reference and tool call ID explain "
                           "why it was flagged and who initiated it. LLM costs are allocated only through "
                           "explicit tool-call links, never because an event happened nearby.")
            else:
                st.info("No evidence-linked unnecessary operations priced in this journey.")
    with st.expander("How costs are calculated", expanded=False):
        pricing = load_pricing()
        st.dataframe(pd.DataFrame(pricing_display_rows(pricing), columns=["Cost assumption", "Illustrative amount"]),
                     hide_index=True, use_container_width=True)
        st.caption("All prices are hypothetical CAD demonstration assumptions, not current provider "
                   "charges, bank invoices, currency conversions or established ROI. "
                   "Input/output token prices are per ONE MILLION tokens; tool price is per single execution. "
                   "The JSON configuration is kept for reproducibility.")
        with st.expander("Advanced · Inspect/export pricing JSON"):
            st.json(pricing)
            st.download_button("Download pricing assumptions JSON",
                               data=json.dumps(pricing, ensure_ascii=False, indent=2),
                               file_name="bacab_pricing_assumptions.json", mime="application/json")

with trace_tab:
    st.markdown("### Execution evidence")
    selected_run = st.radio("Journey", ["baseline", "stress"], horizontal=True, format_func=lambda v: v.title())
    run = run_info[selected_run]
    st.caption(f"{run['metadata'].get('display_label', selected_run.title())} · Language: {'French' if run['cohort_language']=='fr' else 'English'} · Run ID: {run['run_id']}")
    display_columns = ["sequence", "event_id", "actor", "event_type", "tool_name", "tool_call_id", "initiated_by", "status", "error_code", "attempt", "customer_action_required", "verification_valid_before", "duration_ms", "cost_cad"]
    st.dataframe(pd.DataFrame([{**{key: e.get(key) for key in display_columns},
                               "initiated_by": e.get("metadata", {}).get("initiated_by", "not_recorded")}
                              for e in run["events"]]),
                 use_container_width=True, hide_index=True)
    st.caption(timing_explanation + " The timing label follows the original trace provenance, "
               "even when imported through PLAN B. All CAD rates remain hypothetical. "
               "Evidence IDs link findings to specific events.")
    with st.expander("Inspect raw execution trace JSON"):
        st.json(run)

with review_tab:
    st.markdown("### Human review and audit evidence")
    st.caption("Review decisions confirm or reject an audit *finding*. They do not authorize a code change or automatically modify an agent.")
    if not audit["findings"]:
        st.info("No findings to review in this audit.")
    else:
        chosen_f = st.selectbox("Finding to review", audit["findings"],
                                format_func=lambda f: f"{f['finding_type'].replace('_',' ').title()} · {f['variant']}")
        decision_label = st.selectbox("Review decision", ["Needs investigation", "Finding confirmed", "Finding rejected"])
        decision = {"Needs investigation":"needs_investigation", "Finding confirmed":"approved", "Finding rejected":"rejected"}[decision_label]
        review_note = st.text_area("Reviewer notes", max_chars=2000)
        if st.button("Save finding review"):
            save_review(st.session_state.get("audit_record_id") or audit["pair_id"],
                        chosen_f["finding_id"], decision, review_note, DB_PATH)
            st.success("Review saved locally. No agent workflow was modified.")
    reviews = list_reviews(st.session_state.get("audit_record_id") or audit["pair_id"], DB_PATH)
    if reviews:
        st.markdown("**Recorded reviews**")
        st.dataframe(pd.DataFrame(reviews), use_container_width=True, hide_index=True)
    st.divider()
    st.download_button("↓ Complete audit + reviews (JSON)", audit_json_with_reviews(audit, reviews),
                       file_name=f"bacab_{audit['scenario_id']}_audit.json", mime="application/json")
    st.download_button("↓ Trace evidence (CSV)", evidence_csv(audit),
                       file_name=f"bacab_{audit['scenario_id']}_trace.csv", mime="text/csv")
    st.caption("Exports contain fictional bank data only. PLAN A and imported live traces can include "
               "real model execution metadata (not API keys). All displayed money is hypothetical CAD, "
               "and provenance remains explicit.")

st.caption(f"Source: {audit['mode']} · Policy: {audit['policy_version']} · Currency: CAD (hypothetical prices) · One controlled pair, not statistical evidence of population bias.")
