"""Sentinel — `c.notes.*` 단위 일관성 회귀 차단.

dartlab notes accessor 가 모두 원 단위로 노출되어야 한다 (Layer 1 root fix).
백만원 raw 가 들어오면 fail. Phase A2 의 ground truth (5 sample 종목) 회귀.

기준: notes magnitude (log10) 가 finance ground truth 와 ±2 자리 이내.
- 백만원 raw 면 −6 차이 → 즉시 fail
- 정상 (원 단위) 이면 ±2 이내
"""

from __future__ import annotations

import math

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_data]


def _maxAbsLog(df, col: str) -> float | None:
    """DataFrame 의 col 컬럼 abs max log10."""
    if df is None or not hasattr(df, "columns") or col not in df.columns:
        return None
    vals = [v for v in df[col].to_list() if v is not None and v != 0]
    if not vals:
        return None
    mx = max(abs(v) for v in vals)
    return math.log10(mx) if mx > 0 else None


@pytest.mark.parametrize(
    "stockCode,notesKey,refLog,tolerance",
    [
        # SK하이닉스 — Phase A2 검증된 ground truth (Layer 1 fix 후)
        ("000660", "costByNature", 13.1, 1.0),       # IS 매출원가와 ±1
        ("000660", "tangibleAsset", 13.9, 1.0),      # BS 유형자산과 ±1
        ("000660", "inventory", 13.2, 1.0),          # BS 재고자산과 ±1
        ("000660", "borrowings", 13.4, 1.0),         # 통합 차입금과 ±1
        # 삼성전자 — 더 큰 회사
        ("005930", "costByNature", 14.0, 1.0),
        ("005930", "tangibleAsset", 14.3, 1.0),
        ("005930", "segments", 14.5, 1.0),
        # HMM — 작은 회사
        ("011200", "costByNature", 12.4, 1.0),
        ("011200", "tangibleAsset", 12.9, 1.0),
    ],
)
def test_notes_unit_consistency(stockCode: str, notesKey: str, refLog: float, tolerance: float):
    """notes accessor 가 원 단위로 노출되어야 한다 (백만원 raw 면 fail)."""
    import dartlab

    c = dartlab.Company(stockCode)
    df = getattr(c.notes, notesKey, None)
    if df is None or not hasattr(df, "columns"):
        pytest.skip(f"{stockCode} {notesKey} 데이터 없음")

    # 최신 연도 컬럼 찾기
    yearCols = []
    for col in df.columns:
        s = str(col)
        # "2025", "2025_기말", "2025_기초" 등
        if s[:4].isdigit() and len(s) >= 4:
            yearCols.append(s)
    if not yearCols:
        pytest.skip(f"{stockCode} {notesKey} 연도 컬럼 없음")

    yearCols.sort(reverse=True)
    actualLog = None
    for col in yearCols[:3]:
        v = _maxAbsLog(df, col)
        if v is not None:
            actualLog = v
            break

    assert actualLog is not None, f"{stockCode} {notesKey} 모든 연도 결손"
    diff = abs(actualLog - refLog)
    assert diff <= tolerance, (
        f"{stockCode} {notesKey} log10={actualLog:.2f} (ref={refLog}, ±{tolerance}). "
        f"백만원 raw 가 들어왔다면 −6 차이. fix 회귀."
    )
