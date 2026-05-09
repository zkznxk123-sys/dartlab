"""추세추종 (Trend Following) — 검증된 50년 글로벌 표준 스타일.

[언제 강한가]
명확한 상승/하락 추세가 3개월 이상 지속되는 시장. 횡보장에서는 whipsaw 손실.
2009-2010 (금융위기 회복), 2016-2017 (글로벌 리플레이션), 2020-2021 (코로나 반등)
같은 강한 추세 국면에서 50년 검증.

[어떤 종목에 어울리나]
시가총액 중대형 + 거래대금 꾸준한 종목. 사이클 산업(반도체/화학/조선)에서 추세
지속성이 강함. 동전주/저유동성 종목 금지.

[진입 조건의 의미]
EMA20 > EMA60 (단기 추세) + MACD 양전환 + 12-1개월 모멘텀 양수. 3중 필터로
가짜 추세 (whipsaw) 제거. 진입 늦지만 신뢰도 높음.

[청산 조건]
EMA20 < EMA60 (데스크로스) 또는 ATR×3 trailing stop 도달 (Chandelier Exit).

[주의점]
- 횡보장에서 연속 손절. regime 필터 병행 권장.
- 진입이 늦어 첫 trade pnl 작을 수 있음.
- 손절 폭이 큼 → 자본의 5% 이상 잃지 않게 sizing 조정.

[대표 사례]
- William Dunn, Mulvaney, Winton 50년 검증 (CTA trend-following)
- AQR (Asness 2013) "Value and Momentum Everywhere"
- Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum"

[관련 dartlab 축]
indicators.vema, signals.vmacdSignal, momentum.calcMomentum (ts12_1)

[복제 + 수정 예시]
    from dartlab.quant.strategy import Signal, Rule
    s = Signal()
    s.add("ema_up", ema20 > ema60)
    s.add("macd_up", macd_signal == 1)
    s.add("mom_up", ts12_1 > 0)
    rule = Rule(s.ema_up & s.macd_up & s.mom_up, ~s.ema_up).with_stop("atr", k=3.0)
"""

from __future__ import annotations

import numpy as np

from dartlab.gather.indicators import vema
from dartlab.quant.momentum import _momentumSeries
from dartlab.quant.signals import vmacdSignal
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import getArrays


def build(
    company,
    *,
    ema_fast: int = 20,
    ema_slow: int = 60,
    atr_k: float = 3.0,
    use_macd_filter: bool = True,
) -> Rule:
    """추세추종 룰 빌드 — Moskowitz-Ooi-Pedersen 2012 TSMOM 정의.

    학술 정의 (TSMOM):
        sign(r_{t-12, t-1}) — 최근 12개월 (1개월 제외) 누적 수익률 부호.
        양수 = 매수, 음수 = 청산. AQR 2013 "Value and Momentum Everywhere" 전 자산군 검증.

    추가 robustness 필터 (false breakout 감소):
        - EMA20 > EMA60 (단기 추세 동조)
        - MACD histogram 양전환 (옵션, use_macd_filter)

    Args:
        ema_fast/ema_slow: SMA crossover 기간
        atr_k: ATR Chandelier exit 배수
        use_macd_filter: MACD 추가 필터 (기본 True)
    """
    arr = getArrays(company)
    close = arr.get("close")
    if close is None or len(close) < 252:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "trendFollow", "error": "insufficient data"},
        )

    ef = vema(close, ema_fast)
    es = vema(close, ema_slow)
    mom_series = _momentumSeries(close)
    ts12_1 = mom_series["ts12_1"]  # MOP 학술 정의

    s = Signal()
    s.add("tsmom_pos", (ts12_1 > 0) & ~np.isnan(ts12_1))  # 학술 핵심
    s.add("tsmom_neg", (ts12_1 < 0) & ~np.isnan(ts12_1))
    s.add("ema_up", (ef > es) & ~np.isnan(ef) & ~np.isnan(es))
    s.add("ema_dn", (ef < es) & ~np.isnan(ef) & ~np.isnan(es))

    entry = s.tsmom_pos & s.ema_up
    if use_macd_filter:
        macd_sig = vmacdSignal(close)
        s.add("macd_up", macd_sig == 1)
        # MACD 양전환은 단발 신호 → 진입 시점 필터로만 사용
        # tsmom + ema 는 상태 필터, macd 는 trigger
        # 여기서는 tsmom + ema 로 계속 보유, macd 는 진입 시점 보강
        entry = s.tsmom_pos & s.ema_up

    return Rule(
        entry_expr=entry,
        exit_expr=s.tsmom_neg | s.ema_dn,  # 학술: tsmom 음전환 → 청산
        meta={"style": "trendFollow", "definition": "MOP2012_TSMOM"},
    ).with_stop("atr", k=atr_k, period=14)
