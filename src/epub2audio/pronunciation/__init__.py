"""Pronunciation lexicon subsystem for epub2audio.

This package provides the :class:`PronunciationLexicon` (loaded from a
``pronunciations.yaml`` file) and the associated :class:`PronunciationEntry`
data type.  The Narration Director uses them to resolve pronunciation hints
before building a :class:`~epub2audio.models.NarrationPlan`; provider adapters
consume the pre-resolved :class:`~epub2audio.models.PronunciationHint` objects
and never need to import this package.

See ``docs/decisions/005-pronunciation-subsystem.md``.

Public API::

    from epub2audio.pronunciation import PronunciationEntry, PronunciationLexicon, load_lexicon

    lexicon = load_lexicon(Path("pronunciations.yaml"))
    entry   = lexicon.lookup("Ono-Sendai")
    matches = lexicon.find_terms("Case jacked into the Ono-Sendai deck.")
"""

from __future__ import annotations

from epub2audio.pronunciation.lexicon import (
    PronunciationEntry,
    PronunciationLexicon,
    load_lexicon,
)

__all__ = ["PronunciationEntry", "PronunciationLexicon", "load_lexicon"]
