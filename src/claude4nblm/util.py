"""Small shared helpers."""

from __future__ import annotations

# Telegram rejects messages longer than 4096 characters.
TELEGRAM_MAX_CHARS = 4096


def chunk_text(text: str, limit: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Split ``text`` into chunks no longer than ``limit`` characters.

    Splits on line boundaries where possible so formatting stays readable; a
    single line longer than ``limit`` is hard-split. Empty input yields an empty
    list (nothing to send).
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not text:
        return []

    chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        # A single line longer than the limit must be hard-split on its own.
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]

        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks
