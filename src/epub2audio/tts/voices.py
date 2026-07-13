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
    "af_heart": "American Heart (default)",
    "af_bella": "American Bella",
    "af_sarah": "American Sarah",
    "am_adam": "American Adam",
    "am_michael": "American Michael",
    "bf_emma": "British Emma",
    "bf_isabella": "British Isabella",
    "bm_george": "British George",
    "bm_lewis": "British Lewis",
}
"""Curated voice catalogue: voice identifier → human-readable description.

Voice identifiers are passed directly to :class:`~epub2audio.tts.kokoro.KokoroTTSEngine`
and forwarded to the Kokoro ``KPipeline``.  The catalogue is intentionally
small; add entries here when new voices are verified to work with the
installed Kokoro version.
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
