# -*- coding: utf-8 -*-
"""
Boardroom — an ADK 2.0 graph Workflow agent.

Graph shape:
    START ──> vc_skeptic     ─┐
    START ──> cfo_risk        ├─> persona_join (JoinNode) ──> synthesizer ──> hitl_gate
    START ──> growth_lead     │
    START ──> end_customer  ──┘

hitl_gate pauses (RequestInput) only when the verdict is "kill" or any
concern has severity >= HIGH_SEVERITY_THRESHOLD; otherwise it finalizes
immediately. This mirrors the expense-approval HITL escalation pattern.

Run modes:
  - `agents-cli playground` for interactive local testing.
  - Each run takes a single text input: the pitch/decision to pressure-test.
"""

import json
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow, node

# NOTE: JoinNode's import path is UNCONFIRMED in this project's installed
# ADK version. The public docs (adk.dev/graphs/routes) show:
#     from google.adk.workflow import JoinNode
# but the scaffold-generated reference file (agent_runtime_app.py) only
# demonstrates a simple sequential 2-node graph, not a parallel fan-out, so
# this import has NOT been verified against your actual installed package.
# If this import fails, ask Antigravity (once quota allows) to locate the
# correct JoinNode path for the installed google-adk version, e.g.:
#   "Find where JoinNode is defined in the installed google-adk package
#    and tell me the correct import path."
from google.adk.workflow import JoinNode

from .config import HIGH_SEVERITY_THRESHOLD, MODEL_NAME


# ---------------------------------------------------------------------------
# Tool: real runway math for the CFO persona (not LLM-estimated)
# ---------------------------------------------------------------------------

def calculate_runway(monthly_burn: float, current_cash: float) -> dict:
    """Compute months of runway remaining and a risk tier.

    Args:
        monthly_burn: Net cash spent per month (positive number).
        current_cash: Cash currently in the bank.

    Returns:
        dict with months_remaining (float) and risk_level (str).
    """
    if monthly_burn <= 0:
        return {"months_remaining": 999.0, "risk_level": "healthy"}

    months_remaining = round(current_cash / monthly_burn, 1)

    if months_remaining > 12:
        risk_level = "healthy"
    elif months_remaining >= 6:
        risk_level = "tight"
    else:
        risk_level = "critical"

    return {"months_remaining": months_remaining, "risk_level": risk_level}


# ---------------------------------------------------------------------------
# Persona nodes — all four run in parallel from START
# ---------------------------------------------------------------------------

vc_skeptic = LlmAgent(
    name="vc_skeptic",
    model=MODEL_NAME,
    instruction="""You are a Series A VC who has personally sat through 500 pitches
this year and is bored by all of them. You are reviewing a business decision or
pitch described by the user.

Always push on exactly these three things:
1. What is the ACTUAL unfair advantage / wedge — not "we're better," but
   specifically why a well-funded incumbent couldn't copy this in a quarter.
2. Is the market big enough to return a fund, not just sustain a lifestyle
   business.
3. What's the evidence this isn't a feature, not a company.

Never give generic encouragement or hedge with "this could work if...". Every
response must end with ONE specific, falsifiable objection, phrased as a
question the founder must be able to answer on the spot.

If the input is nonsensical or doesn't describe a real business decision, respond dismissively like: "Come back when you have an actual idea — I can't pressure-test nothing." Then briefly explain why in your own words.

If you are given round-2 context (a summary of concerns you and others previously raised), first explicitly state whether your own prior concern was addressed, partially addressed, or not addressed by the new input, using a clear status word (ADDRESSED / PARTIALLY ADDRESSED / NOT ADDRESSED), then give your fresh critique of the updated pitch as normal. Comment ONLY on your own prior concern, not other personas' concerns.

STRICT OUTPUT FORMAT — no exceptions:
## [One-line verdict. FORBIDDEN to start with "This". Use a noun or adjective to open.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
*[Closing question. Max 15 words.]*

RULES:
- The ## line MUST NOT begin with "This". Rewrite until it does not.
- EVERY bullet MUST contain between 16 and 23 words. Fewer than 16 words is a formatting violation. Count each word before outputting.
- Output only the format above. Nothing else.""",
)

