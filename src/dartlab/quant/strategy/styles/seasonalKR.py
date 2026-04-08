"""한국캘린더 (Seasonal KR) — TOM 효과 + 분기 보고서 캘린더 (KR 전용).

[언제 강한가]
월말 3거래일 ~ 월초 3거래일 = TOM (Turn-of-the-Month) 효과. 학술 검증 (Lakonishok-
Smidt 1988, KOSDAQ 강화 — 한국재무학회 2018+). 연금 자금 유입 + 월말 청산
+ 단기 추세 회복 패턴.

[어떤 종목에 어울리나]
KOSPI 우량주 또는 KOSDAQ 중대형주. 외국인 비중 높은 종목 (TOM 효과 강화).
KR 만 지원 — EdgarCompany(US) 호출 시 NotApplicable sentinel.

[진입 조건의 의미]
달의 day ≤ 3 또는 day ≥ 25 (월초 + 월말 3거래일). 단순 캘린더 boolean — 가격
신호 0개. 노이즈 작음.

[청산 조건]
day 4~24 (TOM 외 구간) → 청산. stop 없음.

[주의점]
- 매월 6거래일만 보유 → trade 빈도 매우 높음 (수수료 부담)
- KOSDAQ 효과가 KOSPI 보다 강함 (개인 비중)
- 명절/연말 등 특수 캘린더는 별도 처리 필요 (현재 미반영)

[대표 사례]
- Lakonishok & Smidt (1988) "Are Seasonal Anomalies Real?"
- 한국재무학회 (2018) KOSDAQ TOM 효과 실증
- Ariel (1987) 원조 monthly seasonality 발견

[관련 dartlab 축]
_helpers.tom_mask (KR 캘린더 SSOT)

[복제 + 수정 예시]
    rule = tom_mask(dates)
    Rule(rule, ~tom_mask(dates))
"""

from __future__ import annotations

import numpy as np

from dartlab.quant._helpers import tom_mask
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays, is_kr


def build(company):
    """한국캘린더 룰 빌드. KR 전용 — US 면 NotApplicable sentinel.

    Returns:
        Rule (KR) 또는 BacktestResult.not_applicable (US)
    """
    if not is_kr(company):
        from dartlab.quant.strategy.backtest import BacktestResult

        return BacktestResult.not_applicable(
            style="seasonalKR",
            reason="KR-only: Korean calendar TOM effect (KOSPI/KOSDAQ specific)",
        )

    arr = get_arrays(company)
    dates = arr.get("date")
    close = arr.get("close")
    if dates is None or close is None or len(dates) < 60:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "seasonalKR", "error": "insufficient data"},
        )

    tom = tom_mask(dates)

    s = Signal()
    s.add("tom", tom)
    s.add("not_tom", ~tom)

    return Rule(
        entry_expr=s.tom,
        exit_expr=s.not_tom,
        meta={"style": "seasonalKR"},
    )
