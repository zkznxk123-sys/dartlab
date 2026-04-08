"""돌파 (Breakout) — 거래량 동반 채널 돌파 매수 / 채널 중간 청산.

[언제 강한가]
변동성 수축 → 폭발 전환 구간. 박스권 끝 돌파 시점. 강한 모멘텀 시작 직전.
2020 코로나 회복, 2017 비트코인 같은 추세 시작 국면.

[어떤 종목에 어울리나]
유동성 풍부한 대형주 (slippage 작음). Donchian 채널이 명확한 종목.
저변동성 → 고변동성 전환 패턴 잦은 종목.

[진입 조건의 의미]
종가 > Donchian 20일 상단 (채널 돌파) + OBV 5일 양전환 (거래량 확인).
거래량 확인 없이 가격만 보면 fake breakout 빈번 → 2중 필터 필수.

[청산 조건]
종가 < Donchian 중간 (모멘텀 약화). ATR×2.5 trailing stop.

[주의점]
- 갭 상승 시 진입가가 너무 멀어짐 → slippage 5bp 이상 고려.
- 박스권 좁을수록 신호 자주 → 과적합 위험. 채널 기간 20일 이상 권장.
- 첫 돌파에서만 진입, 재돌파는 신호로 보지 마라.

[대표 사례]
- Richard Donchian (Donchian Channel 창시, 1960s)
- Curtis Faith "Way of the Turtle" (Turtle Trading, 1980s)
- Larry Williams 변동성 돌파 시스템

[관련 dartlab 축]
indicators.vdonchian, indicators.vobv, signals.vbreakoutSignal

[복제 + 수정 예시]
    rule = (close > donch_high) & (obv_up)
    Rule(rule, close < donch_mid).with_stop("atr", k=2.5)
"""

from __future__ import annotations

import numpy as np

from dartlab.quant.indicators import vdonchian, vobv
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays


def build(company, *, donch_period: int = 20, atr_k: float = 2.5) -> Rule:
    """돌파 룰 빌드."""
    arr = get_arrays(company)
    close = arr.get("close")
    high = arr.get("high")
    low = arr.get("low")
    volume = arr.get("volume")
    if close is None or high is None or low is None or volume is None or len(close) < 60:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "breakout", "error": "insufficient data"},
        )

    upper, middle, lower = vdonchian(high, low, period=donch_period)
    obv = vobv(close, volume)
    obv_5d = np.diff(obv, prepend=obv[0])
    obv_5d_ma = np.convolve(obv_5d, np.ones(5) / 5, mode="same")

    s = Signal()
    s.add("above_high", (close > upper) & ~np.isnan(upper))
    s.add("below_mid", (close < middle) & ~np.isnan(middle))
    s.add("obv_up", obv_5d_ma > 0)

    return Rule(
        entry_expr=s.above_high & s.obv_up,
        exit_expr=s.below_mid,
        meta={"style": "breakout"},
    ).with_stop("atr", k=atr_k, period=14)
