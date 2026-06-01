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
    dedupKeyed,
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


def _keyedRow(key: str, scope: str, period: str, content: str, xc: str | None) -> dict:
    """dedupKeyed 테스트용 최소 행 (READ 정렬 단계 입력 형태)."""
    return {"disclosureKey": key, "scope": scope, "period": period, "contentRaw": content, "xbrlClass": xc}


def test_dedup_keyed_body_attachment_one_per_period() -> None:
    """같은 (key,scope,period)가 본문+첨부 2행이면 1행으로 — 구조화(xbrlClass)>최장 우선."""
    df = pl.DataFrame(
        [
            _keyedRow("BS", "consolidated", "2024Q4", "X" * 50, "BS_C"),  # 구조화(짧음)
            _keyedRow("BS", "consolidated", "2024Q4", "Y" * 99, None),  # 첨부(길지만 비구조화)
        ]
    )
    out = dedupKeyed(df)
    assert out.height == 1
    assert out["xbrlClass"][0] == "BS_C"  # xbrlClass 보유 우선 (길이보다 먼저)


def test_dedup_keyed_distinct_periods_preserved() -> None:
    """period 가 subset 에 있어 다기간 격자 보존 — 같은 (key,scope) 라도 period 다르면 둘 다 유지."""
    df = pl.DataFrame(
        [
            _keyedRow("BS", "consolidated", "2024Q4", "a" * 10, "BS_C"),
            _keyedRow("BS", "consolidated", "2023Q4", "b" * 10, "BS_C"),
        ]
    )
    out = dedupKeyed(df)
    assert out.height == 2
    assert set(out["period"].to_list()) == {"2024Q4", "2023Q4"}


def test_dedup_keyed_scope_separates() -> None:
    """연결/별도(scope)는 같은 canonicalKey 라도 분리 보존."""
    df = pl.DataFrame(
        [
            _keyedRow("BS", "consolidated", "2024Q4", "c" * 10, "BS_C"),
            _keyedRow("BS", "standalone", "2024Q4", "s" * 10, "BS_S"),
        ]
    )
    out = dedupKeyed(df)
    assert out.height == 2
    assert set(out["scope"].to_list()) == {"consolidated", "standalone"}


def test_dedup_keyed_narrative_untouched() -> None:
    """narrative(disclosureKey null) 행은 dedup 대상 아님 — 전부 보존."""
    df = pl.DataFrame(
        [
            {"disclosureKey": None, "scope": "consolidated", "period": "2024Q4", "contentRaw": "n1", "xbrlClass": None},
            {"disclosureKey": None, "scope": "consolidated", "period": "2024Q4", "contentRaw": "n2", "xbrlClass": None},
        ]
    )
    out = dedupKeyed(df)
    assert out.height == 2


def test_dedup_keyed_no_scope_column_passthrough() -> None:
    """scope 컬럼 부재(빌드 단계 등) 시 입력 그대로 — READ 전용 가드."""
    df = pl.DataFrame([{"disclosureKey": "BS", "period": "2024Q4", "contentRaw": "x", "xbrlClass": "BS_C"}])
    out = dedupKeyed(df)
    assert out.height == 1
