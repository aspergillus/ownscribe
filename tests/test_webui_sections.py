from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webui"))

import sections


def test_profiles_match_the_agreed_sets():
    assert sections.PROFILES["action"] == [
        "exec_summary", "main_discussions", "action_plan", "decisions", "next_steps",
    ]
    assert sections.PROFILES["information"] == [
        "exec_summary", "main_topics", "key_points", "questions", "follow_up",
    ]
    assert sections.PROFILES["complete"] == [s["key"] for s in sections.SECTIONS]


def test_prompt_contains_only_selected_sections_in_canonical_order():
    prompt = sections.build_template(["key_points", "exec_summary"])["prompt"]
    assert "## Executive Summary" in prompt and "## Key Points" in prompt
    assert prompt.index("## Executive Summary") < prompt.index("## Key Points")
    assert "## Action Plan" not in prompt


def test_prompt_only_uses_braces_for_the_transcript_placeholder():
    prompt = sections.build_template(sections.PROFILES["complete"])["prompt"]
    assert prompt.count("{") == 1
    assert "{transcript}" in prompt.format(transcript="{transcript}")  # str.format must not raise


def test_detailed_raises_the_caps():
    concise = sections.build_template(["key_points"], "concise")["prompt"]
    detailed = sections.build_template(["key_points"], "detailed")["prompt"]
    assert "At most 6 bullets" in concise and "45-70 words" in concise
    assert "At most 12 bullets" in detailed and "70-110 words" in detailed


def test_key_points_are_complete_explanatory_sentences():
    concise = sections.build_template(["key_points"], "concise")["prompt"]
    detailed = sections.build_template(["key_points"], "detailed")["prompt"]
    assert "complete, self-contained sentence" in concise and "45-70" in concise
    assert "complete, self-contained sentence" in detailed and "70-110" in detailed
    assert "20 words" not in concise


def test_clean_transcript_drops_fillers_and_repeats_but_keeps_content():
    text = (
        "Okay. Yeah okay. We launch the project in November. Alice will send the budget report on Friday. "
        "Alice will send the budget report on Friday. Alice will send the budget reports on Friday. "
        "Bob books the room. Thank you."
    )
    assert sections.clean_transcript(text) == (
        "We launch the project in November. Alice will send the budget report on Friday. Bob books the room."
    )


def test_clean_transcript_collapses_immediate_repeats_but_keeps_distant_short_sentences():
    far = " ".join(f"Item {hashlib.md5(str(i).encode()).hexdigest()} was reviewed today." for i in range(25))
    text = f"We agreed. We agreed. {far} We agreed."
    out = sections.clean_transcript(text)
    assert out.startswith("We agreed. Item ")  # immediate repeat collapsed
    assert out.endswith("We agreed.")  # same short sentence much later is kept
