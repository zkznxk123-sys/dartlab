"""gather.original.dart.keys — DART 키 resolve unit 테스트 (네트워크 0)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_explicit_args_win() -> None:
    """인자(apiKeys/apiKey)가 최우선."""
    from dartlab.gather.original.dart.keys import resolveDartKeys

    assert resolveDartKeys(apiKeys=["a", "b"]) == ["a", "b"]
    assert resolveDartKeys(apiKey="solo") == ["solo"]


def test_env_multi_over_single(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """DART_API_KEYS(복수)가 DART_API_KEY(단일)보다 키 많아 채택 (키풀 극대화)."""
    from dartlab.gather.original.dart.keys import resolveDartKeys

    monkeypatch.setenv("DART_API_KEYS", "k1,k2,k3")
    monkeypatch.setenv("DART_API_KEY", "single")
    assert resolveDartKeys(startPath=tmp_path) == ["k1", "k2", "k3"]


def test_no_keys_empty(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """키 부재면 빈 list (호출자 안내 분기)."""
    from dartlab.gather.original.dart.keys import resolveDartKeys

    monkeypatch.delenv("DART_API_KEYS", raising=False)
    monkeypatch.delenv("DART_API_KEY", raising=False)
    assert resolveDartKeys(startPath=tmp_path) == []
