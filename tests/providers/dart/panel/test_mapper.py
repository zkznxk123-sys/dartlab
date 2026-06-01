"""panel mapper — canonicalKey scope-strip + rowIdentity + resolveBatch (순수 규칙).

``mapper.py`` 의 ``canonicalKey``/``canonicalKeyExpr``(정렬키), ``rowIdentity``/``rowIdentityExpr``
(spine·diff 행 식별), ``resolveBatch``(native canonicalKey 부착). bridge lookup 0 — 정부 코드 SSOT.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.panel.mapper import (
    canonicalKey,
    canonicalKeyExpr,
    resolveBatch,
    rowIdentity,
    rowIdentityExpr,
)

pytestmark = pytest.mark.unit


def test_resolve_batch_adds_disclosure_key_column() -> None:
    """xbrlClass 컬럼 df → disclosureKey(=canonicalKey) 컬럼 부착."""
    df = pl.DataFrame({"xbrlClass": ["BS_C", None]})
    out = resolveBatch(df, marketNs="kr")
    assert "disclosureKey" in out.columns
    assert out.height == 2
    assert out["disclosureKey"].to_list() == ["BS", None]


def test_resolve_batch_empty_passthrough() -> None:
    """빈 df 는 그대로 (변환 0)."""
    empty = pl.DataFrame({"xbrlClass": []}, schema={"xbrlClass": pl.Utf8})
    assert resolveBatch(empty, marketNs="kr").height == 0


def test_resolve_batch_default_market() -> None:
    """marketNs 기본값 'kr' — 인자 없이 호출 가능 (canonicalKey 시장 무관)."""
    df = pl.DataFrame({"xbrlClass": ["NT_C_D826380"]})
    assert resolveBatch(df)["disclosureKey"].to_list() == ["NT_D826380"]


# ── rowIdentity — spine·diff 행 식별 SSOT (keyed=disclosureKey / narrative=NARR::) ──


def test_row_identity_keyed_is_disclosure_key() -> None:
    """disclosureKey 있는 행 → disclosureKey 자체가 identity (era-stable)."""
    assert rowIdentity("NT_D826380", "III. 재무에 관한 사항", "3. 연결재무제표 주석") == "NT_D826380"


def test_row_identity_narrative_uses_chapter_section() -> None:
    """disclosureKey 부재 행 → NARR::chapter␟section (정부 양식 제목 안정)."""
    assert rowIdentity(None, "I. 회사의 개요", "1. 회사의 개요") == "NARR::I. 회사의 개요␟1. 회사의 개요"
    assert rowIdentity("", "I", "1") == "NARR::I␟1"


def test_row_identity_expr_matches_scalar() -> None:
    """rowIdentityExpr(polars) ≡ rowIdentity(scalar) — 규칙 분기 0 (단일 SSOT)."""
    df = pl.DataFrame(
        {
            "disclosureKey": ["BS", None, "NT_D826380", ""],
            "chapter": ["c", "I. 회사의 개요", "III", "X"],
            "sectionLeaf": ["s", "1. 회사의 개요", "3.주석", "y"],
        }
    )
    exprOut = df.select(rowIdentityExpr())["_rowIdentity"].to_list()
    scalarOut = [
        rowIdentity(k, c, s) for k, c, s in zip(df["disclosureKey"], df["chapter"], df["sectionLeaf"], strict=True)
    ]
    assert exprOut == scalarOut


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
