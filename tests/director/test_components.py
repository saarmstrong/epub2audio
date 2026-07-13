"""Unit tests for the Narration Director's building blocks."""

from __future__ import annotations

import pytest

from epub2audio.director import dialogue, emphasis, scenes, scoring


class TestScenes:
    def test_no_break_is_single_scene(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        assert scenes.split_scenes(text) == [text]

    @pytest.mark.parametrize("divider", ["* * *", "***", "---", "\u2022", "#"])
    def test_break_lines_split(self, divider: str) -> None:
        text = f"Before the break.\n\n{divider}\n\nAfter the break."
        result = scenes.split_scenes(text)
        assert result == ["Before the break.", "After the break."]

    def test_divider_is_discarded(self) -> None:
        result = scenes.split_scenes("A.\n\n* * *\n\nB.")
        assert all("*" not in scene for scene in result)

    def test_empty_text(self) -> None:
        assert scenes.split_scenes("   \n\n  ") == []

    def test_long_dotted_line_is_not_a_break(self) -> None:
        # A real (if odd) sentence of dots should not be treated as a divider.
        text = "Real sentence here....................... still going."
        assert scenes.split_scenes(text) == [text]


class TestDialogue:
    def test_plain_narration(self) -> None:
        t, speaker = dialogue.classify("The wind blew across the empty plain.")
        assert t == "narration"
        assert speaker == "narrator"

    def test_dialogue_verb_then_name(self) -> None:
        t, speaker = dialogue.classify('"We should go," said Case, quietly.')
        assert t == "dialogue"
        assert speaker == "Case"

    def test_dialogue_name_then_verb(self) -> None:
        t, speaker = dialogue.classify('"We should go," Molly whispered.')
        assert t == "dialogue"
        assert speaker == "Molly"

    def test_dialogue_pronoun_speaker_lowercased(self) -> None:
        t, speaker = dialogue.classify('"Run," she shouted.')
        assert t == "dialogue"
        assert speaker == "she"

    def test_dialogue_unknown_speaker(self) -> None:
        t, speaker = dialogue.classify('"Is anyone there?"')
        assert t == "dialogue"
        assert speaker == "unknown"

    def test_brief_quote_in_narration_is_narration(self) -> None:
        # A short quoted word inside a long narration paragraph stays narration.
        text = (
            'The sign simply read "open", though the whole street had been '
            "abandoned for years and nothing about it felt welcoming at all."
        )
        t, _ = dialogue.classify(text)
        assert t == "narration"


class TestEmphasis:
    def test_all_caps_is_strong(self) -> None:
        hints = emphasis.extract_emphasis("You need to STOP right now.")
        assert any(h.phrase == "STOP" and h.level == "strong" for h in hints)

    def test_short_acronym_not_flagged(self) -> None:
        hints = emphasis.extract_emphasis("He works in AI and TV.")
        assert hints == []

    def test_wrapped_is_moderate(self) -> None:
        hints = emphasis.extract_emphasis("This is *very* important.")
        assert any(h.phrase == "very" and h.level == "moderate" for h in hints)

    def test_deduplicated(self) -> None:
        hints = emphasis.extract_emphasis("STOP. I said STOP.")
        assert [h.phrase for h in hints] == ["STOP"]

    def test_phrase_is_substring(self) -> None:
        text = "NEVER go back, *ever*."
        for h in emphasis.extract_emphasis(text):
            assert h.phrase in text


class TestScoring:
    def test_intensity_bounds(self) -> None:
        assert scoring.intensity("") == 0.0
        assert 0.0 <= scoring.intensity("Calm, even prose about nothing.") <= 1.0

    def test_exclamations_raise_intensity(self) -> None:
        calm = scoring.intensity("The room was quiet and still.")
        loud = scoring.intensity("Run! Now! Go! Move!")
        assert loud > calm

    def test_pace_clamped(self) -> None:
        for text in ["Short.", "Run! Now!", "A " * 200]:
            p = scoring.pace(text, scoring.intensity(text))
            assert 0.85 <= p <= 1.15

    def test_dialogue_ratio_bounds(self) -> None:
        assert scoring.dialogue_ratio("") == 0.0
        assert scoring.dialogue_ratio('"all quoted"') > 0.5
        assert scoring.dialogue_ratio("no quotes here") == 0.0

    def test_mood_labels(self) -> None:
        assert scoring.mood("x", 0.9, 0.0) == "tense and urgent"
        assert scoring.mood("x", 0.3, 0.8) == "conversational"
        assert scoring.mood("x", 0.1, 0.0) == "calm and measured"
        assert scoring.mood("x", 0.4, 0.1) == "neutral narration"
