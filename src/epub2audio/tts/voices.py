"""Voice catalogue and language map for Kokoro TTS.

This module is the single source of truth for:

- :data:`LANGUAGE_MAP` — mapping from BCP-47 language tags to Kokoro
  ``lang_code`` values.
- :data:`VOICE_CATALOGUE` — curated set of supported voice identifiers and
  human-readable descriptions.
- :func:`get_lang_code` — validated language-to-lang_code conversion.
- :func:`list_voices` — sorted voice listing for the CLI ``voices`` command.

Supported Kokoro lang_code values
----------------------------------
``a`` en-us · ``b`` en-gb · ``f`` fr-fr · ``j`` ja · ``k`` ko · ``z`` cmn/zh
"""

from __future__ import annotations

from epub2audio.errors import UnsupportedLanguageError

# ---------------------------------------------------------------------------
# Language map
# ---------------------------------------------------------------------------

LANGUAGE_MAP: dict[str, str] = {
    "en-us": "a",
    "en-gb": "b",
    "fr-fr": "f",
    "ja": "j",
    "ko": "k",
    "cmn": "z",
    "zh": "z",
}
"""Mapping from lower-cased BCP-47 language tag to Kokoro ``lang_code``.

Only languages in this table are supported.  Attempting to synthesize with
any other language tag raises :exc:`~epub2audio.errors.UnsupportedLanguageError`.
"""

# ---------------------------------------------------------------------------
# Voice catalogue
# ---------------------------------------------------------------------------

VOICE_CATALOGUE: dict[str, str] = {
    # -- American English — female (af_) -----------------------------------
    "af_heart": "American female · warm, natural · grade A · default",
    "af_bella": "American female · expressive · grade A-",
    "af_nicole": "American female · soft, intimate (ASMR-ish) · grade B-",
    "af_aoede": "American female · grade C+",
    "af_kore": "American female · grade C+",
    "af_sarah": "American female · grade C+",
    "af_nova": "American female · grade C",
    "af_alloy": "American female · grade C",
    "af_jessica": "American female · grade C",
    "af_river": "American female · grade C",
    "af_sky": "American female · grade C-",
    # -- American English — male (am_) -------------------------------------
    "am_michael": "American male · warm, steady narrator · grade C+",
    "am_fenrir": "American male · gritty, intense — good for noir/cyberpunk · grade C+",
    "am_puck": "American male · lively, characterful · grade C+",
    "am_onyx": "American male · deep, resonant — cyberpunk narrator, less stable · grade D",
    "am_echo": "American male · grade D",
    "am_eric": "American male · grade D",
    "am_liam": "American male · grade D",
    "am_adam": "American male · harder-edged, least stable · grade F+",
    "am_santa": "American male · character voice · grade D-",
    # -- British English — female (bf_) ------------------------------------
    "bf_emma": "British female · clear, measured · grade B-",
    "bf_isabella": "British female · grade C",
    "bf_alice": "British female · grade D",
    "bf_lily": "British female · grade D",
    # -- British English — male (bm_) --------------------------------------
    "bm_george": "British male · cool, detached — Blade Runner-ish noir · grade C",
    "bm_fable": "British male · storyteller tone · grade C",
    "bm_lewis": "British male · grade D+",
    "bm_daniel": "British male · understated, literary · grade D",
    # -- Other languages (match language= to the voice's language) ---------
    "ff_siwis": "French female (fr-fr) · grade B-",
    "jf_alpha": "Japanese female (ja) · grade C+",
    "jm_kumo": "Japanese male (ja) · grade C-",
    "zf_xiaoxiao": "Mandarin female (zh) · grade C",
    "zm_yunxi": "Mandarin male (zh) · grade C",
}
"""Curated voice catalogue: voice identifier → human-readable description.

Voice identifiers are passed directly to
:class:`~epub2audio.tts.kokoro.KokoroTTSEngine` and forwarded to the Kokoro
``KPipeline``.  ``--voice`` is *not* restricted to this catalogue — any voice
the installed Kokoro version ships can be passed — so this table is a curated
guide, not a whitelist.

The ``grade`` in each description is Kokoro's own published voice-quality /
stability grade (A = best, F = worst).  Higher grades are more consistent;
lower-graded voices may occasionally mispronounce or waver but can still have
the most fitting *character* for a given book.  Grades are informational and
reflect the standard Kokoro v1.0 voice pack; the exact set available depends on
your installed Kokoro version.

For a William Gibson / cyberpunk-noir feel, see ``am_onyx`` (deep American
narrator), ``am_fenrir`` (gritty), or ``bm_george`` (cool British noir).
"""

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_lang_code(language: str) -> str:
    """Return the Kokoro ``lang_code`` for a BCP-47 language tag.

    Lookup is case-insensitive.

    Args:
        language: BCP-47 language tag such as ``"en-us"`` or ``"ja"``.

    Returns:
        Single-character Kokoro ``lang_code`` (e.g. ``"a"`` for ``"en-us"``).

    Raises:
        UnsupportedLanguageError: If *language* has no entry in
            :data:`LANGUAGE_MAP`.
    """
    key = language.lower()
    if key not in LANGUAGE_MAP:
        raise UnsupportedLanguageError(language)
    return LANGUAGE_MAP[key]


def list_voices() -> list[tuple[str, str]]:
    """Return a sorted list of ``(voice_id, description)`` pairs.

    Sorted alphabetically by voice identifier so that CLI output is
    deterministic across Python versions and platforms.

    Returns:
        Sorted list of ``(voice_id, description)`` tuples from
        :data:`VOICE_CATALOGUE`.
    """
    return sorted(VOICE_CATALOGUE.items())
