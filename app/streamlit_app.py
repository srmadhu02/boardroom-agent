"""
Boardroom Agent — Streamlit UI

A polished single-file Streamlit frontend for the Boardroom ADK Workflow.
Displays four persona critique cards, a color-coded verdict badge,
ranked concerns, and a HITL approve/reject panel when required.

Run with:
    uv run streamlit run app/streamlit_app.py
"""

import json
import textwrap
import time
from typing import Any

from dotenv import load_dotenv
load_dotenv()  # Load GOOGLE_API_KEY (and others) from .env before any ADK imports

import streamlit as st
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Boardroom — AI Decision Pressure-Test",
    page_icon="🏛️",
    layout="wide",
)

st.markdown(textwrap.dedent("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-primary: #0a0e1a;
    --bg-card: #111827;
    --bg-card-hover: #1a2235;
    --border-subtle: #1e293b;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --accent-vc: #8b5cf6;
    --accent-cfo: #f59e0b;
    --accent-growth: #10b981;
    --accent-customer: #3b82f6;
    --verdict-proceed: #10b981;
    --verdict-revise: #f59e0b;
    --verdict-kill: #ef4444;
}

/* Global overrides */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
}
.block-container {
    padding-top: 1.5rem !important;
}

/* Hide Streamlit header / footer */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

