"""평균회귀 (Mean Reversion) — 단기 과매도 매수 / 과매수 매도 스타일.

[언제 강한가]
횡보장 + 변동성 정상 구간. 명확한 추세 없는 6~24개월 박스권 국면.
2014-2015 KOSPI, 2018 KOSPI, 2023 KOSDAQ 같은 횡보 환경에서 강함.

[어떤 종목에 어울리나]
유동성 풍부한 대형주 + 변동성 낮은 종목. 사이클 산업 (반등 명확).
실적 안정 + 과매도 후 회복 패턴 잦은 종목.

[진입 조건의 의미]
RSI(14) < 30 (과매도) + 종가 < 볼린저 하단 (이상 하락) + 변동성 정상 (vol < q60).
변동성 폭발 구간(vol > q60) 회피해서 추세 시작점에 진입하지 않음.

[청산 조건]
RSI > 50 (정상 회복). ATR×2 stop 으로 손실 제한.

[주의점]
- 추세 시작점에서 catch falling knife 위험. 변동성 필터 필수.
- 청산 임계 RSI 50 너무 빠르면 win 작아짐 → 60~70 으로 조정 가능.
- 금융위기/코로나 같은 fat tail 에서 큰 손실.

[대표 사례]
- Avellaneda & Lee (2008) "Statistical Arbitrage in the U.S. Equities Market"
- Lo & MacKinlay (1990) — 단기 평균회귀
- Khandani & Lo (2007) — 8월 2007 quant crisis 평균회귀

[관련 dartlab 축]
indicators.vrsi, indicators.vbollinger, volatility (garch_vol)

[복제 + 수정 예시]
    rule = (rsi < 30) & (close < bb_lower) & (vol < vol_q60)
    Rule(rule, rsi > 50).with_stop("atr", k=2.0)
"""

from __future__ import annotations

import numpy as np

from dartlab.quant.indicators import vbollinger, vrsi
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays
from dartlab.quant.volatility import _volatilitySeries


def build(company, *, rsi_low: float = 30, rsi_high: float = 50, atr_k: float = 2.0) -> Rule:
    """평균회귀 룰 빌드."""
    arr = get_arrays(company)
    close = arr.get("close")
    if close is None or len(close) < 60:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "meanReversion", "error": "insufficient data"},
        )

    rsi = vrsi(close, period=14)
    bb_up, bb_mid, bb_lo = vbollinger(close, period=20, std=2.0)
    vol_series = _volatilitySeries(close)
    realized = vol_series["realized_vol"]
    vol_q60 = float(np.nanquantile(realized, 0.60)) if not np.all(np.isnan(realized)) else float("inf")

    s = Signal()
    s.add("rsi_low", (rsi < rsi_low) & ~np.isnan(rsi))
    s.add("rsi_high", (rsi > rsi_high) & ~np.isnan(rsi))
    s.add("below_bb", (close < bb_lo) & ~np.isnan(bb_lo))
    s.add("vol_normal", (realized < vol_q60) & ~np.isnan(realized))

    return Rule(
        entry_expr=s.rsi_low & s.below_bb & s.vol_normal,
        exit_expr=s.rsi_high,
        meta={"style": "meanReversion"},
    ).with_stop("atr", k=atr_k, period=14)
