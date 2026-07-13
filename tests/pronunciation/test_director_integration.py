"""Integration tests: pronunciation lexicon wired into the Narration Director.

Covers:
- build_narration_plan propagates lexicon hints into segment.pronunciation_hints
- Hints carry correct ipa + respelling from the lexicon
- lexicon=None (default) keeps pronunciation_hints empty — backward compat
- Kokoro adapter substitutes respellings in rendered text
- M9-09 (carried): end-to-end completeness — all non-divider narration text
  lands in some segment (not just substring containment)
"""

from __future__ import annotations

import re

from epub2audio.config import Settings
from epub2audio.director import build_narration_plan
from epub2audio.models import NarrationDirection, NarrationSegment
from epub2audio.pronunciation import PronunciationEntry, PronunciationLexicon
from epub2audio.providers.kokoro import KokoroProvider
from epub2audio.text.normalize import normalize_text
from epub2audio.tts.fake import FakeTTSEngine

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SAMPLE_TEXT = (
    "Case jacked into the Ono-Sendai deck. "
    "The Hosaka hummed beside him. "
    "Tessier-Ashpool loomed in the dark."
)

_LEXICON = PronunciationLexicon(
    {
        "Ono-Sendai": PronunciationEntry(
            term="Ono-Sendai",
            ipa="/oʊnoʊ sɛnˈdaɪ/",
            respelling="Oh-no Sen-DYE",
        ),
        "Hosaka": PronunciationEntry(term="Hosaka", respelling="Ho-SAH-kah"),
        "Tessier-Ashpool": PronunciationEntry(
            term="Tessier-Ashpool", respelling="Tess-ee-ay Ash-pool"
        ),
        "Neuromancer": PronunciationEntry(
            term="Neuromancer",
            ipa="/njʊəroʊˈmænsər/",
            respelling="Nyu-ro-MAN-ser",
        ),
    }
)


def _all_segs(plans: list) -> list[NarrationSegment]:
    return [seg for plan in plans for seg in plan.segments]


# ---------------------------------------------------------------------------
# Lexicon wired into Director
# ---------------------------------------------------------------------------


def test_no_lexicon_hints_empty() -> None:
    plans = build_narration_plan(_SAMPLE_TEXT, 1)
    for seg in _all_segs(plans):
        assert seg.pronunciation_hints == []


def test_lexicon_hints_populated() -> None:
    plans = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    all_hints = [h for seg in _all_segs(plans) for h in seg.pronunciation_hints]
    terms = {h.term for h in all_hints}
    assert "Ono-Sendai" in terms
    assert "Hosaka" in terms
    assert "Tessier-Ashpool" in terms


def test_hints_carry_ipa_and_respelling() -> None:
    plans = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    for seg in _all_segs(plans):
        for h in seg.pronunciation_hints:
            if h.term == "Ono-Sendai":
                assert h.ipa == "/oʊnoʊ sɛnˈdaɪ/"
                assert h.respelling == "Oh-no Sen-DYE"
            if h.term == "Hosaka":
                assert h.respelling == "Ho-SAH-kah"
                assert h.ipa is None


def test_term_not_in_text_not_in_hints() -> None:
    plans = build_narration_plan("No proper nouns here.", 1, lexicon=_LEXICON)
    all_hints = [h for seg in _all_segs(plans) for h in seg.pronunciation_hints]
    assert all_hints == []


def test_deterministic_with_lexicon() -> None:
    a = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    b = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    assert [p.model_dump() for p in a] == [p.model_dump() for p in b]


def test_hint_term_is_substring_of_segment_text() -> None:
    plans = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    for seg in _all_segs(plans):
        for h in seg.pronunciation_hints:
            assert h.term in seg.text, f"{h.term!r} not a substring of {seg.text!r}"


# ---------------------------------------------------------------------------
# M9-09 (carried): end-to-end completeness assertion
# ---------------------------------------------------------------------------


def test_all_narration_text_lands_in_some_segment() -> None:
    """Every non-divider word from the normalized source must appear in a segment.

    This is a stronger guarantee than the M8 substring check: here we verify
    that the *union* of segment texts covers every word from the normalized
    chapter text (ignoring scene-break dividers), not just that individual
    segments are substrings.
    """
    chapter = """The rain fell on the neon street.

* * *

Later the room was quiet.

Case walked slowly."""

    plans = build_narration_plan(chapter, 1)

    # Collect all segment words
    seg_words: set[str] = set()
    for seg in _all_segs(plans):
        seg_words.update(re.findall(r"[A-Za-z']+", seg.text))

    # Every word from the normalized source (excluding divider lines) must appear
    normalized = normalize_text(chapter)
    divider_re = re.compile(r"^[\s*#•·.\-—_=~]+$")
    for para in re.split(r"\n\s*\n+", normalized):
        para = para.strip()
        if not para or divider_re.match(para):
            continue
        for word in re.findall(r"[A-Za-z']+", para):
            assert word in seg_words, (
                f"Word {word!r} from source not found in any segment. "
                f"Segment words: {sorted(seg_words)}"
            )


# ---------------------------------------------------------------------------
# Kokoro adapter applies respellings from hints
# ---------------------------------------------------------------------------


def test_kokoro_renders_respelling_not_original_term() -> None:
    plans = build_narration_plan(_SAMPLE_TEXT, 1, lexicon=_LEXICON)
    provider = KokoroProvider(FakeTTSEngine())
    defaults = NarrationDirection(mood="neutral narration", pace=1.0, intensity=0.0)
    settings = Settings(voice="af_heart", language="en-us", speed=1.0)

    rendered_texts = []
    for seg in _all_segs(plans):
        req = provider.render(seg, defaults, settings)
        rendered_texts.append(req.text)

    combined = " ".join(rendered_texts)
    assert "Oh-no Sen-DYE" in combined, "Ono-Sendai respelling not applied"
    assert "Ho-SAH-kah" in combined, "Hosaka respelling not applied"
    assert "Tess-ee-ay Ash-pool" in combined, "Tessier-Ashpool respelling not applied"


def test_kokoro_ipa_only_hint_is_noop() -> None:
    """A hint with ipa but no respelling must not alter the rendered text."""
    lex = PronunciationLexicon(
        {"Neuromancer": PronunciationEntry(term="Neuromancer", ipa="/njʊəroʊˈmænsər/")}
    )
    plans = build_narration_plan("He read Neuromancer.", 1, lexicon=lex)
    provider = KokoroProvider(FakeTTSEngine())
    defaults = NarrationDirection(mood="neutral narration", pace=1.0, intensity=0.0)
    settings = Settings(voice="af_heart", language="en-us", speed=1.0)

    req = provider.render(_all_segs(plans)[0], defaults, settings)
    assert "Neuromancer" in req.text  # original term preserved (no respelling to sub)


def test_kokoro_empty_hints_byte_identical() -> None:
    """Provider output is byte-identical to M9 when hints list is empty."""
    provider = KokoroProvider(FakeTTSEngine())
    defaults = NarrationDirection(mood="neutral narration", pace=1.0, intensity=0.0)
    seg = NarrationSegment(
        id="x",
        type="narration",
        speaker="narrator",
        text="The rain fell.",
        direction=None,
        pause_after_ms=300,
        pace=1.0,
        emphasis=[],
        pronunciation_hints=[],
    )
    req = provider.render(seg, defaults, Settings())
    assert req.text == "The rain fell."
