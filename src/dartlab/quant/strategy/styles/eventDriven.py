"""이벤트드리븐 (Event-Driven) — DART/SEC 공시 발표 후 PEAD drift.

[언제 강한가]
분기/사업/반기 보고서 발표 직후 +20일 PEAD (Post-Earnings Announcement Drift).
한국 시장에서 학술 검증된 효과 — Chaebol 관계사 거래 강화 (Park & Chai 2020).

[어떤 종목에 어울리나]
공시 사이클이 명확한 정기 보고 종목. 개인 투자자 비중 높은 KOSDAQ 중소형주
(역추종 거래 → drift 강화).

[진입 조건의 의미]
DART allFilings 에서 high-impact (정기보고서/공정공시) 발표 + 종가 > SMA5
(반응 시작 확인). T+0 ~ T+20 보유.

[청산 조건]
T+20일 경과 또는 SMA5 하회. ATR×3 stop.

[주의점]
- allFilings 데이터 로컬에 없으면 작동 불가 (KR 만 데이터 풍부, US 는 10-K)
- 컨센서스 surprise 데이터 없이 단순 발표 시점만 사용 → 정확도 제한
- 하루 여러 종목 동시 trigger 가능 → sizing 분산

[대표 사례]
- Ball & Brown (1968) 원조 PEAD 발견
- Bernard & Thomas (1989) "Post-Earnings-Announcement Drift"
- Park & Chai (2020) 한국 PEAD + Chaebol 관계사 효과
- Bartov, Radhakrishnan, Krinsky (2000) — 개인 투자자 PEAD

[관련 dartlab 축]
eventSignal.analyze_event_signal, allFilings parquet, indicators.vsma

[복제 + 수정 예시]
    rule = filing_flag & (close > sma5)
    Rule(rule, t_plus_20).with_stop("atr", k=3.0)
"""

from __future__ import annotations

from datetime import date as Date

import numpy as np

from dartlab.quant.eventSignal import analyze_event_signal
from dartlab.quant.indicators import vsma
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays, stock_code


def _date_to_filing_flag(dates: list, filing_date_strs: list[str], window: int = 20) -> np.ndarray:
    """OHLCV date 리스트에 high-impact filing 일자 매칭 → boolean flag.

    filing day 부터 window 일까지 True (PEAD drift 구간).
    """
    n = len(dates)
    flag = np.zeros(n, dtype=np.bool_)
    if not filing_date_strs:
        return flag
    # filing dates 를 set 으로 (YYYY-MM-DD)
    filing_set = set()
    for s in filing_date_strs:
        try:
            filing_set.add(s[:10])
        except (TypeError, IndexError):
            continue
    for i, d in enumerate(dates):
        d_str = d.strftime("%Y-%m-%d") if isinstance(d, Date) else str(d)[:10]
        if d_str in filing_set:
            for j in range(i, min(i + window, n)):
                flag[j] = True
    return flag


def build(company, *, hold_window: int = 20, atr_k: float = 3.0) -> Rule:
    """이벤트드리븐 룰 빌드. allFilings 없으면 빈 룰."""
    arr = get_arrays(company)
    close = arr.get("close")
    dates = arr.get("date")
    if close is None or dates is None or len(close) < 60:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "eventDriven", "error": "insufficient data"},
        )

    # eventSignal 시계열 추출
    code = stock_code(company)
    ev = analyze_event_signal(code, series=True)
    series = ev.get("_series") or {}
    high_impact_dates = series.get("high_impact_dates", [])

    filing_flag = _date_to_filing_flag(dates, high_impact_dates, window=hold_window)
    sma5 = vsma(close, 5)

    s = Signal()
    s.add("filing", filing_flag)
    s.add("above_sma5", (close > sma5) & ~np.isnan(sma5))
    s.add("not_filing", ~filing_flag)

    return Rule(
        entry_expr=s.filing & s.above_sma5,
        exit_expr=s.not_filing,
        meta={"style": "eventDriven", "n_filings": len(high_impact_dates)},
    ).with_stop("atr", k=atr_k, period=14)
