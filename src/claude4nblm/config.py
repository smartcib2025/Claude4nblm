"""Configuration loading and validation.

Reads settings from environment variables (optionally via a ``.env`` file) and
validates that the required values are present, failing fast with a clear error.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _parse_chat_ids(raw: str | None) -> list[int]:
    """Parse a comma-separated list of chat IDs into ints, ignoring blanks."""
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError as exc:
            raise ConfigError(f"Invalid chat id in ALLOWED_CHAT_IDS: {part!r}") from exc
    return ids


def _mask(value: str | None) -> str:
    """Return a short, non-revealing preview of a secret (never the full value)."""
    if not value:
        return "unset"
    if len(value) <= 8:
        return "set(…)"
    return f"set({value[:6]}…{value[-2:]})"


@dataclass(frozen=True)
class Settings:
    """Validated application settings."""

    telegram_bot_token: str
    anthropic_api_key: str | None
    allowed_chat_ids: list[int] = field(default_factory=list)
    allowlist_path: Path = Path("./state/allowlist.json")
    workdir: Path = Path(".")
    system_prompt: str | None = None
    notebooklm_notebook: str | None = None
    # Model-access configuration (for diagnostics — the SDK reads these from env).
    anthropic_base_url: str | None = None
    anthropic_auth_token_set: bool = False
    anthropic_model: str | None = None

    def auth_summary(self) -> str:
        """A masked, human-readable description of how the model will be reached.

        Never includes a full key or token — only presence and a short prefix — so
        it is safe to log and to send back over Telegram.
        """
        base = self.anthropic_base_url or "default (api.anthropic.com)"
        token = "set" if self.anthropic_auth_token_set else "unset"
        return (
            f"API key: {_mask(self.anthropic_api_key)} · "
            f"auth token: {token} · "
            f"base URL: {base} · "
            f"model: {self.anthropic_model or 'default'}"
        )


def load_settings(env_file: str | os.PathLike[str] | None = ".env") -> Settings:
    """Load and validate settings from the environment.

    Args:
        env_file: Path to a dotenv file to load before reading the environment.
            Pass ``None`` to skip loading a file (env vars must already be set).

    Raises:
        ConfigError: If a required variable is missing or malformed.
    """
    if env_file is not None and Path(env_file).exists():
        load_dotenv(env_file)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN is required. Create a bot with @BotFather and "
            "set it in your .env file."
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip() or None

    return Settings(
        telegram_bot_token=token,
        anthropic_api_key=api_key,
        allowed_chat_ids=_parse_chat_ids(os.getenv("ALLOWED_CHAT_IDS")),
        allowlist_path=Path(os.getenv("ALLOWLIST_PATH", "./state/allowlist.json")),
        workdir=Path(os.getenv("WORKDIR", ".")),
        system_prompt=os.getenv("CLAUDE_SYSTEM_PROMPT", "").strip() or None,
        notebooklm_notebook=os.getenv("NOTEBOOKLM_NOTEBOOK", "").strip() or None,
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", "").strip() or None,
        anthropic_auth_token_set=bool(os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "").strip() or None,
    )
