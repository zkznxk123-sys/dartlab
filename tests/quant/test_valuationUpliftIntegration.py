"""P1a calcDFV 통합 게이트 (requires_data) — de-gate 출력 배선 확인.

구조만 검증(시장가 비의존): reinvestmentCheck(=g=reinvest×ROIC fade 진단)·scenarios 배선이
calcDFV 출력에 들어오고 크래시가 없음을 실데이터로 확인. dFV 절대값은 시장가 의존이라
별도(damodaranPhase4 범위가드) — 본 게이트는 값이 아닌 *배선*.

⚠ 바레 pytest 로컬 실행은 gather httpx 클라이언트 close 라이프사이클(첫 fetch 후 닫힘)로
불가 → CI 영속 async 컨텍스트에서 실행. 배선 자체는 close→no-op 우회 스모크로 사전 확인됨
(tests/_attempts/valuationUplift/smoke_calcdfv.py): 005930 reinvestmentCheck.fundamentalGrowth=8.91.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.requires_data, pytest.mark.slow]


def test_calcdfv_reinvestment_check_wired():
    """calcDFV 출력에 reinvestmentCheck(fundamentalGrowth·reinvestRate)·scenarios 배선."""
    import dartlab
    from dartlab.analysis.valuation.dFV import calcDFV

    c = dartlab.Company("005930")
    try:
        r = calcDFV(c)
        assert r is not None, "calcDFV None"
        rc = r.get("reinvestmentCheck")
        assert rc is not None, "reinvestmentCheck 미배선 (de-gate 회귀)"
        assert rc.get("fundamentalGrowth") is not None
        assert 0.0 <= rc.get("reinvestRate", -1) <= 0.9
        assert "scenarios" in r and set(r["scenarios"]) == {"bull", "base", "bear"}
    finally:
        del c
        gc.collect()


def test_calcdfv_no_crash_with_degate_outputs():
    """de-gate 출력(scenarios·reinvestmentCheck) 추가 후 다종목 calcDFV 무크래시."""
    import dartlab
    from dartlab.analysis.valuation.dFV import calcDFV

    for code in ("035420", "000660"):  # NAVER(dcf2stage)·SK하이닉스 — 스모크 확인 종목
        c = dartlab.Company(code)
        try:
            r = calcDFV(c)
            assert r is None or "scenarios" in r
        finally:
            del c
            gc.collect()