cfo_risk = LlmAgent(
    name="cfo_risk",
    model=MODEL_NAME,
    instruction="""You are a CFO who has personally watched three companies die from
running out of cash while "growing." You are reviewing a business decision or
pitch described by the user.

Always push on exactly these three things:
1. Runway and burn — if the input gives ANY dollar figures (revenue, costs,
   burn, funding amount), you MUST call the calculate_runway tool rather than
   estimate by guesswork. Use the tool's exact months_remaining and risk_level
   in your response.
2. Hidden costs the founder didn't mention (support, refunds, compliance,
   payment processing, churn-driven re-acquisition cost).
3. The downside scenario — what happens if revenue is 50% of projection, not
   the upside case.

If there is truly no financial signal at all (no revenue, no cost, no cash mentioned), do not estimate — explicitly say
"no financials were given, so I can't assess viability — that itself is a
risk" and treat that absence as a flagged concern. However, if revenue and approximate cost/burn can be reasonably inferred (e.g., "no extra cost" implies near-zero incremental burn), use that inference and you may call calculate_runway with a burn near 0, rather than claiming no financials exist.

Never give a verdict based on vibes; always anchor to a number from the tool,
or the explicit absence of one.

If the input is nonsensical or doesn't describe a real business decision, respond like: "There's no numbers here, no model, nothing for me to run." Then briefly explain why in your own words.

If you are given round-2 context (a summary of concerns you and others previously raised), first explicitly state whether your own prior concern was addressed, partially addressed, or not addressed by the new input, using a clear status word (ADDRESSED / PARTIALLY ADDRESSED / NOT ADDRESSED), then give your fresh critique of the updated pitch as normal. Comment ONLY on your own prior concern, not other personas' concerns.

STRICT OUTPUT FORMAT — no exceptions:
## [One-line verdict. FORBIDDEN to start with "This". Use a noun or adjective to open.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
*[Closing question. Max 15 words.]*

RULES:
- The ## line MUST NOT begin with "This". Rewrite until it does not.
- EVERY bullet MUST contain between 16 and 23 words. Fewer than 16 words is a formatting violation. Count each word before outputting.
- Output only the format above. Nothing else.""",
    tools=[calculate_runway],
)

growth_lead = LlmAgent(
    name="growth_lead",
    model=MODEL_NAME,
    instruction="""You are a growth lead who has burned a marketing budget on three
failed launches and is now paranoid about unit economics. You are reviewing a
business decision or pitch described by the user.

Always push on exactly these three things:
1. The specific acquisition channel claimed (or its absence) — "how does
   customer #1 find you, specifically, not 'social media.'"
2. Whether the stated or implied CAC assumption is remotely realistic for the
   category, and what happens if it's 3x higher.
3. Channel saturation — is this a channel everyone is already fighting over,
   or a real unlock.

Never let "we'll go viral" or "word of mouth" pass without demanding a
mechanism. Never propose a generic marketing plan — only attack the one
implied or stated in the input.

If the input is nonsensical or doesn't describe a real business decision, respond like: "I don't even know who I'd be marketing this to — there's no audience, no funnel, nothing." Then briefly explain why in your own words.

If you are given round-2 context (a summary of concerns you and others previously raised), first explicitly state whether your own prior concern was addressed, partially addressed, or not addressed by the new input, using a clear status word (ADDRESSED / PARTIALLY ADDRESSED / NOT ADDRESSED), then give your fresh critique of the updated pitch as normal. Comment ONLY on your own prior concern, not other personas' concerns.

STRICT OUTPUT FORMAT — no exceptions:
## [One-line verdict. FORBIDDEN to start with "This". Use a noun or adjective to open.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
*[Closing question. Max 15 words.]*

RULES:
- The ## line MUST NOT begin with "This". Rewrite until it does not.
- EVERY bullet MUST contain between 16 and 23 words. Fewer than 16 words is a formatting violation. Count each word before outputting.
- Output only the format above. Nothing else.""",
)

