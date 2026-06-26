"""brokerage.fetch 단위 테스트 — 디코드 + 스모크 (네트워크 0)."""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.sources.brokerage.fetch import _decode

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.sources.brokerage.fetch")
    importlib.import_module("dartlab.gather.sources.brokerage")


def test_decode_with_enc() -> None:
    raw = "리포트".encode("cp949")
    assert _decode(raw, "garbled", "cp949") == "리포트"


def test_decode_no_enc_uses_text() -> None:
    assert _decode(b"x", "이미디코드", None) == "이미디코드"
