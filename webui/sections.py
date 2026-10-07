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

# Per-section instruction; {n} is the item cap, {w} the words-per-sentence cap. Detailed mode doubles n and raises w.
_RULES = {
    "exec_summary": "2-3 sentences of plain prose: what the meeting was for and what came out of it.",
    "main_discussions": "At most {n} bullets, each `**Topic** - the outcome in one line`.",
    "action_plan": "At most {n} bullets, each `**Owner** - task (deadline if stated)`. Explicit commitments only.",
    "decisions": "At most {n} bullets. Only decisions that were explicitly made, not ideas that were floated.",
    "next_steps": "At most {n} bullets: the upcoming steps in chronological order.",
    "main_topics": "At most {n} short labels of 2-5 words each. No full sentences.",
    "key_points": "At most {n} bullets, one sentence of at most {w} words each. Only the major facts or conclusions.",
    "questions": "At most {n} bullets: questions left unanswered or points still being debated.",
    "follow_up": "At most {n} bullets: documents, data or people that need follow-up later.",
}
_CAPS = {"concise": {"n": 6, "w": 20}, "detailed": {"n": 12, "w": 30}}

_SYSTEM = (
    "You turn meeting transcripts into short, scannable notes. Be selective: report what matters, "
    "not everything that was said."
)

_PROMPT = """Write notes for the transcript below.

Output ONLY these sections, in this order, each starting with exactly the heading shown:

{sections}

Rules:
- No introduction, no closing remarks, no sections other than the ones above.
- The transcript may repeat itself. Mention each fact once, and never repeat an item across sections.
- Ignore greetings, filler and off-topic chatter. Do not invent owners, dates or facts.
- If nothing in the transcript fits a section, write exactly `None mentioned.` under its heading.
- Write in the language of the transcript.

---

Transcript:
{{transcript}}"""


def build_template(keys, detail="concise"):
    """Return {"system_prompt", "prompt"} asking for only the selected sections, in canonical order.

    The prompt keeps a literal {transcript} placeholder (ownscribe fills it with str.format).
    """
    caps = _CAPS.get(detail, _CAPS["concise"])
    chosen = [s for s in SECTIONS if s["key"] in set(keys)]
    block = "\n\n".join(f"## {s['label']}\n{_RULES[s['key']].format(**caps)}" for s in chosen)
    return {"system_prompt": _SYSTEM, "prompt": _PROMPT.format(sections=block)}
