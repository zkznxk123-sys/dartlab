"""저변동방어 (Low Vol Defensive) — 변동성 낮고 낙폭 작은 종목 보유.

[언제 강한가]
약세장 + 횡보장. 변동성 폭발 회피 전략. AQR/MSCI 의 long-term low-vol anomaly
검증 (1968-2020 미국 시장에서 risk-adjusted return 최고 quintile).

[어떤 종목에 어울리나]
유틸리티/필수소비재/통신 같은 defensive 섹터. 사이클 종목 제외.
KOSPI 우량주 대형주 best.

[진입 조건의 의미]
20일 realized vol < 30 percentile (시장 평균보다 안정) + 252일 rolling MDD > -10%
(역사적 낙폭 작음). 두 조건 모두 만족 시 보유 시작.

[청산 조건]
vol > 70 percentile (변동성 폭발) 시 즉시 청산. stop 없음 (홀드 유지).

[주의점]
- 강세장에서 underperform (방어주는 상승률 낮음)
- 청산 임계 (q70) 자주 터지면 너무 빠른 청산 → q80 으로 조정 가능
- 252일 MDD 계산을 위해 최소 1년 데이터 필요

[대표 사례]
- Frazzini & Pedersen (2014) "Betting Against Beta"
- Asness, Frazzini, Pedersen (2019) "Quality Minus Junk"
- MSCI Minimum Volatility Index (1988-)

[관련 dartlab 축]
volatility.analyze_volatility (realized_vol), tailrisk.analyze_tailrisk (rolling_mdd)

[복제 + 수정 예시]
    rule = (vol < q30) & (mdd > -0.10)
    Rule(rule, vol > q70)
"""

from __future__ import annotations

import numpy as np

from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays
from dartlab.quant.tailrisk import _tailriskSeries
from dartlab.quant.volatility import _volatilitySeries


def build(company, *, vol_low_q: float = 0.30, vol_high_q: float = 0.70, mdd_threshold: float = -0.10) -> Rule:
    """저변동방어 룰 빌드."""
    arr = get_arrays(company)
    close = arr.get("close")
    if close is None or len(close) < 252:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "lowVolDefensive", "error": "insufficient data"},
        )

    vs = _volatilitySeries(close)
    realized = vs["realized_vol"]
    ts = _tailriskSeries(close)
    mdd_series = ts["rolling_mdd"]

    valid_vol = realized[~np.isnan(realized)]
    if len(valid_vol) < 20:
        n = len(close)
        return Rule(
            entry_expr=np.zeros(n, dtype=np.bool_),
            exit_expr=np.zeros(n, dtype=np.bool_),
            meta={"style": "lowVolDefensive", "error": "no vol data"},
        )

    q_low = float(np.quantile(valid_vol, vol_low_q))
    q_high = float(np.quantile(valid_vol, vol_high_q))

    s = Signal()
    s.add("vol_low", (realized < q_low) & ~np.isnan(realized))
    s.add("vol_high", (realized > q_high) & ~np.isnan(realized))
    s.add("mdd_ok", (mdd_series > mdd_threshold) & ~np.isnan(mdd_series))

    return Rule(
        entry_expr=s.vol_low & s.mdd_ok,
        exit_expr=s.vol_high,
        meta={"style": "lowVolDefensive"},
    )