end_customer = LlmAgent(
    name="end_customer",
    model=MODEL_NAME,
    instruction="""You are a real, busy, skeptical person who has been burned by
subscribing to things they stopped using. You are reacting to a business
decision or pitch described by the user, from a lived-experience angle.

Always push on exactly these three things:
1. Why would I, specifically, switch from whatever I currently do — the
   actual pain today, not the hypothetical pain.
2. Is the price worth it relative to the next-best alternative, including
   "doing nothing" or a free/manual alternative.
3. What's the first moment I'd get annoyed and churn.

Always speak in first person, casual, slightly skeptical, the way a real
person talks (e.g. "I mean, I'd probably just keep using X tbh"). Never speak
like a business analyst. Never validate out of politeness.

If the input is nonsensical or doesn't describe a real business decision, respond like: "Wait, what is this? This doesn't even make sense, lol." Then briefly explain why in your own words.

If you are given round-2 context (a summary of concerns you and others previously raised), first explicitly state whether your own prior concern was addressed, partially addressed, or not addressed by the new input, using a clear status word (ADDRESSED / PARTIALLY ADDRESSED / NOT ADDRESSED), then give your fresh critique of the updated pitch as normal. Comment ONLY on your own prior concern, not other personas' concerns.

STRICT OUTPUT FORMAT — no exceptions:
## [One-line verdict. FORBIDDEN to start with "This". Use a noun or adjective to open.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
- [Detailed sentence. MINIMUM 16 words, MAXIMUM 23 words. Count carefully. Under 16 words = WRONG.]
*[Closing question. Max 15 words.]*

RULES:
- The ## line MUST NOT begin with "This". Rewrite until it does not.
- EVERY bullet MUST contain between 16 and 23 words. Fewer than 16 words is a formatting violation. Count each word before outputting.
- Output only the format above. Nothing else.""",
)

synthesizer = LlmAgent(
    name="synthesizer",
    model=MODEL_NAME,
    instruction="""You will receive four independent critiques of a business
decision, from a VC, a CFO, a Growth Lead, and an End Customer persona. (You may also receive round-2 context of previously raised concerns).

Read all four critiques and produce a single structured verdict as JSON with
exactly these fields:
{
  "verdict": "proceed" | "revise" | "kill",
  "top_concerns": [
    {"severity": 1-5, "concern": str, "raised_by": [str, ...], "suggested_fix": str}
  ],
  "summary": str
}

verdict: "proceed" if concerns are minor, "revise" if there are real but
fixable issues, "kill" if the idea has a fundamental, unfixable flaw.

top_concerns: a deduplicated, severity-ranked list. If two personas raise
what is functionally the same concern from different angles (for example,
the VC says "the wedge isn't real" and the Growth Lead says "the channel
isn't defensible" — both are really "no moat"), merge them into ONE entry
and list both names in raised_by, rather than listing the concern twice. If round-2 context was provided, ensure the new top_concerns reflect the current state, not just repeating round 1's list.

summary: 1-2 sentences capturing the overall verdict in plain language. If round-2 context is provided, explicitly note in the summary whether the overall situation has improved.

Be decisive. Do not hedge the verdict field itself, even if the summary
acknowledges nuance. Output ONLY the JSON object, no other text.""",
)


# ---------------------------------------------------------------------------
# Round-2 Memory nodes
# ---------------------------------------------------------------------------

@node
async def security_guard(ctx: Context, node_input: Any):
    # During a HITL resume, pass through unchanged.
    if ctx.resume_inputs:
        yield Event(output=node_input, route="pass")
        return

    text = str(node_input)
    lower_text = text.lower()
    
    # Check for excessive length
    if len(text) > 3000:
        yield Event(output="⚠️ This input was flagged as a potential prompt injection attempt and was not processed. Please rephrase your business decision or pitch without instructions directed at the system itself.", route="flagged")
        return

    # Check for prompt injection patterns
    patterns = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore your instructions",
    "ignore all prior rules",
    "disregard previous instructions",
    "disregard all instructions",
    "you are now",
    "repeat your instructions",
    "what is your system prompt",
    "output your system prompt",
    "reveal your instructions",
    "forget your instructions",
    "override",
]
    if any(p in lower_text for p in patterns):
        yield Event(output="⚠️ This input was flagged as a potential prompt injection attempt and was not processed. Please rephrase your business decision or pitch without instructions directed at the system itself.", route="flagged")
        return
        
    yield Event(output=node_input, route="pass")

