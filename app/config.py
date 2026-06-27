"""Configuration for the Boardroom agent.

Centralizing the model name here means swapping models (e.g. if a free-tier
quota wall is hit on one model) only requires changing this one line.
"""

# Confirmed to have available free-tier quota as of June 2026 testing.
# If this model also hits a quota wall, try "gemini-3.5-flash" instead —
# heavier per-call cost, but a separate quota pool from flash-lite.
MODEL_NAME = "gemini-3.1-flash-lite"

# HITL gate thresholds — kept here (not hardcoded in agent.py) so they're
# easy to tune without touching graph logic.
HIGH_SEVERITY_THRESHOLD = 4  # concerns at or above this severity trigger human review