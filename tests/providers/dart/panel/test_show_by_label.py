"""panel reader.resolveKeyArg — key → canonicalKey 정규화 (P4, 데이터 경량/synthetic).

show/cross 가 받는 key 를 canonicalKey 정렬키로 정규화: exact canonicalKey 는 항상 포함,
byLabel 시 _label.parquet labelKr substring 매칭 canonicalKey 추가. _label 없으면 exact 만.
synthetic _label 을 monkeypatch 로 주입 — 실데이터 불요.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel import reader
from dartlab.providers.dart.panel.reader import resolveKeyArg

pytestmark = pytest.mark.unit


def test_resolve_key_arg_exact_no_label() -> None:
    """byLabel=False → exact canonicalKey 자기 자신만 (라벨 read 0)."""
    assert resolveKeyArg("NT_D826380", byLabel=False) == ["NT_D826380"]
    assert resolveKeyArg("BS", byLabel=False) == ["BS"]


def _synthLabel(tmp_path) -> object:
    p = tmp_path / "_label.parquet"
    pl.DataFrame(
        {
            "canonicalKey": ["NT_D826380", "NT_D826385", "BS"],
            "labelKr": ["재고자산", "재고자산", "재무상태표"],
        }
    ).write_parquet(str(p))
    return p


def test_resolve_key_arg_label_substring(tmp_path, monkeypatch) -> None:
    """byLabel=True → labelKr substring 매칭 canonicalKey 추가 ('재고'→연결/별도 둘 다)."""
    lp = _synthLabel(tmp_path)
    monkeypatch.setattr(reader, "_labelPath", lambda marketNs="kr": lp)
    out = resolveKeyArg("재고", marketNs="kr", byLabel=True)
    assert "NT_D826380" in out
    assert "NT_D826385" in out
    assert "BS" not in out


def test_resolve_key_arg_exact_always_present_with_label(tmp_path, monkeypatch) -> None:
    """exact canonicalKey 는 라벨 매칭과 무관하게 항상 결과 포함."""
    lp = _synthLabel(tmp_path)
    monkeypatch.setattr(reader, "_labelPath", lambda marketNs="kr": lp)
    out = resolveKeyArg("NT_D826380", marketNs="kr", byLabel=True)
    assert "NT_D826380" in out
