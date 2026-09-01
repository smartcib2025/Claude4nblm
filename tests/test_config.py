"""Tests for settings diagnostics (auth summary masking)."""

from __future__ import annotations

from claude4nblm.config import Settings, _mask


def _settings(**kw) -> Settings:
    base = {"telegram_bot_token": "t", "anthropic_api_key": None}
    base.update(kw)
    return Settings(**base)


def test_mask_never_reveals_full_secret():
    secret = "sk-ant-abcdefghijklmnop1234"
    masked = _mask(secret)
    assert secret not in masked
    assert masked.startswith("set(")
    # Short values are masked without exposing characters beyond the marker.
    assert _mask("short") == "set(…)"
    assert _mask(None) == "unset"
    assert _mask("") == "unset"


def test_auth_summary_masks_key_and_reports_defaults():
    s = _settings(anthropic_api_key="sk-ant-abcdefghijklmnop1234")
    summary = s.auth_summary()
    assert "sk-ant-abcdefghijklmnop1234" not in summary
    assert "default (api.anthropic.com)" in summary
    assert "auth token: unset" in summary
    assert "model: default" in summary


def test_auth_summary_flags_gateway_config():
    s = _settings(
        anthropic_api_key=None,
        anthropic_base_url="https://gw.example.com",
        anthropic_auth_token_set=True,
        anthropic_model="claude-x",
    )
    summary = s.auth_summary()
    assert "API key: unset" in summary
    assert "https://gw.example.com" in summary
    assert "auth token: set" in summary
    assert "model: claude-x" in summary
