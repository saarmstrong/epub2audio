"""Pronunciation lexicon: load and query ``pronunciations.yaml``.

This module is the **sole** place that reads the pronunciation dictionary.
The Narration Director imports it to resolve lexicon terms while building a
:class:`~epub2audio.models.NarrationPlan`; provider adapters are deliberately
kept free of any dependency on this package — they only consume the
pre-resolved :class:`~epub2audio.models.PronunciationHint` objects that the
Director has already baked into each segment.

See ``docs/decisions/005-pronunciation-subsystem.md`` for the rationale.

Supported YAML forms
--------------------
All of the following are valid:

.. code-block:: yaml

    # Form 1 — top-level mapping (bare terms to respelling strings)
    Ono-Sendai: Oh-no Sen-DYE
    Tessier-Ashpool: Tess-ee-ay Ash-pool

    # Form 2 — top-level mapping (terms to ipa+respelling dicts)
    Neuromancer:
      ipa: "/njʊəroʊˈmænsər/"
      respelling: Nyu-ro-MAN-ser

    # Form 3 — pronunciations: key wrapper (either of the above nested)
    pronunciations:
      Ono-Sendai: Oh-no Sen-DYE

    # Form 4 — bare list of terms (flag only; no replacement supplied)
    - Ono-Sendai
    - Hosaka

A term may also be ``null`` in a mapping context, which creates an entry with
both ``ipa=None`` and ``respelling=None`` (flags the term for the provider's
own G2P handling; the Kokoro adapter simply skips it).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from epub2audio.models import PronunciationHint


class PronunciationEntry:
    """One resolved entry from the pronunciation lexicon.

    Attributes:
        term: The verbatim key as it appears in ``pronunciations.yaml``
            and as it will occur in the narration text.
        ipa: IPA transcription (e.g. ``"/oʊnoʊ sɛnˈdaɪ/"``), or ``None``
            if the lexicon entry does not supply one.
        respelling: Plain phonetic respelling (e.g. ``"Oh-no Sen-DYE"``),
            or ``None`` if the lexicon entry does not supply one.
    """

    __slots__ = ("ipa", "respelling", "term")

    def __init__(
        self,
        term: str,
        *,
        ipa: str | None = None,
        respelling: str | None = None,
    ) -> None:
        self.term = term
        self.ipa = ipa
        self.respelling = respelling

    def to_hint(self) -> PronunciationHint:
        """Return a :class:`~epub2audio.models.PronunciationHint` for this entry.

        The hint carries the same ``term``, ``ipa``, and ``respelling``
        fields so the Director can embed it directly into a
        :class:`~epub2audio.models.NarrationSegment` without the adapter
        needing to re-query the lexicon.

        Returns:
            A frozen :class:`~epub2audio.models.PronunciationHint`.
        """
        return PronunciationHint(term=self.term, ipa=self.ipa, respelling=self.respelling)

    def __repr__(self) -> str:
        return (
            f"PronunciationEntry(term={self.term!r}, "
            f"ipa={self.ipa!r}, respelling={self.respelling!r})"
        )


def _build_pattern(term: str) -> re.Pattern[str]:
    """Build a whole-token regex pattern for *term*.

    Hyphens and apostrophes are treated as part of the token so that
    ``"Tessier-Ashpool"`` is not partially matched by a hypothetical rule
    that looks for ``"Ashpool"`` alone.  The boundary assertions use a
    negative look-behind / look-ahead for ``[\\w-]`` (word chars and hyphen).

    Args:
        term: The verbatim term from the lexicon.

    Returns:
        A compiled :class:`re.Pattern` that matches *term* as a whole token.
    """
    escaped = re.escape(term)
    return re.compile(r"(?<![\w\-])" + escaped + r"(?![\w\-])")


class PronunciationLexicon:
    """In-memory pronunciation dictionary.

    Entries are keyed by exact term (case-sensitive, to preserve proper
    nouns).  Lookup and scanning are deterministic: :meth:`find_terms` sorts
    candidates by descending term length so that longer, more-specific entries
    are matched before shorter ones; ties are then resolved by first appearance
    in the text.

    Args:
        entries: Mapping from term string to
            :class:`PronunciationEntry`.  Typically constructed by
            :func:`load_lexicon` rather than directly.
    """

    def __init__(self, entries: dict[str, PronunciationEntry]) -> None:
        self._entries = entries
        # Pre-compile patterns and sort by descending term length for
        # deterministic, longest-match-first scanning.
        self._sorted: list[tuple[re.Pattern[str], PronunciationEntry]] = [
            (_build_pattern(e.term), e)
            for e in sorted(entries.values(), key=lambda e: -len(e.term))
        ]

    @classmethod
    def empty(cls) -> PronunciationLexicon:
        """Return a :class:`PronunciationLexicon` with no entries.

        Useful as a safe default when no ``pronunciations.yaml`` is
        configured.  :meth:`find_terms` always returns ``[]`` on an empty
        lexicon, and all existing behaviour is preserved unchanged.

        Returns:
            A new, empty :class:`PronunciationLexicon`.
        """
        return cls({})

    def lookup(self, term: str) -> PronunciationEntry | None:
        """Return the entry for *term*, or ``None`` if not in the lexicon.

        The lookup is case-sensitive: ``"ono-sendai"`` does **not** match
        an entry keyed as ``"Ono-Sendai"``.

        Args:
            term: Exact term string to look up.

        Returns:
            The :class:`PronunciationEntry`, or ``None``.
        """
        return self._entries.get(term)

    def find_terms(self, text: str) -> list[PronunciationEntry]:
        """Return all lexicon entries whose terms appear in *text*.

        Scanning rules:

        - Longest terms are tried first so that ``"Tessier-Ashpool"`` is
          matched before a hypothetical ``"Ashpool"`` in the same text.
        - Once a character span is consumed by a match, it is not available
          for subsequent (shorter) matches — no overlapping matches.
        - Entries are returned ordered by the **position** of their first
          match in the text.  If the same term appears more than once, only
          one entry is returned.

        Args:
            text: The segment text to scan.

        Returns:
            Ordered list of :class:`PronunciationEntry` objects (possibly
            empty) in first-appearance order.
        """
        if not self._sorted:
            return []

        # Track consumed character spans so shorter terms don't match inside
        # an already-consumed longer match.
        consumed: list[tuple[int, int]] = []
        found: dict[str, tuple[int, PronunciationEntry]] = {}  # term -> (pos, entry)

        def _is_consumed(start: int, end: int) -> bool:
            return any(cs <= start < ce or cs < end <= ce for cs, ce in consumed)

        for pattern, entry in self._sorted:
            for m in pattern.finditer(text):
                start, end = m.start(), m.end()
                if _is_consumed(start, end):
                    continue
                if entry.term not in found:
                    consumed.append((start, end))
                    found[entry.term] = (start, entry)
                break  # only need first occurrence for ordering; term done

        # Return entries sorted by position of first match.
        return [entry for _, entry in sorted(found.values(), key=lambda t: t[0])]


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def _parse_entry(term: str, value: Any) -> PronunciationEntry:
    """Parse one term/value pair from the YAML into a :class:`PronunciationEntry`.

    Supported value shapes:

    - ``str`` → treated as ``respelling``
    - ``dict`` with optional ``ipa`` / ``respelling`` keys
    - ``None`` / falsy → both fields ``None`` (term flagged but no replacement)

    Args:
        term: The lexicon term (YAML key or list element).
        value: The YAML value for this term.

    Returns:
        A :class:`PronunciationEntry`.

    Raises:
        ValueError: If *value* is a non-empty, non-string, non-dict,
            non-null type (e.g. a bare number or list).
    """
    if value is None or value == "":
        return PronunciationEntry(term=term)

    if isinstance(value, str):
        return PronunciationEntry(term=term, respelling=value)

    if isinstance(value, dict):
        ipa = value.get("ipa") or None
        respelling = value.get("respelling") or None
        # Normalise to str | None (YAML might give us numbers, though unlikely)
        if ipa is not None:
            ipa = str(ipa)
        if respelling is not None:
            respelling = str(respelling)
        return PronunciationEntry(term=term, ipa=ipa, respelling=respelling)

    raise ValueError(
        f"Pronunciation entry for {term!r} has an unsupported value type "
        f"{type(value).__name__!r}. Expected a string (respelling), a dict "
        f"with 'ipa'/'respelling' keys, or null."
    )


def load_lexicon(path: Path | None) -> PronunciationLexicon:
    """Load a :class:`PronunciationLexicon` from a YAML file.

    Returns an empty lexicon when *path* is ``None`` or the file does not
    exist, so callers can always use the return value without a ``None``
    check.

    Supports all YAML forms documented in the module docstring:

    - Bare top-level mapping (term → string or dict)
    - ``pronunciations:`` wrapper around a mapping
    - Top-level list of bare term strings (Feature.md minimal form)

    Unknown keys inside per-entry dicts are silently ignored.

    Args:
        path: Path to ``pronunciations.yaml``, or ``None``.

    Returns:
        A populated :class:`PronunciationLexicon`, or an empty one if the
        file is absent or *path* is ``None``.

    Raises:
        ValueError: If the file exists but its YAML is structurally invalid
            (e.g. the top-level value is not a mapping or list), or if an
            individual entry value has an unsupported type.
    """
    if path is None:
        return PronunciationLexicon.empty()

    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return PronunciationLexicon.empty()

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Could not parse pronunciation dictionary at {path}: {exc}") from exc

    if data is None:
        # Empty YAML file.
        return PronunciationLexicon.empty()

    entries: dict[str, PronunciationEntry] = {}

    # Form 3 — pronunciations: wrapper
    if isinstance(data, dict) and set(data.keys()) == {"pronunciations"}:
        data = data["pronunciations"]
        if data is None:
            return PronunciationLexicon.empty()

    # Form 4 — bare list of term strings
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, str):
                raise ValueError(
                    f"Pronunciation list entries must be strings, got "
                    f"{type(item).__name__!r}: {item!r}"
                )
            entries[item] = PronunciationEntry(term=item)
        return PronunciationLexicon(entries)

    # Forms 1 & 2 — top-level mapping
    if isinstance(data, dict):
        for term, value in data.items():
            term_str = str(term)
            entries[term_str] = _parse_entry(term_str, value)
        return PronunciationLexicon(entries)

    raise ValueError(
        f"Pronunciation dictionary at {path} must be a YAML mapping or list, "
        f"got {type(data).__name__!r}."
    )
