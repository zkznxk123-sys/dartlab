"""Sentinel — Plan v7 R0: 분기 schema 만 노출, 연간은 toDict 합성 경유.

사용자 피드백 (2026-04-08): 시계열 view 에 분기+연간 둘 다 노출은 schema noise.
- `c.IS / c.BS / c.CF / c.CIS` 는 기본 분기 컬럼만 (연간 컬럼 없음).
- calc 함수는 `toDictBySnakeId` 가 분기에서 자동 합성하므로 `data[sid]['2024']` 사용 가능.
- 연간 컬럼이 필요하면 별도 명시 옵션 (`includeAnnual=True`) 으로만 노출.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_data]


def test_dart_is_no_annual_column_default():
    """공개 show 은퇴 → c.panel("IS") 단일 표면. 연간 컬럼 default 없음."""
    import dartlab

    c = dartlab.Company("000660")
    df = c.panel("IS")
    assert df is not None

    annCols = [col for col in df.columns if col.isdigit() and len(col) == 4]
    assert annCols == [], f"연간 컬럼이 default 노출됨: {annCols}"
    assert any("Q" in col for col in df.columns), "분기 컬럼이 사라짐"


def test_dart_bs_no_annual_column_default():
    """c.panel("BS") 도 동일 — 분기 컬럼만."""
    import dartlab

    c = dartlab.Company("000660")
    df = c.panel("BS")
    assert df is not None
    annCols = [col for col in df.columns if col.isdigit() and len(col) == 4]
    assert annCols == [], f"BS 에도 연간 컬럼 default 노출됨: {annCols}"


def test_toDictBySnakeId_synthesizes_annual_for_flow():
    """toDictBySnakeId 가 IS 분기에서 연간 합성 (4분기 합)."""
    import dartlab
    from dartlab.core.utils.helpers import toDictBySnakeId

    c = dartlab.Company("000660")
    parsed = toDictBySnakeId(c.select("IS", ["매출액"]))
    assert parsed is not None
    data, periods = parsed
    assert "sales" in data or "매출액" in data
    rev = data.get("sales") or data.get("매출액")
    # 합성된 연간 값 존재
    assert "2025" in rev or "2024" in rev, f"연간 합성 안됨. keys={list(rev.keys())[:10]}"
    yr = "2025" if "2025" in rev else "2024"
    annual = rev[yr]
    if annual is not None:
        # SK하이닉스 매출 ≈ 50조 이상
        assert annual > 30e12, f"{yr} 합성값 비정상: {annual}"


def test_toDictBySnakeId_synthesizes_annual_for_stock():
    """toDictBySnakeId 가 BS 분기에서 Q4 = 연말잔액 alias."""
    import dartlab
    from dartlab.core.utils.helpers import toDictBySnakeId

    c = dartlab.Company("000660")
    parsed = toDictBySnakeId(c.select("BS", ["자산총계"]))
    assert parsed is not None
    data, _ = parsed
    ta = data.get("assets") or data.get("자산총계") or data.get("total_assets")
    assert ta is not None
    yr = "2025" if "2025" in ta else "2024"
    annual = ta.get(yr)
    q4 = ta.get(f"{yr}Q4")
    if annual is not None and q4 is not None:
        assert annual == q4, f"BS {yr} 합성값({annual}) ≠ Q4({q4})"


def test_annualColsFromPeriods_picks_synthesized():
    """annualColsFromPeriods 가 toDict 가 합성한 연간 라벨을 우선."""
    import dartlab
    from dartlab.core.utils.helpers import annualColsFromPeriods, toDictBySnakeId

    c = dartlab.Company("000660")
    parsed = toDictBySnakeId(c.select("IS", ["매출액"]))
    assert parsed is not None
    _, periods = parsed
    yCols = annualColsFromPeriods(periods)
    assert yCols, "연간 컬럼 추출 실패"
    assert yCols[0].isdigit(), f"annualColsFromPeriods[0]={yCols[0]} (4자리 연도 기대)"
    assert "Q" not in yCols[0]