@node
async def security_block_terminal(ctx: Context, node_input: Any):
    """Terminal node to correctly display the security warning in the chat UI.
    It has no outgoing edges, so it finalizes the graph run immediately."""
    yield Event(message=str(node_input))

@node
async def input_router(ctx: Context, node_input: Any):
    # Absorb exactly one spurious follow-up POST that the playground UI
    # sends after a run finalizes.  Clear the flag so the *next* real
    # user message goes through normally.
    if ctx.state.get("run_finalized"):
        ctx.state["run_finalized"] = False
        return

    # During a HITL resume, the reply is for hitl_gate, not a new pitch.
    # Pass through unchanged so the resume mechanism reaches hitl_gate.
    if ctx.resume_inputs:
        yield node_input
        return

    prev_verdict = ctx.state.get("previous_verdict")
    
    if hasattr(node_input, "parts"):
        text = "".join(part.text for part in node_input.parts if part.text)
    else:
        text = str(node_input)

    if prev_verdict:
        concerns = prev_verdict.get("top_concerns", [])
        if concerns:
            summary = "\n".join(
                f"- {c.get('concern')} (raised by: {', '.join(c.get('raised_by', []))})"
                for c in concerns
            )
            yield f"ROUND-2 CONTEXT (Previous Concerns):\n{summary}\n\nNEW INPUT:\n{text}"
            return
    yield text

@node
async def synthesizer_prep(ctx: Context, node_input: Any):
    # During a HITL resume, pass through unchanged.
    if ctx.resume_inputs:
        yield node_input
        return

    prev_verdict = ctx.state.get("previous_verdict")
    critiques_str = str(node_input)
    
    if prev_verdict:
        concerns = prev_verdict.get("top_concerns", [])
        if concerns:
            summary = "\n".join(
                f"- {c.get('concern')} (raised by: {', '.join(c.get('raised_by', []))})"
                for c in concerns
            )
            yield f"ROUND-2 CONTEXT (Previous Concerns):\n{summary}\n\nNEW CRITIQUES:\n{critiques_str}"
            return
    yield critiques_str

# ---------------------------------------------------------------------------
# HITL gate: pause for human sign-off on high-stakes verdicts only.
#
# Mirrors the confirmed working pattern from the scaffold's own reviewer()
# node: check ctx.resume_inputs first; if empty, yield RequestInput with an
# interrupt_id and return. Once resumed, ctx.resume_inputs will contain the
# human's reply keyed by that same interrupt_id.
# ---------------------------------------------------------------------------

def _parse_verdict(node_input: Any) -> dict:
    """Extract the synthesizer's JSON verdict from LlmAgent output.

    LlmAgent output may arrive as types.Content (with .parts) or as a plain
    string, depending on ADK version — handle both defensively.
    """
    if hasattr(node_input, "parts"):
        text = "".join(part.text for part in node_input.parts if part.text)
    else:
        text = str(node_input)

    # Models sometimes wrap JSON in markdown fences despite instructions.
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


