from __future__ import annotations

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
    assert "At most 6 bullets" in concise and "20 words" in concise
    assert "At most 12 bullets" in detailed and "30 words" in detailed
