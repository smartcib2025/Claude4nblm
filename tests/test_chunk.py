"""Tests for Telegram message chunking."""

from __future__ import annotations

import pytest

from claude4nblm.util import TELEGRAM_MAX_CHARS, chunk_text


def test_empty_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_is_single_chunk():
    assert chunk_text("hello world") == ["hello world"]


def test_respects_limit():
    text = "\n".join(f"line {i}" for i in range(1000))
    chunks = chunk_text(text)
    assert all(len(c) <= TELEGRAM_MAX_CHARS for c in chunks)
    # Reassembling on newlines reproduces the original text.
    assert "\n".join(chunks) == text


def test_hard_splits_a_single_long_line():
    line = "x" * (TELEGRAM_MAX_CHARS * 2 + 5)
    chunks = chunk_text(line)
    assert all(len(c) <= TELEGRAM_MAX_CHARS for c in chunks)
    assert "".join(chunks) == line


def test_custom_limit():
    chunks = chunk_text("aaa\nbbb\nccc", limit=7)
    assert all(len(c) <= 7 for c in chunks)


def test_invalid_limit_raises():
    with pytest.raises(ValueError):
        chunk_text("hi", limit=0)