/* Persona cards */
.persona-card {
    background: linear-gradient(145deg, #111827, #1a2235);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 1.5rem;
    min-height: 220px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}
.persona-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.persona-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.persona-card.vc::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.persona-card.cfo::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.persona-card.growth::before { background: linear-gradient(90deg, #10b981, #34d399); }
.persona-card.customer::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }

.persona-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1rem;
}
.persona-emoji {
    font-size: 1.6rem;
    line-height: 1;
}
.persona-name {
    font-weight: 700;
    font-size: 0.95rem;
    letter-spacing: -0.01em;
}
.persona-name.vc { color: #a78bfa; }
.persona-name.cfo { color: #fbbf24; }
.persona-name.growth { color: #34d399; }
.persona-name.customer { color: #60a5fa; }

.persona-text {
    color: var(--text-secondary);
    font-size: 0.88rem;
    line-height: 1.65;
}

.persona-card.customer .persona-text h2 { color: #60a5fa; font-size: 0.95rem; font-weight: 700; margin: 0 0 0.75rem 0; line-height: 1.4; letter-spacing: -0.01em; }
.persona-card.growth .persona-text h2 { color: #34d399; font-size: 0.95rem; font-weight: 700; margin: 0 0 0.75rem 0; line-height: 1.4; letter-spacing: -0.01em; }
.persona-card.vc .persona-text h2 { color: #a78bfa; font-size: 0.95rem; font-weight: 700; margin: 0 0 0.75rem 0; line-height: 1.4; letter-spacing: -0.01em; }
.persona-card.cfo .persona-text h2 { color: #fbbf24; font-size: 0.95rem; font-weight: 700; margin: 0 0 0.75rem 0; line-height: 1.4; letter-spacing: -0.01em; }

/* Distinct styling for closing questions/paragraphs that appear after the bullet list */
.persona-text > ul + p {
    margin-top: 1.2rem;
    font-size: 0.85rem;
    font-style: italic;
    opacity: 0.9;
}

/* Verdict badge */
.verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1.4rem;
    border-radius: 100px;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.verdict-proceed {
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05));
    border: 1px solid rgba(16,185,129,0.4);
    color: #34d399;
}
.verdict-revise {
    background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05));
    border: 1px solid rgba(245,158,11,0.4);
    color: #fbbf24;
}
.verdict-kill {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05));
    border: 1px solid rgba(239,68,68,0.4);
    color: #f87171;
}

/* HITL panel */
.hitl-panel {
    background: linear-gradient(145deg, rgba(239,68,68,0.08), rgba(245,158,11,0.05));
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
}
.hitl-panel-content {
    color: #94a3b8;
    font-size: 0.88rem;
    line-height: 1.6;
}
.hitl-panel-content p {
    margin-bottom: 0.75rem;
}
.hitl-panel-content ul {
    margin-top: 0.1rem;
    margin-bottom: 0;
}
.hitl-panel-content li {
    margin-bottom: 0.4rem;
}

/* Concern row */
.concern-row {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.severity-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px; height: 28px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.8rem;
}
.severity-low { background: rgba(16,185,129,0.15); color: #34d399; }
.severity-med { background: rgba(245,158,11,0.15); color: #fbbf24; }
.severity-high { background: rgba(239,68,68,0.15); color: #f87171; }

/* Waiting / empty placeholder */
.placeholder-text {
    color: #475569;
    font-style: italic;
    font-size: 0.85rem;
    text-align: center;
    padding: 2rem 0;
}

/* Input styling */
.stTextArea textarea {
    background: #111827 !important;
    border: 1px solid #1e293b !important;
    color: #f1f5f9 !important;
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea textarea:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 2px rgba(139,92,246,0.2) !important;
}

/* Button styling */
div.stButton > button {
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em !important;
    transition: all 0.2s ease !important;
}
div.stButton > button:not(:disabled) {
    background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
    color: white !important;
}
div.stButton > button:not(:disabled):hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(139,92,246,0.4) !important;
}
div.stButton > button:disabled {
    background: #1e293b !important;
    color: #64748b !important;
    cursor: not-allowed !important;
    opacity: 0.7 !important;
}

/* Security warning */
.security-warning {
    background: linear-gradient(145deg, rgba(239,68,68,0.1), rgba(239,68,68,0.03));
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 12px;
    padding: 1.2rem;
    color: #f87171;
    font-weight: 500;
}
</style>
"""), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERSONA_META = {
    "vc_skeptic":   {"emoji": "🦈", "label": "VC Skeptic",    "css": "vc"},
    "cfo_risk":     {"emoji": "📊", "label": "CFO Risk",      "css": "cfo"},
    "growth_lead":  {"emoji": "🚀", "label": "Growth Lead",   "css": "growth"},
    "end_customer": {"emoji": "🧑‍💻", "label": "End Customer",  "css": "customer"},
}

DECISION_PREFIXES = {
    "Pitch":   "This is a startup pitch: ",
    "Hiring":  "This is a hiring decision: ",
    "Pricing": "This is a pricing decision: ",
    "Other":   "",
}

DECISION_PLACEHOLDERS = {
    "Pitch":   "e.g. We're launching a B2B SaaS tool that uses AI to automate expense reports for mid-market companies…",
    "Hiring":  "e.g. We want to hire a senior backend engineer at $180k/year, currently a team of 3 with 14 months of runway…",
    "Pricing": "e.g. We're raising prices from $10 to $15/month for our existing 2,000 subscribers…",
    "Other":   "e.g. Describe the business decision you want pressure-tested…",
}

APP_NAME = "boardroom_streamlit"


# ---------------------------------------------------------------------------
# Session-state initialization
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "session_service": InMemorySessionService(),
        "session_id": None,
        "runner": None,
        "persona_responses": {k: None for k in PERSONA_META},
        "verdict": None,
        "hitl_interrupt_id": None,
        "hitl_message": None,
        "hitl_resolved": False,
        "run_complete": False,
        "run_in_progress": False,
        "security_blocked": False,
        "security_message": "",
        "invocation_id": None,
        "current_round": 1,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_runner() -> Runner:
    """Return a reusable Runner (one per Streamlit session)."""
    if st.session_state.runner is None:
        st.session_state.runner = Runner(
            agent=root_agent,
            session_service=st.session_state.session_service,
            app_name=APP_NAME,
        )
    return st.session_state.runner


def _get_or_create_session(runner: Runner) -> str:
    """Create a fresh session for each run, unless we are in a continuing round."""
    if st.session_state.session_id and st.session_state.current_round > 1:
        return st.session_state.session_id

    session = st.session_state.session_service.create_session_sync(
        user_id="streamlit_user",
        app_name=APP_NAME,
    )
    st.session_state.session_id = session.id
    return session.id


def _extract_text(event: Event) -> str:
    """Pull text from an event's content.parts."""
    if event.content and event.content.parts:
        return "".join(p.text for p in event.content.parts if p.text)
    return ""


def _parse_verdict_from_text(text: str) -> dict | None:
    """Try to parse JSON verdict from synthesizer output text."""
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _run_agent(user_input: str):
    """Execute the Boardroom agent and collect results into session state."""
    runner = _get_runner()
    session_id = _get_or_create_session(runner)

    # Reset state
    st.session_state.persona_responses = {k: None for k in PERSONA_META}
    st.session_state.verdict = None
    st.session_state.hitl_interrupt_id = None
    st.session_state.hitl_message = None
    st.session_state.hitl_final_message = None
    st.session_state.hitl_resolved = False
    st.session_state.run_complete = False
    st.session_state.security_blocked = False
    st.session_state.security_message = ""
    st.session_state.invocation_id = None

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)],
    )

    events = list(runner.run(
        user_id="streamlit_user",
        session_id=session_id,
        new_message=message,
        run_config=RunConfig(streaming_mode=StreamingMode.NONE),
    ))

    # Process events
    for event in events:
        # Track invocation_id for potential resume
        if event.invocation_id:
            st.session_state.invocation_id = event.invocation_id

        author = event.author or ""
        text = _extract_text(event)

        # Check for security block
        if "flagged as a potential prompt injection" in (event.output if isinstance(event.output, str) else text):
            st.session_state.security_blocked = True
            st.session_state.security_message = event.output if isinstance(event.output, str) else text
            continue

        # Persona responses
        if author in PERSONA_META and text:
            st.session_state.persona_responses[author] = text

        # Synthesizer / verdict — stored by hitl_gate as event.output (a dict)
        if isinstance(event.output, dict) and "verdict" in event.output:
            st.session_state.verdict = event.output

        # Also try parsing synthesizer text if we got it
        if author == "synthesizer" and text and st.session_state.verdict is None:
            parsed = _parse_verdict_from_text(text)
            if parsed:
                st.session_state.verdict = parsed

        # HITL RequestInput
        if isinstance(event, RequestInput):
            st.session_state.hitl_interrupt_id = event.interrupt_id
            st.session_state.hitl_message = event.message
            continue
        elif event.content and event.content.parts:
            fc = event.content.parts[0].function_call
            if fc and fc.name == "adk_request_input":
                args = fc.args or {}
                st.session_state.hitl_interrupt_id = args.get("interruptId") or args.get("interrupt_id")
                st.session_state.hitl_message = args.get("message")
                continue

        # Final message from hitl_gate
        if event.node_info and event.node_info.path and "hitl_gate" in event.node_info.path:
            if isinstance(event.output, dict) and "verdict" in event.output:
                st.session_state.verdict = event.output

    # If no HITL needed, mark complete
    if st.session_state.hitl_interrupt_id is None:
        st.session_state.run_complete = True


def _resume_hitl(decision: str):
    """Resume the HITL gate with the user's approve/reject decision."""
    runner = _get_runner()
    interrupt_id = st.session_state.hitl_interrupt_id

    # Build the function-response message for resume
    resume_message = types.Content(
        role="user",
        parts=[types.Part(
            function_response=types.FunctionResponse(
                id=interrupt_id,
                name=interrupt_id,
                response={"result": decision},
            )
        )],
    )

    events = list(runner.run(
        user_id="streamlit_user",
        session_id=st.session_state.session_id,
        new_message=resume_message,
        run_config=RunConfig(streaming_mode=StreamingMode.NONE),
    ))

    # Process resume events
    for event in events:
        if isinstance(event.output, dict) and "verdict" in event.output:
            st.session_state.verdict = event.output
        if getattr(event, "message", None):
            st.session_state.hitl_final_message = event.message

    st.session_state.hitl_resolved = True
    st.session_state.hitl_interrupt_id = None
    st.session_state.run_complete = True
    
    if decision == "reject":
        st.session_state.current_round += 1


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_persona_card(key: str, placeholder_slots: dict):
    """Render a single persona card."""
    meta = PERSONA_META[key]
    response = st.session_state.persona_responses.get(key)

    import markdown as md
    import re
    if response:
        body_content = md.markdown(response)
        body_html = f'<div class="persona-text">{body_content}</div>'
    else:
        body_html = '<div class="placeholder-text">Awaiting analysis…</div>'

    st.markdown(textwrap.dedent(f"""
    <div class="persona-card {meta['css']}">
        <div class="persona-header">
            <span class="persona-emoji">{meta['emoji']}</span>
            <span class="persona-name {meta['css']}">{meta['label']}</span>
        </div>
        {body_html}
    </div>
    """), unsafe_allow_html=True)


def _render_verdict_badge(verdict_dict: dict):
    """Render the verdict badge."""
    verdict = verdict_dict.get("verdict", "").lower()
    summary = verdict_dict.get("summary", "")

    css_class = {
        "proceed": "verdict-proceed",
        "revise": "verdict-revise",
        "kill": "verdict-kill",
    }.get(verdict, "verdict-revise")

    icon = {"proceed": "✅", "revise": "⚠️", "kill": "🚫"}.get(verdict, "❓")

    st.markdown(textwrap.dedent(f"""
    <div style="display: flex; align-items: center; gap: 1rem; margin: 1.5rem 0;">
        <div class="verdict-badge {css_class}">{icon} {verdict.upper()}</div>
    </div>
    <div style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1rem;">
        {summary}
    </div>
    """), unsafe_allow_html=True)


def _render_concerns(verdict_dict: dict):
    """Render the ranked concerns in an expander."""
    comparison_summary = verdict_dict.get("comparison_summary", {})
    if comparison_summary:
        with st.expander("🔄 Round 2 Comparison Summary", expanded=True):
            resolved = comparison_summary.get("resolved", [])
            partially_resolved = comparison_summary.get("partially_resolved", [])
            unresolved = comparison_summary.get("unresolved", [])
            new_concerns = comparison_summary.get("new_concerns", [])
            
            if resolved:
                st.markdown("**✅ Resolved:**")
                for item in resolved:
                    st.markdown(f"- {item}")
            if partially_resolved:
                st.markdown("**⚠️ Partially Resolved:**")
                for item in partially_resolved:
                    st.markdown(f"- {item}")
            if unresolved:
                st.markdown("**❌ Unresolved:**")
                for item in unresolved:
                    st.markdown(f"- {item}")
            if new_concerns:
                st.markdown("**🆕 New Concerns:**")
                for item in new_concerns:
                    st.markdown(f"- {item}")

    concerns = verdict_dict.get("top_concerns", [])
    if not concerns:
        return

    with st.expander("📋 Ranked Concerns", expanded=True):
        for c in concerns:
            sev = c.get("severity", 0)
            sev_class = "severity-low" if sev <= 2 else ("severity-med" if sev <= 3 else "severity-high")
            raised = ", ".join(c.get("raised_by", []))
            concern_text = c.get("concern", "")
            fix = c.get("suggested_fix", "—")

            st.markdown(textwrap.dedent(f"""
            <div class="concern-row">
                <div style="display: flex; align-items: flex-start; gap: 0.8rem;">
                    <div class="severity-badge {sev_class}">{sev}</div>
                    <div style="flex: 1;">
                        <div style="color: #f1f5f9; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.3rem;">
                            {concern_text}
                        </div>
                        <div style="color: #64748b; font-size: 0.8rem; margin-bottom: 0.3rem;">
                            Raised by: <span style="color: #94a3b8;">{raised}</span>
                        </div>
                        <div style="color: #64748b; font-size: 0.8rem;">
                            Fix: <span style="color: #94a3b8;">{fix}</span>
                        </div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

# Title
round_badge = ""
if st.session_state.current_round > 1:
    round_badge = f'<div style="display: inline-block; background: #8b5cf6; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.9rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: 0.05em; text-transform: uppercase;">Round {st.session_state.current_round} – Revision Review</div>'

st.markdown(f"""<div style="text-align: center; padding: 0 0 1rem;">
<div style="font-size: 2.5rem; margin-bottom: 0.3rem;">🏛️</div>
{round_badge}
<h1 style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 2rem;
background: linear-gradient(135deg, #a78bfa, #60a5fa);
-webkit-background-clip: text; -webkit-text-fill-color: transparent;
margin: 0; letter-spacing: -0.03em;">
The Boardroom
</h1>
<p style="color: #64748b; font-size: 0.95rem; margin-top: 0.4rem;">
AI-powered decision pressure-testing with four adversarial personas
</p>
</div>""", unsafe_allow_html=True)

# Inputs are disabled while a run is in progress or HITL is awaiting resolution
_inputs_disabled = st.session_state.run_in_progress or (
    st.session_state.hitl_interrupt_id is not None and not st.session_state.hitl_resolved
)

# Input section
col_left, col_right = st.columns([3, 1])

with col_left:
    decision_type = st.radio(
        "Decision type:",
        options=list(DECISION_PREFIXES.keys()),
        horizontal=True,
        index=0,
        disabled=_inputs_disabled,
    )

    # Clear the text area when the user switches decision type
    if "prev_decision_type" not in st.session_state:
        st.session_state.prev_decision_type = decision_type
    if decision_type != st.session_state.prev_decision_type:
        st.session_state.prev_decision_type = decision_type
        st.session_state.user_input_text = ""

    user_text = st.text_area(
        "Describe your decision or pitch:",
        height=140,
        placeholder=DECISION_PLACEHOLDERS.get(decision_type, DECISION_PLACEHOLDERS["Other"]),
        key="user_input_text",
        disabled=_inputs_disabled,
    )

with col_right:
    st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)
    run_clicked = st.button("🏛️  Run the Boardroom", use_container_width=True, disabled=_inputs_disabled)

# ---------------------------------------------------------------------------
# Execute on button click
# ---------------------------------------------------------------------------

if run_clicked and user_text.strip():
    prefix = DECISION_PREFIXES.get(decision_type, "")
    st.session_state.pending_run_input = prefix + user_text.strip()
    st.session_state.run_in_progress = True
    st.rerun()  # Rerun immediately to send the disabled UI state to the browser

elif run_clicked and not user_text.strip():
    st.warning("Please enter a decision or pitch to pressure-test.")

# Execute the deferred run now that the UI is disabled
if st.session_state.get("pending_run_input"):
    input_to_run = st.session_state.pending_run_input
    st.session_state.pending_run_input = None  # Clear so it only runs once
    
    try:
        with st.spinner("The boardroom is deliberating…"):
            _run_agent(input_to_run)
    finally:
        # Guarantee this flag resets even if a queued frontend event aborts the script
        st.session_state.run_in_progress = False
        st.rerun()

# ---------------------------------------------------------------------------
# Security block display
# ---------------------------------------------------------------------------

if st.session_state.security_blocked:
    st.markdown(textwrap.dedent(f"""
    <div class="security-warning">
        🛡️ {st.session_state.security_message}
    </div>
    """), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Persona cards — staggered reveal
# ---------------------------------------------------------------------------

has_any_response = any(v is not None for v in st.session_state.persona_responses.values())

if (has_any_response or st.session_state.run_complete or st.session_state.hitl_interrupt_id) and not st.session_state.security_blocked:
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    cols = st.columns(4)
    persona_keys = ["end_customer", "growth_lead", "vc_skeptic", "cfo_risk"]

    for i, key in enumerate(persona_keys):
        with cols[i]:
            _render_persona_card(key, {})
            # Staggered reveal effect: brief pause between cards
            if st.session_state.persona_responses.get(key) is not None:
                time.sleep(0.15)

# ---------------------------------------------------------------------------
# Verdict & concerns
# ---------------------------------------------------------------------------

if st.session_state.verdict:
    st.markdown("---")
    _render_verdict_badge(st.session_state.verdict)
    _render_concerns(st.session_state.verdict)

# ---------------------------------------------------------------------------
# HITL panel
# ---------------------------------------------------------------------------

if st.session_state.hitl_interrupt_id and not st.session_state.hitl_resolved:
    display_msg = st.session_state.hitl_message or "This verdict requires human sign-off before finalizing."
    
    import markdown as md
    
    # Strip the inline plain-text header and CLI instructions, since the UI provides its own styled equivalents
    display_msg = display_msg.replace("⚠️ Human review required.", "").strip()
    display_msg = display_msg.replace("Reply 'approve' (or 'accept', 'yes', 'y') to finalize this verdict, or 'reject' (or anything else) to send it back for founder revision.", "").strip()

    # Enhance typography for the UI and force clear paragraphs
    display_msg = display_msg.replace("Verdict:", "**Verdict:**")
    display_msg = display_msg.replace("Summary:", "\n\n**Summary:**")
    display_msg = display_msg.replace("Concerns:\n", "\n\n**Concerns:**\n\n")
    
    msg_html = md.markdown(display_msg)

    st.markdown(f"""<div class="hitl-panel">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1rem;">
<span style="font-size: 1.5rem;">⚠️</span>
<span style="font-weight: 700; font-size: 1.1rem; color: #f87171;">
Human Review Required
</span>
</div>
<div class="hitl-panel-content">
{msg_html}
</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # Override button colors for approve (green) and reject (red)
    st.markdown(textwrap.dedent("""
    <style>
    div[data-testid="stHorizontalBlock"] div:nth-child(1) div.stButton > button:not(:disabled) {
        background: linear-gradient(135deg, #10b981, #059669) !important;
    }
    div[data-testid="stHorizontalBlock"] div:nth-child(1) div.stButton > button:not(:disabled):hover {
        box-shadow: 0 4px 16px rgba(16,185,129,0.4) !important;
    }
    
    div[data-testid="stHorizontalBlock"] div:nth-child(2) div.stButton > button:not(:disabled) {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    }
    div[data-testid="stHorizontalBlock"] div:nth-child(2) div.stButton > button:not(:disabled):hover {
        box-shadow: 0 4px 16px rgba(239,68,68,0.4) !important;
    }
    </style>
    """), unsafe_allow_html=True)

    hitl_col1, hitl_col2, _ = st.columns([1, 1, 2])

    with hitl_col1:
        if st.button("Approve", use_container_width=True, key="hitl_approve"):
            with st.spinner("Resuming with approval…"):
                _resume_hitl("approve")
            st.rerun()

    with hitl_col2:
        if st.button("Reject", use_container_width=True, key="hitl_reject"):
            with st.spinner("Resuming with rejection…"):
                _resume_hitl("reject")
            st.rerun()

# ---------------------------------------------------------------------------
# Final resolution message
# ---------------------------------------------------------------------------

if st.session_state.hitl_resolved:
    st.markdown("---")
    final_msg = st.session_state.get("hitl_final_message", "")
    
    if hasattr(final_msg, "parts"):
        final_msg_text = "".join(part.text for part in final_msg.parts if hasattr(part, "text") and part.text)
    else:
        final_msg_text = str(final_msg)

    if "human rejected" in final_msg_text.lower() or "rejected" in final_msg_text.lower():
        st.error(f"❌ {final_msg_text}")
    elif final_msg_text:
        st.success(f"✅ {final_msg_text}")
    else:
        st.success("✅ Human review complete — verdict finalized.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("""<div style="text-align: center; padding: 3rem 0 1rem; color: #334155; font-size: 0.75rem;">
Boardroom Agent • Built with Google ADK & Streamlit
</div>""", unsafe_allow_html=True)
