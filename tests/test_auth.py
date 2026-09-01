"""Tests for pairing codes and the persisted allowlist."""

from __future__ import annotations

import time

import pytest

from claude4nblm import auth
from claude4nblm.auth import Allowlist, generate_pairing_code


def test_pairing_code_is_six_digits():
    for _ in range(50):
        code = generate_pairing_code()
        assert len(code) == 6
        assert code.isdigit()


def test_add_remove_and_membership(tmp_path):
    al = Allowlist(tmp_path / "allow.json")
    assert not al.is_allowed(123)

    al.add(123, name="alice")
    assert al.is_allowed(123)
    assert 123 in al.all_ids()

    assert al.remove(123) is True
    assert not al.is_allowed(123)
    assert al.remove(123) is False  # already gone


def test_persistence_across_instances(tmp_path):
    path = tmp_path / "allow.json"
    Allowlist(path).add(999, name="bob")

    reloaded = Allowlist(path)
    assert reloaded.is_allowed(999)


def test_corrupt_file_is_tolerated(tmp_path):
    path = tmp_path / "allow.json"
    path.write_text("not json{{{", encoding="utf-8")
    al = Allowlist(path)  # should not raise
    assert al.all_ids() == []


def test_redeem_authorizes_matching_chat(tmp_path):
    al = Allowlist(tmp_path / "allow.json")
    code = al.start_pairing(555, name="carol")

    assert al.redeem("000000") is None  # wrong code
    assert al.redeem(code) == 555
    assert al.is_allowed(555)


def test_redeem_rejects_expired_code(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "PAIRING_TTL_SECONDS", 0)
    al = Allowlist(tmp_path / "allow.json")
    code = al.start_pairing(777)
    time.sleep(0.01)
    assert al.redeem(code) is None
    assert not al.is_allowed(777)
