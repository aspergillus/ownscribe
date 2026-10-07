"""Summary sections the user can pick from, grouped as in the UI (action-oriented vs information-oriented)."""

# Order here is the order sections appear in the prompt and in the UI.
SECTIONS = [
    {"key": "exec_summary", "label": "Executive Summary", "group": "action"},
    {"key": "main_discussions", "label": "Main Discussions", "group": "action"},
    {"key": "action_plan", "label": "Action Plan", "group": "action"},
    {"key": "decisions", "label": "Decisions Made", "group": "action"},
    {"key": "next_steps", "label": "Next Steps", "group": "action"},
    {"key": "main_topics", "label": "Main Topics", "group": "info"},
    {"key": "key_points", "label": "Key Points", "group": "info"},
    {"key": "questions", "label": "Questions & Discussions", "group": "info"},
    {"key": "follow_up", "label": "Follow-up Elements", "group": "info"},
]

_ACTION = [s["key"] for s in SECTIONS if s["group"] == "action"]
_INFO = [s["key"] for s in SECTIONS if s["group"] == "info"]

PROFILES = {
    "action": _ACTION,
    "information": ["exec_summary", *_INFO],
    "complete": [s["key"] for s in SECTIONS],
}
