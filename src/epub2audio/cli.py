"""Command-line interface for epub2audio.

Entry point declared in ``pyproject.toml`` as ``epub2audio.cli:app``.

Commands implemented in Milestone 1:

- ``inspect``  — show the conversion plan for an EPUB without generating audio.

Commands implemented in Milestone 2:

- ``convert``  — full EPUB → MP3 conversion.

Commands planned for later milestones (stubs):

- ``voices``   — list available Kokoro voices (Milestone 3)
- ``doctor``   — environment dependency check (Milestone 3)
- ``config``   — manage configuration file (Milestone 3)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from epub2audio.config import load_settings
from epub2audio.epub.chapters import finalize_chapters, score_candidates, select_chapters
from epub2audio.epub.metadata import extract_metadata
from epub2audio.epub.navigation import extract_navigation
from epub2audio.epub.reader import open_epub
from epub2audio.errors import DrmProtectedEpubError, InvalidEpubError, MissingDependencyError

app = typer.Typer(
    name="epub2audio",
    help="Convert EPUB ebooks to audiobooks using local Kokoro TTS.",
    add_completion=False,
)

_console = Console()
_err_console = Console(stderr=True)


@app.command()
def inspect(
    epub_path: Path = typer.Argument(..., help="Path to the EPUB file to inspect."),
    json_output: bool = typer.Option(
        False, "--json", help="Output machine-readable JSON instead of a Rich table."
    ),
    config: Path | None = typer.Option(None, "--config", help="Path to a TOML configuration file."),
) -> None:
    """Inspect an EPUB file and show the conversion plan as a table.

    Displays every spine document with its chapter score, status, word count,
    and the scoring signals that determined inclusion or exclusion.  Use
    ``--json`` for machine-readable output suitable for scripting.
    """
    try:
        book = open_epub(epub_path)
    except FileNotFoundError:
        _err_console.print(f"[red]Error:[/red] File not found: {epub_path}")
        raise typer.Exit(code=1) from None
    except DrmProtectedEpubError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None
    except InvalidEpubError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None

    metadata = extract_metadata(book)
    nav_entries = extract_navigation(book)
    candidates = score_candidates(book, nav_entries)
    chapters = finalize_chapters(select_chapters(candidates), candidates, nav_entries, book)

    # Build sets for status lookup
    included_paths = {doc for ch in chapters for doc in ch.source_docs}

    if json_output:
        # Warned candidates: included but low score (0–1)
        warned = [{"title": c.title, "signals": c.signals} for c in candidates if 0 <= c.score <= 1]
        payload = {
            "metadata": metadata.model_dump(),
            "chapters": [ch.model_dump() for ch in chapters],
            "warnings": warned,
        }
        sys.stdout.write(json.dumps(payload, indent=2))
        sys.stdout.write("\n")
        return

    # ------------------------------------------------------------------ #
    # Rich table output                                                    #
    # ------------------------------------------------------------------ #

    # Print book header
    _console.print(f"\n[bold cyan]{metadata.title}[/bold cyan]  [dim]by {metadata.author}[/dim]\n")

    table = Table(
        show_header=True,
        header_style="bold",
        title="Conversion Plan",
        expand=False,
    )
    table.add_column("#", style="dim", justify="right", no_wrap=True)
    table.add_column("Title", min_width=20)
    table.add_column("Source Doc(s)", style="dim", overflow="fold")
    table.add_column("Words", justify="right")
    table.add_column("Status", no_wrap=True)
    table.add_column("Signals", overflow="fold", min_width=20)

    chapter_num = 0
    for candidate in candidates:
        is_included = candidate.doc_path in included_paths
        is_warned = is_included and 0 <= candidate.score <= 1

        if candidate.score < 0:
            status_str = "❌ Excluded"
            status_style = "red"
            display_num = "-"
        elif is_warned:
            chapter_num += 1
            status_str = "⚠️  Warned"
            status_style = "yellow"
            display_num = str(chapter_num)
        else:
            chapter_num += 1
            status_str = "✅ Included"
            status_style = "green"
            display_num = str(chapter_num)

        title_display = candidate.title or "(no title)"
        signals_display = "; ".join(candidate.signals)

        # Word count: look up from the chapter list
        wc_display = ""
        if is_included:
            for ch in chapters:
                if candidate.doc_path in ch.source_docs:
                    wc_display = str(ch.word_count) if ch.word_count else ""
                    break

        table.add_row(
            display_num,
            title_display,
            candidate.doc_path,
            wc_display,
            f"[{status_style}]{status_str}[/{status_style}]",
            signals_display,
        )

    _console.print(table)
    _console.print(f"\n[green]Found {len(chapters)} chapter(s) to convert.[/green]\n")


# ---------------------------------------------------------------------------
# convert command
# ---------------------------------------------------------------------------


@app.command()
def convert(
    epub_path: Path = typer.Argument(..., help="Path to the EPUB file to convert."),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Output directory for MP3 files."
    ),
    voice: str = typer.Option("af_heart", "--voice", help="Kokoro voice identifier."),
    language: str = typer.Option("en-us", "--language", help="BCP-47 language tag."),
    speed: float = typer.Option(1.0, "--speed", help="TTS speed multiplier (0.25–4.0)."),
    bitrate: str = typer.Option("96k", "--bitrate", help="MP3 bitrate, e.g. '96k'."),
    sample_rate: int = typer.Option(24000, "--sample-rate", help="Output sample rate in Hz."),
    normalize: bool = typer.Option(
        True, "--normalize/--no-normalize", help="Apply EBU R128 loudness normalization."
    ),
    resume: bool = typer.Option(
        True, "--resume/--no-resume", help="Resume an interrupted conversion."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing MP3 files."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Plan conversion without producing audio."
    ),
    workers: int = typer.Option(1, "--workers", help="Number of parallel TTS workers (1–16)."),
    chapter_start: int | None = typer.Option(
        None, "--chapter-start", help="First chapter number to convert (1-based)."
    ),
    chapter_end: int | None = typer.Option(
        None, "--chapter-end", help="Last chapter number to convert (1-based, inclusive)."
    ),
    config: Path | None = typer.Option(None, "--config", help="Path to TOML configuration file."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output."),
) -> None:
    """Convert an EPUB ebook to MP3 audiobook chapters.

    Produces one MP3 file per logical chapter in reading order.  Chapter
    files are named ``NNN - Chapter Title.mp3`` and written to *output*.

    TTS engine selection: uses Kokoro if available, otherwise falls back to
    the built-in ``FakeTTSEngine`` (silent audio, useful for testing the
    pipeline without a model).
    """
    import logging as _logging

    if verbose:
        _logging.basicConfig(level=_logging.DEBUG)
    elif not quiet:
        _logging.basicConfig(level=_logging.INFO)
    else:
        _logging.basicConfig(level=_logging.WARNING)

    # ------------------------------------------------------------------ #
    # Open EPUB                                                            #
    # ------------------------------------------------------------------ #
    try:
        from epub2audio.epub.reader import open_epub as _open_epub

        book = _open_epub(epub_path)
    except FileNotFoundError:
        _err_console.print(f"[red]Error:[/red] File not found: {epub_path}")
        raise typer.Exit(code=1) from None
    except DrmProtectedEpubError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None
    except InvalidEpubError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from None

    # ------------------------------------------------------------------ #
    # Build settings                                                       #
    # ------------------------------------------------------------------ #
    base_settings = load_settings(config)
    settings = base_settings.model_copy(
        update={
            "voice": voice,
            "language": language,
            "speed": speed,
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "normalize": normalize,
            "resume": resume,
            "workers": workers,
            "output_dir": output,
        }
    )

    # ------------------------------------------------------------------ #
    # Build conversion plan                                                #
    # ------------------------------------------------------------------ #
    from epub2audio.pipeline.planner import plan_conversion

    plan = plan_conversion(book, settings)

    chapters = plan.chapters
    # Apply chapter range filtering
    if chapter_start is not None:
        chapters = chapters[chapter_start - 1 :]
    if chapter_end is not None:
        limit = chapter_end - (chapter_start - 1 if chapter_start else 0)
        chapters = chapters[:limit]

    if not quiet:
        _console.print(
            f"\n[bold cyan]{plan.book_metadata.title}[/bold cyan]  "
            f"[dim]by {plan.book_metadata.author}[/dim]"
        )
        _console.print(f"  Chapters to convert: [bold]{len(chapters)}[/bold]")
        _console.print(f"  Output directory:    [bold]{output}[/bold]")
        _console.print(f"  Voice / language:    {voice} / {language}")
        _console.print(f"  Normalize:           {normalize}")
        _console.print()

    if dry_run:
        _console.print("[yellow]Dry run — no audio will be produced.[/yellow]")
        return

    # ------------------------------------------------------------------ #
    # TTS engine selection                                                 #
    # ------------------------------------------------------------------ #
    from epub2audio.tts.base import TTSEngine

    tts_engine: TTSEngine
    try:
        from epub2audio.tts.kokoro import KokoroTTSEngine
        from epub2audio.tts.voices import get_lang_code

        # Get the lang_code for the configured language
        lang_code = get_lang_code(settings.language)
        tts_engine = KokoroTTSEngine(lang_code=lang_code)
        if not quiet:
            _console.print("[green]Using Kokoro TTS engine.[/green]")
    except Exception as exc:
        from epub2audio.tts.fake import FakeTTSEngine

        tts_engine = FakeTTSEngine()
        if not quiet:
            _console.print(
                f"[yellow]Kokoro not available ({type(exc).__name__}: {exc}) — "
                "using FakeTTSEngine (silent audio for pipeline testing).[/yellow]"
            )

    # ------------------------------------------------------------------ #
    # Run conversion                                                       #
    # ------------------------------------------------------------------ #
    from epub2audio.models import ConversionPlan
    from epub2audio.pipeline.converter import convert_epub

    filtered_plan = ConversionPlan(
        book_metadata=plan.book_metadata,
        chapters=chapters,
        config_snapshot=plan.config_snapshot,
    )

    try:
        report = convert_epub(
            epub_path=epub_path,
            output_dir=output,
            settings=settings,
            tts_engine=tts_engine,
            plan=filtered_plan,
        )
    except MissingDependencyError as exc:
        _err_console.print(f"[red]Error:[/red] {exc}")
        _err_console.print("[dim]Install FFmpeg: https://ffmpeg.org/download.html[/dim]")
        raise typer.Exit(code=1) from None
    except Exception as exc:
        _err_console.print(f"[red]Conversion failed:[/red] {exc}")
        raise typer.Exit(code=1) from None

    # ------------------------------------------------------------------ #
    # Summary                                                              #
    # ------------------------------------------------------------------ #
    if not quiet:
        successful = sum(1 for r in report.chapter_results if r.output_path is not None)
        failed = len(report.chapter_results) - successful
        _console.print(
            f"\n[green]Done.[/green] {successful} chapter(s) converted"
            + (f", [red]{failed} failed[/red]" if failed else "")
            + "."
        )
        if report.errors:
            for err in report.errors:
                _err_console.print(f"[red]Error:[/red] {err}")


@app.command()
def voices() -> None:
    """List available Kokoro TTS voices.

    Displays all voices in the epub2audio voice catalogue with their
    human-readable descriptions.  Pass the *Voice ID* as ``--voice`` to
    the ``convert`` command.
    """
    from epub2audio.tts.voices import VOICE_CATALOGUE, list_voices

    table = Table(title="Kokoro TTS Voices")
    table.add_column("Voice ID", style="cyan", no_wrap=True)
    table.add_column("Description")
    for voice_id, description in list_voices():
        table.add_row(voice_id, description)
    _console.print(table)
    _console.print(f"{len(VOICE_CATALOGUE)} voices available.")


@app.command()
def doctor() -> None:
    """Check the epub2audio environment and dependencies.

    Prints the status of each required and optional dependency.  Exits with
    code **0** when all *required* dependencies (FFmpeg and FFprobe) are
    present; exits with code **1** if either is missing.  Optional
    dependencies (espeak-ng, kokoro, misaki) show a warning but do not
    affect the exit code.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    espeak_path = shutil.which("espeak-ng")

    # ------------------------------------------------------------------ #
    # Collect check results                                                #
    # ------------------------------------------------------------------ #

    lines: list[tuple[str, str]] = []

    # 1. Python
    py_version = sys.version.split()[0]
    lines.append(("✅", f"Python {py_version}"))

    # 2. FFmpeg (required)
    if ffmpeg_path:
        lines.append(("✅", f"FFmpeg      {ffmpeg_path}"))
    else:
        lines.append(("❌", "FFmpeg      not found  (install: https://ffmpeg.org/download.html)"))

    # 3. FFprobe (required)
    if ffprobe_path:
        lines.append(("✅", f"FFprobe     {ffprobe_path}"))
    else:
        lines.append(("❌", "FFprobe     not found  (install: https://ffmpeg.org/download.html)"))

    # 4. espeak-ng (optional)
    if espeak_path:
        lines.append(("✅", f"espeak-ng   {espeak_path}"))
    else:
        lines.append(
            ("⚠️ ", "espeak-ng   not found  (optional — required by Kokoro for some languages)")
        )

    # 5. kokoro package (optional)
    try:
        import kokoro as _kokoro

        kokoro_ver = getattr(_kokoro, "__version__", "unknown")
        lines.append(("✅", f"kokoro      {kokoro_ver}"))
    except ImportError:
        lines.append(
            (
                "⚠️ ",
                "kokoro      not installed  (optional — install with: uv pip install 'epub2audio[tts]')",
            )
        )

    # 6. misaki package (optional)
    try:
        import misaki as _misaki

        misaki_ver = getattr(_misaki, "__version__", "unknown")
        lines.append(("✅", f"misaki      {misaki_ver}"))
    except ImportError:
        lines.append(
            (
                "⚠️ ",
                "misaki      not installed  (optional — install with: uv pip install 'epub2audio[tts]')",
            )
        )

    # 7. Disk space
    usage = shutil.disk_usage(".")
    free_gb = usage.free / (1024**3)
    lines.append(("✅", f"Disk space  {free_gb:.1f} GB free"))

    # ------------------------------------------------------------------ #
    # Print results                                                        #
    # ------------------------------------------------------------------ #

    _console.print()
    _console.print("[bold]epub2audio — environment check[/bold]")
    _console.print()
    for symbol, message in lines:
        _console.print(f"  {symbol}  {message}")
    _console.print()

    # ------------------------------------------------------------------ #
    # Exit code                                                            #
    # ------------------------------------------------------------------ #

    if ffmpeg_path and ffprobe_path:
        _console.print("[green]All required dependencies found.[/green]")
        raise typer.Exit(code=0)
    else:
        missing = []
        if not ffmpeg_path:
            missing.append("FFmpeg")
        if not ffprobe_path:
            missing.append("FFprobe")
        _err_console.print(f"[red]Missing required dependencies: {', '.join(missing)}[/red]")
        raise typer.Exit(code=1)
