"""수급추종 (Flow Follow) — 외국인/기관 동시 순매수 (KR 전용, short-term).

[데이터 한계 — Phase 4 R4 명시]
gather/flow.py 는 naver finance 페이지네이션 한계로 **최근 5~30일 외국인/기관 데이터**
만 제공. 5년 walk-forward 백테스트 불가능. 본 스타일은 **단기 swing trade** (1주~1개월)
로만 작동 — 학술적으로도 외국인 수급은 단기 효과 (Choe-Kho-Stulz 2005).

EdgarCompany(US) 또는 데이터 부족 (< 30일) 시 NotApplicable / data_limited sentinel.

[언제 강한가]
외국인 보유비중 증가 + 기관 동조 매수 구간. 한국 시장 학술 검증된
"smart money 추종" 효과 (한국증권학회 2017+). EdgarCompany(US) 에서는
NotApplicable sentinel 반환 (KRX 전용 데이터).

[어떤 종목에 어울리나]
시총 중대형 + 외국인 보유 비중 25% 이상 종목. KOSPI 우량주가 best.
KOSDAQ 소형주는 외국인 비중 낮아 효과 약함.

[진입 조건의 의미]
외국인 5일 누적 순매수 > 0 + 기관 5일 누적 순매수 > 0. AND 조건으로 둘 다
양수일 때만 진입 → 의견 일치 확인.

[청산 조건]
외국인 5일 누적이 음수로 전환 (매도 우위). ATR×3 stop.

[주의점]
- KRX 일별 수급 데이터 필요 (gather/flow.py KR 전용)
- 외국인/기관 패턴이 며칠 지연 가능 (lag effect)
- 개별 헤지펀드 매매가 외국인으로 집계 → 노이즈
- US 종목 호출 시 NotApplicable sentinel (예외 X)

[대표 사례]
- 한국증권학회 (2017) — 투자주체별 정보력 실증
- Choe, Kho, Stulz (2005) — 외국인 거래와 한국 주식 수익률
- KRX 외국인 수급 통계

[관련 dartlab 축]
flowAnalysis.analyze_flow (KR only), gather/flow.py

[복제 + 수정 예시]
    rule = (foreign_cum5 > 0) & (inst_cum5 > 0)
    Rule(rule, foreign_cum5 < 0).with_stop("atr", k=3.0)
"""

from __future__ import annotations

from datetime import date as Date

import numpy as np

from dartlab.quant.flowAnalysis import analyze_flow
from dartlab.quant.strategy.rule import Rule
from dartlab.quant.strategy.signal import Signal
from dartlab.quant.strategy.styles._common import get_arrays, is_kr, stock_code


def build(company, *, atr_k: float = 3.0):
    """수급추종 룰 빌드. KR 전용 — US 면 NotApplicable sentinel.

    Returns:
        Rule (KR) 또는 BacktestResult.not_applicable (US)
    """
    # KR-only 방어
    if not is_kr(company):
        from dartlab.quant.strategy.backtest import BacktestResult

        return BacktestResult.not_applicable(
            style="flowFollow",
            reason="KR-only: foreign/institutional flow data not available for US",
        )

    arr = get_arrays(company)
    close = arr.get("close")
    dates = arr.get("date")
    if close is None or dates is None or len(close) < 60:
        n = len(close) if close is not None else 0
        return Rule(
            entry_expr=np.zeros(max(n, 1), dtype=np.bool_),
            exit_expr=np.zeros(max(n, 1), dtype=np.bool_),
            meta={"style": "flowFollow", "error": "insufficient data"},
        )

    code = stock_code(company)
    fl = analyze_flow(code, series=True)
    series = fl.get("_series") or {}
    flow_dates = series.get("date", [])
    fc5 = series.get("foreign_cum5")
    ic5 = series.get("inst_cum5")

    if fc5 is None or ic5 is None or not flow_dates or len(flow_dates) < 30:
        n = len(close)
        return Rule(
            entry_expr=np.zeros(n, dtype=np.bool_),
            exit_expr=np.zeros(n, dtype=np.bool_),
            meta={
                "style": "flowFollow",
                "error": "data_limited",
                "reason": (
                    f"flowFollow needs 30+ days flow history (Choe-Kho-Stulz 2005), "
                    f"found {len(flow_dates) if flow_dates else 0}. "
                    "naver finance 페이지네이션 한계."
                ),
                "flow_days_available": len(flow_dates) if flow_dates else 0,
            },
        )

    # OHLCV date 와 flow date 매칭 → 시계열 정렬
    n = len(close)
    foreign_aligned = np.full(n, np.nan, dtype=np.float64)
    inst_aligned = np.full(n, np.nan, dtype=np.float64)
    flow_idx_map = {}
    for i, d in enumerate(flow_dates):
        d_str = d.strftime("%Y-%m-%d") if isinstance(d, Date) else str(d)[:10]
        flow_idx_map[d_str] = i
    for i, d in enumerate(dates):
        d_str = d.strftime("%Y-%m-%d") if isinstance(d, Date) else str(d)[:10]
        if d_str in flow_idx_map:
            j = flow_idx_map[d_str]
            if j < len(fc5):
                foreign_aligned[i] = fc5[j]
            if j < len(ic5):
                inst_aligned[i] = ic5[j]

    s = Signal()
    s.add("foreign_up", (foreign_aligned > 0) & ~np.isnan(foreign_aligned))
    s.add("inst_up", (inst_aligned > 0) & ~np.isnan(inst_aligned))
    s.add("foreign_dn", (foreign_aligned < 0) & ~np.isnan(foreign_aligned))

    return Rule(
        entry_expr=s.foreign_up & s.inst_up,
        exit_expr=s.foreign_dn,
        meta={"style": "flowFollow"},
    ).with_stop("atr", k=atr_k, period=14)
