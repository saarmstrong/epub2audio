"""Conversion planner for epub2audio.

Builds a :class:`~epub2audio.models.ConversionPlan` from a parsed
:class:`ebooklib.epub.EpubBook` and :class:`~epub2audio.config.Settings`.
"""

from __future__ import annotations

import ebooklib.epub

from epub2audio.config import Settings
from epub2audio.epub.chapters import finalize_chapters, score_candidates, select_chapters
from epub2audio.epub.cover import extract_cover
from epub2audio.epub.metadata import extract_metadata
from epub2audio.epub.navigation import extract_navigation
from epub2audio.models import ConversionPlan


def plan_conversion(book: ebooklib.epub.EpubBook, settings: Settings) -> ConversionPlan:
    """Build a :class:`ConversionPlan` from an opened EPUB and settings.

    Orchestrates the EPUB-parsing subsystem to extract metadata, navigation
    entries, and scored chapter candidates, then assembles them into a
    :class:`ConversionPlan` together with a snapshot of the effective
    configuration.

    Args:
        book: An :class:`ebooklib.epub.EpubBook` opened by
            :func:`~epub2audio.epub.reader.open_epub`.
        settings: Resolved application settings (from
            :func:`~epub2audio.config.load_settings`).

    Returns:
        A :class:`ConversionPlan` with chapters in spine reading order and a
        serializable snapshot of all settings that affect synthesis.
    """
    book_metadata = extract_metadata(book)
    nav_entries = extract_navigation(book)
    candidates = score_candidates(book, nav_entries)
    chapters = finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)

    # extract_cover is called here to ensure the plan captures cover
    # availability at planning time; the bytes themselves are passed through
    # to the converter at conversion time.
    _ = extract_cover(book)  # side-effect free; result used later by converter

    return ConversionPlan(
        book_metadata=book_metadata,
        chapters=chapters,
        config_snapshot=settings.model_dump(mode="json"),
    )
