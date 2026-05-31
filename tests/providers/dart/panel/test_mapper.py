"""core/panel canonical mirror — rawId→disclosureKey resolve (데이터 경량).

``core/panel/canonical.py`` 의 ``resolveDisclosureKey``(단건)/``resolveBatch``(컬럼 부착).
bridge lookup 기반 — 미등록 rawId 는 None, empty df 는 passthrough.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel.mapper import canonicalKey, canonicalKeyExpr, resolveBatch, resolveDisclosureKey

pytestmark = pytest.mark.unit


def test_resolve_disclosure_key_unknown_none() -> None:
    """미등록 rawId → None (bridge 비어도 안전)."""
    assert resolveDisclosureKey("__nonexistent_rawid__", "kr") is None


def test_resolve_batch_adds_disclosure_key_column() -> None:
    """xbrlClass 컬럼 df → disclosureKey 컬럼 부착."""
    df = pl.DataFrame({"xbrlClass": ["BS_C", None]})
    out = resolveBatch(df, marketNs="kr")
    assert "disclosureKey" in out.columns
    assert out.height == 2


def test_resolve_batch_empty_passthrough() -> None:
    """빈 df 는 그대로 (lookup 0)."""
    empty = pl.DataFrame({"xbrlClass": []}, schema={"xbrlClass": pl.Utf8})
    assert resolveBatch(empty, marketNs="kr").height == 0


# ── canonicalKey scope-strip 순수함수 (단일 SSOT 정렬키) ──

_CANONICAL_CASES = [
    # (xbrlClass, expected canonicalKey)
    ("BS", "BS"),
    ("BS_C", "BS"),
    ("BS_S", "BS"),  # era drift 병합 (scope 는 별도 산출)
    ("CF", "CF"),
    ("CF_C", "CF"),
    ("CF_S", "CF"),
    ("EF_C", "EF"),
    ("EF_S", "EF"),
    ("IS_C1", "IS1"),
    ("IS_C2", "IS2"),  # 손익
    ("IS_C3", "IS3"),  # 포괄손익 — IS2 와 분리 유지
    ("IS_S2", "IS2"),
    ("IS2", "IS2"),  # 옛 양식 = 신 세부폼 병합
    ("IS3", "IS3"),
    ("NT_C_D826380", "NT_D826380"),  # 재고 연결
    ("NT_S_D826385", "NT_D826385"),  # 재고 별도 (C/S D-code 번호 자체 다름)
    ("NT_C_D810000", "NT_D810000"),
    ("{XBRL}NT_C_D810000", "NT_D810000"),  # {XBRL} prefix 방어
    ("COVER", "COVER"),  # 정형폼 passthrough
    ("PB_VAL", "PB_VAL"),
    (None, None),
    ("", None),
    ("   ", None),
]


@pytest.mark.parametrize(("raw", "expected"), _CANONICAL_CASES)
def test_canonical_key_scope_strip(raw: str | None, expected: str | None) -> None:
    """canonicalKey scope-strip 규칙 전 케이스 (§1 표)."""
    assert canonicalKey(raw) == expected


def test_canonical_key_expr_matches_scalar() -> None:
    """canonicalKeyExpr(polars) ≡ canonicalKey(scalar) — 규칙 분기 0 (단일 SSOT)."""
    raws = [c[0] for c in _CANONICAL_CASES]
    df = pl.DataFrame({"xbrlClass": raws}, schema={"xbrlClass": pl.Utf8})
    exprOut = df.select(canonicalKeyExpr())["canonicalKey"].to_list()
    scalarOut = [canonicalKey(r) for r in raws]
    assert exprOut == scalarOut