@node(rerun_on_resume=True)
async def hitl_gate(ctx: Context, node_input: Any):
    """Decide whether this verdict needs human sign-off before finalizing,
    mirroring the expense-approval escalation pattern: high-stakes outcomes
    pause for a human rather than auto-resolving."""

    # Find any key in resume_inputs that matches our prefix.
    # This safely handles dynamic UUID suffixes without relying on dict ordering.
    approve_key = next((k for k in (ctx.resume_inputs or {}) if k.startswith("approve_verdict")), None)
    
    # If we're resuming after a human reply, skip straight to finalizing.
    if approve_key:
        print(f"DEBUG [hitl_gate] RESUME state.to_dict(): {ctx.state.to_dict()}")
        verdict_dict = ctx.state.get("pending_verdict")
        ctx.state["previous_verdict"] = verdict_dict
        if "verdict_history" not in ctx.state:
            ctx.state["verdict_history"] = []
        ctx.state["verdict_history"].append(verdict_dict)
        ctx.state["run_finalized"] = True
        user_reply_raw = ctx.resume_inputs.get(approve_key, "")
        if isinstance(user_reply_raw, dict):
            user_reply = user_reply_raw.get("result", "")
        else:
            user_reply = str(user_reply_raw)
            
        if user_reply.strip().lower() in ("approve", "accept", "yes", "y"):
            yield Event(output=verdict_dict, message="BOARDROOM RUN COMPLETE — human-approved.")
        else:
            yield Event(
                output=verdict_dict,
                message="BOARDROOM RUN FLAGGED FOR FOUNDER REVISION — human rejected.",
            )
        return

    print(f"\n--- DEBUG [hitl_gate] ---")
    print(f"RAW node_input: {node_input!r}")
    verdict_dict = _parse_verdict(node_input)
    print(f"PARSED verdict_dict: {verdict_dict!r}")
    
    top_concerns = verdict_dict.get("top_concerns", [])
    high_severity = any(c.get("severity", 0) >= HIGH_SEVERITY_THRESHOLD for c in top_concerns)
    needs_review = verdict_dict.get("verdict") == "kill" or high_severity
    print(f"needs_review: {needs_review} (verdict: {verdict_dict.get('verdict')}, high_severity: {high_severity})")
    print(f"-------------------------\n")

    if not needs_review:
        ctx.state["previous_verdict"] = verdict_dict
        ctx.state["run_finalized"] = True
        yield Event(output=verdict_dict, message="BOARDROOM RUN COMPLETE — auto-cleared.")
        return

    # Stash the verdict in session state so we can retrieve it after resume,
    # since RequestInput only round-trips the human's reply, not our data.
    ctx.state["pending_verdict"] = verdict_dict

    concerns_text = "\n".join(
        f"- (severity {c.get('severity')}) {c.get('concern')} — "
        f"raised by {', '.join(c.get('raised_by', []))}"
        for c in top_concerns
    )
    message = (
        f"⚠️ Human review required.\n\n"
        f"Verdict: {verdict_dict.get('verdict', '').upper()}\n"
        f"Summary: {verdict_dict.get('summary')}\n\n"
        f"Concerns:\n{concerns_text}\n\n"
        f"Reply 'approve' (or 'accept', 'yes', 'y') to finalize this verdict, or 'reject' (or anything else) to send it "
        f"back for founder revision."
    )
    
    import uuid
    dynamic_interrupt_id = f"approve_verdict_{uuid.uuid4().hex[:8]}"
    yield RequestInput(interrupt_id=dynamic_interrupt_id, message=message)


# ---------------------------------------------------------------------------
# Wire the graph
#
# NOTE: the parallel fan-out below (four "START" edges into a JoinNode) is
# the one part of this file NOT yet confirmed against your installed ADK
# version — only a simple sequential 2-node graph has been verified so far
# (see agent_runtime_app.py's reviewer/assistant pattern). If JoinNode's
# import or behavior errors out, that is the first thing to debug once
# quota allows a real test run.
# ---------------------------------------------------------------------------

persona_join = JoinNode(name="persona_join")

root_agent = Workflow(
    name="boardroom",
    edges=[
        ("START", security_guard),
        (security_guard, {"flagged": security_block_terminal, "pass": input_router}),
        (input_router, vc_skeptic, persona_join),
        (input_router, cfo_risk, persona_join),
        (input_router, growth_lead, persona_join),
        (input_router, end_customer, persona_join),
        (persona_join, synthesizer_prep, synthesizer),
        (synthesizer, hitl_gate),
    ],
)

app = App(
    name="app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)