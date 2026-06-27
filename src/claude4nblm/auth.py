"""Pairing-code generation and a persisted allowlist of authorized chats.

The bot only talks to chats on the allowlist. Unknown chats receive a pairing
code; the operator authorizes them by entering that code in the bridge terminal
(see :mod:`claude4nblm.bot`). The allowlist is persisted to JSON so that
authorizations survive restarts.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

# How long a generated pairing code stays valid, in seconds.
PAIRING_TTL_SECONDS = 600


def generate_pairing_code() -> str:
    """Return a cryptographically random 6-digit pairing code."""
    return f"{secrets.randbelow(1_000_000):06d}"


@dataclass
class _Pending:
    code: str
    name: str
    created_at: float


class Allowlist:
    """A persisted set of authorized Telegram chat IDs plus pending pairings."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._entries: dict[int, dict] = {}
        self._pending: dict[int, _Pending] = {}
        self.load()

    # --- persistence -----------------------------------------------------
    def load(self) -> None:
        """Load entries from disk; tolerate a missing or empty file."""
        if not self.path.exists():
            self._entries = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._entries = {}
            return
        # Keys are serialized as strings in JSON; coerce back to int.
        self._entries = {int(k): v for k, v in raw.items()}

    def save(self) -> None:
        """Persist entries to disk, creating parent directories as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {str(k): v for k, v in self._entries.items()}
        self.path.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # --- membership ------------------------------------------------------
    def is_allowed(self, chat_id: int) -> bool:
        return chat_id in self._entries

    def add(self, chat_id: int, name: str = "") -> None:
        """Authorize ``chat_id`` and persist immediately."""
        self._entries[chat_id] = {
            "name": name,
            "added": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._pending.pop(chat_id, None)
        self.save()

    def remove(self, chat_id: int) -> bool:
        """De-authorize ``chat_id``. Returns True if it was present."""
        existed = self._entries.pop(chat_id, None) is not None
        if existed:
            self.save()
        return existed

    def all_ids(self) -> list[int]:
        return list(self._entries)

    # --- pairing ---------------------------------------------------------
    def start_pairing(self, chat_id: int, name: str = "") -> str:
        """Create (or refresh) a pairing code for ``chat_id`` and return it."""
        code = generate_pairing_code()
        self._pending[chat_id] = _Pending(code=code, name=name, created_at=time.time())
        return code

    def redeem(self, code: str) -> int | None:
        """Authorize the chat whose pending code matches ``code``.

        Expired codes are ignored (and pruned). Returns the chat ID that was
        authorized, or ``None`` if no valid pending code matches.
        """
        code = code.strip()
        now = time.time()
        for chat_id, pending in list(self._pending.items()):
            if now - pending.created_at > PAIRING_TTL_SECONDS:
                del self._pending[chat_id]
                continue
            if pending.code == code:
                self.add(chat_id, pending.name)
                return chat_id
        return None
