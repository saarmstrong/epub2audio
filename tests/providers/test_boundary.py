"""Architectural boundary tests for the provider-adapter layer.

These tests are static (import-level, no network) and assert the layering
rules from ADR-003:

  Layer 1 — Director  (director/) — business logic, provider-neutral
  Layer 2 — Providers (providers/) — mapping only, no analysis
  Layer 3 — Engine    (tts/)       — raw model I/O

Rules enforced here:
1. No providers/*.py file may import from epub2audio.director or epub2audio.epub.
2. No director/*.py file may import from epub2audio.providers or epub2audio.tts.

Rule #1 ensures adapters remain thin mappers without analysis logic.
Rule #2 ensures the Director remains provider-neutral.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SRC = Path(__file__).parent.parent.parent / "src" / "epub2audio"


def _python_files(package_dir: Path) -> list[Path]:
    """Return all *.py files under *package_dir* (excluding __pycache__)."""
    return [p for p in package_dir.rglob("*.py") if "__pycache__" not in p.parts]


def _import_names(source: str) -> list[str]:
    """Extract all top-level module strings imported in *source*.

    Uses the AST to avoid false positives from comments or string literals.

    Returns a list of dotted module names, e.g.::

        ["epub2audio.director", "epub2audio.models", "re"]
    """
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def _forbidden_in_files(
    package_dir: Path,
    forbidden_prefixes: list[str],
    *,
    skip_files: list[str] | None = None,
) -> list[str]:
    """Return violation strings for any import of a forbidden module prefix.

    Args:
        package_dir: Root directory of the package to scan.
        forbidden_prefixes: Module name prefixes that must NOT appear.
        skip_files: Filenames (not paths) to skip entirely.

    Returns:
        List of human-readable violation descriptions (empty = clean).
    """
    violations: list[str] = []
    skip_names = set(skip_files or [])
    for path in sorted(_python_files(package_dir)):
        if path.name in skip_names:
            continue
        source = path.read_text(encoding="utf-8")
        imports = _import_names(source)
        for imported in imports:
            for prefix in forbidden_prefixes:
                if imported == prefix or imported.startswith(prefix + "."):
                    violations.append(
                        f"{path.relative_to(_SRC.parent.parent)}: "
                        f"imports '{imported}' (forbidden prefix '{prefix}')"
                    )
    return violations


# ---------------------------------------------------------------------------
# Rule 1: providers/ must not import director/ or epub/
# ---------------------------------------------------------------------------


def test_providers_do_not_import_director() -> None:
    """providers/*.py must not import from epub2audio.director (no analysis logic in adapters)."""
    violations = _forbidden_in_files(
        _SRC / "providers",
        ["epub2audio.director"],
    )
    assert violations == [], "Provider adapters must not import the Director:\n" + "\n".join(
        violations
    )


def test_providers_do_not_import_epub() -> None:
    """providers/*.py must not import from epub2audio.epub (no EPUB knowledge in adapters)."""
    violations = _forbidden_in_files(
        _SRC / "providers",
        ["epub2audio.epub"],
    )
    assert violations == [], "Provider adapters must not import epub/:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Rule 2: director/ must not import providers/ or tts/
# ---------------------------------------------------------------------------


def test_director_does_not_import_providers() -> None:
    """director/*.py must not import from epub2audio.providers (Director is provider-neutral)."""
    violations = _forbidden_in_files(
        _SRC / "director",
        ["epub2audio.providers"],
    )
    assert violations == [], "Director must not import providers/:\n" + "\n".join(violations)


def test_director_does_not_import_tts() -> None:
    """director/*.py must not import from epub2audio.tts (Director is engine-neutral)."""
    violations = _forbidden_in_files(
        _SRC / "director",
        ["epub2audio.tts"],
    )
    assert violations == [], "Director must not import tts/:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Rule 3: NarrationPlan / NarrationSegment field names contain no SSML tokens
# ---------------------------------------------------------------------------


def _narration_field_names(models_path: Path) -> list[str]:
    """Return field names declared on Narration* classes in models.py (via AST)."""
    source = models_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and "Narration" in node.name:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.append(item.target.id)
    return names


def test_narration_plan_model_has_no_engine_specific_fields() -> None:
    """Narration* model field *names* must not contain SSML or engine-specific terms.

    We check field names only (via AST), not docstring prose — docstrings are
    allowed to reference SSML by name when explaining what future adapters will do.
    """
    field_names = _narration_field_names(_SRC / "models.py")
    # These substrings have no business as field names in provider-neutral models.
    engine_markers = ["ssml", "phoneme", "prosody", "kokoro_token", "openai_"]
    bad = [
        (name, marker)
        for name in field_names
        for marker in engine_markers
        if marker in name.lower()
    ]
    assert bad == [], f"Narration model fields contain engine-specific terms: {bad}"


# ---------------------------------------------------------------------------
# Rule 4 (structural): providers/__init__.py exports the Protocol and all adapters
# ---------------------------------------------------------------------------


def test_providers_package_exports_protocol_and_all_adapters() -> None:
    """The providers package must export NarrationProvider and all four stub adapters."""
    from epub2audio.providers import (  # noqa: F401
        AzureProvider,
        ElevenLabsProvider,
        GeminiProvider,
        KokoroProvider,
        NarrationProvider,
        OpenAIProvider,
        ProviderRequest,
    )
    # If the import above succeeds, all required names are exported.
