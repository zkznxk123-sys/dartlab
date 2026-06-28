"""P1a G2 백테스트 게이트 (requires_data) — de-gate 내재가치 예측력 (02a §5 G2).

방법: t 시점(basePeriod, point-in-time 재무만) calcDFV → t+12M 실현주가 방향 검증.
basePeriod 스레딩(look-ahead 제거) + _rimCalc fix(full dFV) 위에서 동작. 게이트 = §5
"방향 적중 > 55%" + 판별(저평가 코호트 평균실현 ≥ 고평가 코호트).

⚠ 로컬 바레 pytest 는 gather httpx 클라이언트 close 라이프사이클로 실행 불가 → CI 영속
async 컨텍스트(네트워크)에서 실행. 방법론 검증 완료(`tests/_attempts/valuationUplift/g2_pit.py`):
basePeriod=2024Q4·full dFV → 10/14(71%)>55%, 저평가 +181% vs 고평가 −18%(스프레드 +199%p).
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.requires_data, pytest.mark.slow]

# 대표 유니버스 (섹터 분산) — basePeriod 시점에 상장·재무 존재.
_UNIVERSE = [
    "005930",
    "000660",
    "005380",
    "035420",
    "000270",
    "034730",
    "003550",
    "012330",
    "028260",
    "066570",
    "035720",
    "003230",
]
_BASE_PERIOD = "2024Q4"  # t = 2025 중반 가용 (FY2024)
_MIN_HITRATE = 0.55  # 02a §5 게이트
_MIN_SAMPLE = 8


def _backtestRows():
    """각 종목: (dFV[t], 시작가[t], 12M 실현수익%, under, correct). 가격/재무 없으면 skip."""
    import dartlab
    from dartlab.analysis.valuation._dFVCalcs import _inferShares
    from dartlab.analysis.valuation.dFV import calcDFV
    from dartlab.core.di import getMacroProvider

    g = getMacroProvider().getDefaultGather()
    rows = []
    for code in _UNIVERSE:
        c = dartlab.Company(code)
        try:
            p = g.price(code)
            if p is None or not getattr(p, "height", 0) or p.height < 200:
                continue
            pStart, pEnd = float(p["close"][0]), float(p["close"][-1])
            ret = (pEnd / pStart - 1) * 100.0
            sh = _inferShares(c)
            if not sh:
                continue
            # t 시점 시장가 주입(point-in-time): currentPrice/marketCap = 시작가.
            if getattr(c, "_cache", None) is None:
                c._cache = {}
            c._cache["_priceContext"] = {
                "currentPrice": pStart,
                "marketCap": pStart * sh,
                "per": None,
                "pbr": None,
                "isStale": True,
            }
            c.currentPrice = pStart
            r = calcDFV(c, basePeriod=_BASE_PERIOD)
            if not r or not r.get("dFV"):
                continue
            iv = r["dFV"]
            under = iv > pStart
            correct = (under and ret > 0) or (not under and ret < 0)
            rows.append((iv, pStart, ret, under, correct))
        finally:
            del c
            gc.collect()
    return rows


def test_g2_directional_hitrate_and_discrimination():
    """de-gate IV 의 12M 방향 적중 > 55% + 저평가 코호트가 고평가 코호트 능가."""
    rows = _backtestRows()
    assert len(rows) >= _MIN_SAMPLE, f"표본 부족 {len(rows)} < {_MIN_SAMPLE} (데이터 환경 확인)"

    hit = sum(1 for r in rows if r[4]) / len(rows)
    assert hit > _MIN_HITRATE, f"방향 적중 {hit:.0%} ≤ {_MIN_HITRATE:.0%} (G2 게이트 미달)"

    under = [r[2] for r in rows if r[3]]
    over = [r[2] for r in rows if not r[3]]
    if under and over:  # 양 코호트 존재 시 판별력 검증
        assert (sum(under) / len(under)) >= (sum(over) / len(over)), "저평가 코호트가 고평가 코호트 미능가(판별 실패)"
