"""TOML-based configuration with Pydantic Settings for epub2audio.

Configuration is loaded in the following precedence order (highest first):
1. CLI flags (passed via model_validate overrides)
2. Explicit --config file path (TOML)
3. epub2audio.toml in the current working directory
4. ~/.config/epub2audio/config.toml
5. Application defaults
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings for epub2audio.

    All fields can be overridden by environment variables with the
    ``EPUB2AUDIO_`` prefix (e.g. ``EPUB2AUDIO_VOICE=af_sky``).
    """

    model_config = SettingsConfigDict(
        env_prefix="EPUB2AUDIO_",
        env_file=None,
        populate_by_name=True,
    )

    voice: str = Field(default="af_heart", description="Kokoro voice identifier.")
    language: str = Field(default="en-us", description="BCP-47 language tag.")
    speed: Annotated[float, Field(ge=0.25, le=4.0)] = Field(
        default=1.0, description="TTS speed multiplier (0.25–4.0)."
    )
    output_format: Literal["mp3", "m4b"] = Field(
        default="mp3",
        description="Output container: per-chapter MP3 files ('mp3') or a single M4B ('m4b').",
    )
    bitrate: str = Field(default="96k", description="MP3 output bitrate (e.g. '96k').")
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz.")
    normalize: bool = Field(default=True, description="Apply loudness normalisation.")
    resume: bool = Field(default=True, description="Resume interrupted conversions.")
    workers: Annotated[int, Field(ge=1, le=16)] = Field(
        default=1, description="Number of parallel TTS workers (1–16)."
    )
    output_dir: Path = Field(default=Path("."), description="Output directory for MP3s.")
    keep_intermediates: bool = Field(
        default=False,
        description="Keep intermediate segment WAV files after successful conversion.",
    )
    pronunciation_dictionary: Path | None = Field(
        default=None,
        description="Path to a pronunciations.yaml lexicon, or None to disable.",
    )

    @field_validator("output_format", mode="before")
    @classmethod
    def normalize_output_format(cls, v: Any) -> Any:
        """Lower-case and strip the output format so 'MP3'/'M4B' are accepted."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("bitrate")
    @classmethod
    def validate_bitrate(cls, v: str) -> str:
        """Ensure bitrate is a non-empty string like '96k' or '128k'."""
        v = v.strip()
        if not v:
            raise ValueError("bitrate must be a non-empty string such as '96k'")
        return v

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """Ensure sample_rate is a positive integer."""
        if v <= 0:
            raise ValueError("sample_rate must be a positive integer")
        return v


def _load_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file and return its contents as a dict.

    Returns an empty dict if the file does not exist.
    """
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        return {}


def load_settings(config_path: Path | None = None) -> Settings:
    """Load Settings by merging TOML sources according to precedence.

    Args:
        config_path: Explicit path to a TOML config file (highest precedence
            after CLI flags, lower than environment variables).

    Returns:
        A fully resolved :class:`Settings` instance.

    The search order for TOML files (first match wins; all are merged bottom-up
    so that higher-precedence sources override lower ones):

    1. ``config_path`` argument (explicit ``--config`` flag)
    2. ``epub2audio.toml`` in the current working directory
    3. ``~/.config/epub2audio/config.toml``
    """
    # Build merged dict starting from lowest precedence
    merged: dict[str, Any] = {}

    # 3. User-level config
    user_config = Path.home() / ".config" / "epub2audio" / "config.toml"
    merged.update(_load_toml(user_config))

    # 2. Project-level config (cwd)
    cwd_config = Path.cwd() / "epub2audio.toml"
    merged.update(_load_toml(cwd_config))

    # 1. Explicit --config path
    if config_path is not None:
        merged.update(_load_toml(config_path))

    return Settings(**merged)
