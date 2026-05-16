"""경제 사이클 판별 + 자산 해석 + 멀티플 밴드 + 전환 시퀀스 + 금리 분해.

순수 데이터 + 판정 함수. 외부 의존성 없음.
core/ 계층 소속 — gather(수집), macro(시장 해석), analysis(기업 해석) 에서 사용.

사이클 4국면: contraction(침체) → recovery(회복) → expansion(확장) → slowdown(둔화)
"""

from __future__ import annotations

import math

from dartlab.macro.cycles._macroCycleAssets import (
    classifyVixRegime,
    copperGoldRatio,
    interpretFxDrivers,
    interpretGoldDrivers,
    marketLevelValuation,
    realRateRegime,
)

# 결과 타입 (분리: _macroCycleTypes.py SSOT, re-export 으로 BC 보존)
from dartlab.macro.cycles._macroCycleHelpers import (
    _SIGNAL_SERIES_MAP,
    _findFirstTriggerDates,
    _normCdf,
)
from dartlab.macro.cycles._macroCycleTypes import (
    PHASE_LABELS,
    AssetSignal,
    CopperGoldSignal,
    CyclePhase,
    FxDrivers,
    GoldDrivers,
    MarketValuation,
    MultipleBand,
    RateDecomposition,
    RealRateRegimeResult,
    TransitionSignal,
    VixRegime,
)

__all_helpers__ = [
    "_SIGNAL_SERIES_MAP",
    "_findFirstTriggerDates",
    "_normCdf",
    "classifyVixRegime",
    "copperGoldRatio",
    "interpretFxDrivers",
    "interpretGoldDrivers",
    "marketLevelValuation",
    "realRateRegime",
]

# ══════════════════════════════════════
# 사이클 판별
# ══════════════════════════════════════

# 사이클별 섹터 전략 (SectorElasticity.cyclicality 기반)
# 실험 109-02 결과: 회복기/둔화기에서 실효성 확인
CYCLE_SECTOR_MAP: dict[str, dict[str, str]] = {
    "contraction": {
        "defensive": "neutral",  # 침체기엔 전부 하락, 차이 미미
        "moderate": "neutral",
        "high": "underweight",
        "low": "neutral",
    },
    "recovery": {
        "high": "overweight",  # +51%p 초과수익 (실험 검증)
        "moderate": "overweight",
        "defensive": "neutral",
        "low": "neutral",
    },
    "expansion": {
        "high": "overweight",
        "moderate": "overweight",
        "defensive": "neutral",
        "low": "neutral",
    },
    "slowdown": {
        "defensive": "overweight",  # -7.4%p 방어 (실험 검증)
        "moderate": "neutral",
        "high": "underweight",
        "low": "neutral",
    },
}


def classifyCycle(indicators: dict[str, float | None]) -> CyclePhase:
    """매크로 8 지표 → 경제 사이클 4국면 판별 (가중 투표).

    Capabilities:
        HY 스프레드 + Term 스프레드 + VIX + 금 YoY + CLI 모멘텀 + CPI/BEI 등
        8 지표를 가중치로 합산하여 4 국면 (contraction/recovery/expansion/
        slowdown) 중 하나를 선택. macro/summary 의 cycle 축이 직접 호출.

    Args:
        indicators: 매크로 지표 dict. 지원 키:
            - ``hy_spread``: HY 스프레드 (bp)
            - ``term_spread``: 10Y-2Y 스프레드 (%)
            - ``vix``: CBOE VIX
            - ``gold_yoy``: 금 YoY (%)
            - ``cli_mom``: 경기선행지수 전월비
            - ``hy_spread_3m_change``: HY 3M 변화 (bp)
            - ``cpi_yoy``: CPI YoY (%)
            - ``bei_10y``: 10Y BEI (%)
            모든 키 옵션. None 값은 해당 지표 무시.

    Returns:
        CyclePhase dataclass:
            - ``phase`` (str): ``"contraction"``/``"recovery"``/``"expansion"``/``"slowdown"``
            - ``phaseLabel`` (str): 한국어
            - ``confidence`` (str): ``"high"``/``"medium"``/``"low"`` (top - 2nd 차이)
            - ``signals`` (list[str]): 판정 근거 라인 리스트
            - ``scores`` (dict[str, int]): 4 국면 누적 점수

    Raises:
        없음.

    Example:
        >>> r = classifyCycle({"hy_spread": 450, "term_spread": -0.3, "vix": 28})
        >>> r.phase
        'slowdown'

    Guide:
        4 국면 정의: contraction (침체, HY 급등+VIX>30), recovery (회복, HY
        하락+CLI 반등), expansion (확장, HY 안정+CLI 양수), slowdown (둔화,
        Term spread 역전+CPI 가속). 점수 모두 0 이면 ``"expansion"`` 기본값.

    SeeAlso:
        - ``interpretAssets``: 사이클 → 자산 추천
        - ``CYCLE_SECTOR_MAP``: 사이클별 섹터 전략

    Requires:
        없음 (순수 함수).

    AIContext:
        confidence="low" 결과는 전환기 가능성 — 동일 indicators 1~2 분기 후
        재호출 권장. signals 리스트는 라벨 인용 시 함께 노출하여 근거 투명화.

    LLM Specifications:
        AntiPatterns:
            - 단일 지표만으로 phase 추론 금지. 본 함수는 8 지표 가중 합산.
            - signals 리스트가 비어 있을 때 phase 신뢰 금지 — 입력 부족 신호.
        OutputSchema:
            CyclePhase ``{phase, phaseLabel, confidence, signals, scores}``.
        Prerequisites:
            최소 1 개 지표 값 (None 아님). 모두 None 이면 기본 expansion.
        Freshness:
            지표별 갱신 주기 (HY/VIX 일, CLI 월, CPI/BEI 월).
        Dataflow:
            지표별 룰 → scores dict 누적 → max → phase + confidence 계산
            (top - 2nd 차이로).
        TargetMarkets: US (FRED), KR (BOK ECOS).
    """
    signals: list[str] = []
    scores = {"contraction": 0, "recovery": 0, "expansion": 0, "slowdown": 0}

    hy = indicators.get("hy_spread")
    hy_chg = indicators.get("hy_spread_3m_change")
    ts = indicators.get("term_spread")
    vix = indicators.get("vix")
    goldYoy = indicators.get("gold_yoy")
    cli_mom = indicators.get("cli_mom")
    cpiYoy = indicators.get("cpi_yoy")
    bei10y = indicators.get("bei_10y")

    # 1. 하이일드 스프레드 — 레벨 + 변화 속도
    if hy is not None:
        if hy > 500:
            scores["contraction"] += 3
            signals.append(f"HY 스프레드 급등 ({hy:.0f}bp)")
        elif hy > 400:
            scores["contraction"] += 1
            scores["slowdown"] += 2
            signals.append(f"HY 스프레드 경고 ({hy:.0f}bp)")
        elif hy < 350:
            scores["expansion"] += 1
            scores["recovery"] += 1
            signals.append(f"HY 스프레드 안정 ({hy:.0f}bp)")

    # HY 변화 속도 — 회복 전환 핵심 신호 (실험 01 피드백)
    if hy_chg is not None:
        if hy_chg < -50:
            scores["recovery"] += 2
            signals.append(f"HY 스프레드 급감 (3M {hy_chg:+.0f}bp)")
        elif hy_chg > 100:
            scores["contraction"] += 2
            signals.append(f"HY 스프레드 급등 (3M {hy_chg:+.0f}bp)")

    # 2. 장단기 스프레드
    if ts is not None:
        if ts < 0:
            scores["contraction"] += 2
            scores["slowdown"] += 1
            signals.append(f"수익률곡선 역전 ({ts:+.2f}%)")
        elif ts < 0.5:
            scores["slowdown"] += 2
            signals.append(f"수익률곡선 평탄화 ({ts:+.2f}%)")
        elif ts > 1.5:
            scores["recovery"] += 2
            signals.append(f"수익률곡선 가파름 ({ts:+.2f}%)")
        else:
            scores["expansion"] += 1
            signals.append(f"수익률곡선 정상 ({ts:+.2f}%)")

    # 3. VIX
    if vix is not None:
        if vix > 30:
            scores["contraction"] += 2
            signals.append(f"VIX 급등 ({vix:.1f})")
        elif vix > 20:
            scores["slowdown"] += 1
            signals.append(f"VIX 상승 ({vix:.1f})")
        elif vix < 15:
            scores["expansion"] += 2
            signals.append(f"VIX 안정 ({vix:.1f})")
        else:
            scores["recovery"] += 1
            scores["expansion"] += 1

    # 4. 금 YoY
    if goldYoy is not None:
        if goldYoy > 15:
            scores["contraction"] += 1
            scores["slowdown"] += 1
            signals.append(f"금 급등 (YoY {goldYoy:+.1f}%)")
        elif goldYoy < -5:
            scores["recovery"] += 1
            scores["expansion"] += 1
            signals.append(f"금 하락 (YoY {goldYoy:+.1f}%)")

    # 5. CLI 모멘텀 — 반전 강화 (실험 01 피드백)
    if cli_mom is not None:
        if cli_mom < -0.5:
            scores["contraction"] += 2
            signals.append(f"CLI 급락 ({cli_mom:+.2f})")
        elif cli_mom < -0.1:
            scores["slowdown"] += 2
            signals.append(f"CLI 하락 ({cli_mom:+.2f})")
        elif cli_mom > 0.5:
            scores["recovery"] += 2
            signals.append(f"CLI 급등 ({cli_mom:+.2f})")
        elif cli_mom > 0.1:
            scores["expansion"] += 1
            scores["recovery"] += 1
            signals.append(f"CLI 상승 ({cli_mom:+.2f})")

    # 6. 인플레이션 — 사이클 3대 힘 중 하나 (통화/재정/물가)
    if cpiYoy is not None:
        if cpiYoy > 4.0:
            scores["slowdown"] += 2
            signals.append(f"CPI {cpiYoy:.1f}% — 물가 과열, 둔화 전조")
        elif cpiYoy > 3.0:
            scores["expansion"] += 1
            signals.append(f"CPI {cpiYoy:.1f}% — 인플레 동반 확장")
        elif cpiYoy < 1.5:
            scores["contraction"] += 1
            signals.append(f"CPI {cpiYoy:.1f}% — 디플레 우려")

    if bei10y is not None:
        if bei10y > 2.8:
            scores["slowdown"] += 1
            signals.append(f"BEI {bei10y:.2f}% — 기대인플레 상승, 긴축 압력")
        elif bei10y < 1.8:
            scores["contraction"] += 1
            scores["recovery"] += 1
            signals.append(f"BEI {bei10y:.2f}% — 기대인플레 하락")

    # 최고 점수 국면 선택
    phase = max(scores, key=lambda k: scores[k])
    max_score = scores[phase]
    total = sum(scores.values())

    if total == 0:
        return CyclePhase(
            "expansion",
            "확장",
            "low",
            ("신호 데이터 부족",),
            CYCLE_SECTOR_MAP["expansion"],
        )

    ratio = max_score / total if total > 0 else 0
    if ratio > 0.5:
        confidence = "high"
    elif ratio > 0.35:
        confidence = "medium"
    else:
        confidence = "low"

    return CyclePhase(
        phase=phase,
        label=PHASE_LABELS[phase],
        confidence=confidence,
        signals=tuple(signals),
        sectorStrategy=CYCLE_SECTOR_MAP[phase],
    )


# ══════════════════════════════════════
# 5대 자산 해석
# ══════════════════════════════════════


def interpretAssets(indicators: dict[str, float | None]) -> list[AssetSignal]:
    """5 대 자산 (단기금리/장기금리/환율/금/VIX) 현재 상태 해석.

    Capabilities:
        매크로 지표 dict 를 받아 5 자산의 (현 수준 + 변화) 를 해석한 list
        반환. 단기/장기금리는 정책/inflation 근거 분리. 환율은 한미 금리차
        교차 해석. 금은 YoY 모멘텀. VIX 는 변화량.

    Args:
        indicators: 매크로 지표 dict. 지원 키 (모두 옵션):
            - ``short_rate``/``short_rate_change`` (%, %p)
            - ``long_rate``/``long_rate_change`` (%, %p)
            - ``bei_change``/``real_rate_change`` (%p) — 장기금리 "왜" 분해
            - ``fx_usdkrw``/``fx_change_pct`` (원, %)
            - ``rate_diff``/``rate_diff_change`` (%p) — 한미 금리차
            - ``gold``/``gold_yoy`` ($/oz, %)
            - ``vix``/``vix_change`` (index, pts)

    Returns:
        list[AssetSignal]: 자산별 dataclass:
            - ``asset`` (str): 자산명
            - ``level`` (float|None)
            - ``interpretation`` (str): 한국어 해석
            - ``implication`` (str): 함의 라벨 (긴축기대/완화기대/안전선호 등)

    Raises:
        없음.

    Example:
        >>> r = interpretAssets({"short_rate": 3.5, "short_rate_change": 0.5,
        ...                      "vix": 28, "vix_change": 8})
        >>> [s.implication for s in r]
        ['긴축기대', ..., '안전선호']

    Guide:
        장기금리 변화를 BEI/real rate 분해로 인플레 vs 성장 기대 구분.
        환율 변화는 한미 금리차 변화와 교차 — 금리차 확대 + 환율 상승 =
        달러 강세, 금리차 축소 + 환율 하락 = 원화 강세.

    SeeAlso:
        - ``classifyCycle``: 사이클 4 국면 (자산 신호 종합)
        - ``interpretGoldDrivers``: 금 3 요인 분해
        - ``interpretFxDrivers``: 환율 드라이버 분해

    Requires:
        없음 (순수 함수). indicators dict 일부 키만 있어도 동작.

    AIContext:
        해석 라벨 (interpretation) 을 그대로 인용 — 사용자에게 매크로 환경
        의 직접 텍스트 노출 가능. implication 만으로는 정량 정보 부족.

    LLM Specifications:
        AntiPatterns:
            - 단기금리만 보고 "긴축" 단정 — 장기금리 + 환율 함께 확인.
            - VIX 절대값 (예 18) 만 인용 — vix_change 도 함께 (급등 시 panic).
        OutputSchema:
            list[AssetSignal] — 자산 개수만큼 (입력 indicators 에 따름).
        Prerequisites:
            indicators dict (적어도 1 자산의 level + change).
        Freshness:
            지표별 (금리/환율 일, VIX 일, 금 일).
        Dataflow:
            indicators → 자산별 분기 룰 → AssetSignal dataclass list.
        TargetMarkets: KR (USDKRW + 한미 금리차), Global (long_rate/gold/VIX).
    """
    results: list[AssetSignal] = []

    # 1. 단기금리 (2년물 / 기준금리)
    sr = indicators.get("short_rate")
    sr_chg = indicators.get("short_rate_change")
    if sr is not None:
        if sr_chg is not None and sr_chg > 0.25:
            interp = f"단기금리 상승 ({sr:.2f}%, {sr_chg:+.2f}%p) — 긴축 기대"
            impl = "긴축기대"
        elif sr_chg is not None and sr_chg < -0.25:
            interp = f"단기금리 하락 ({sr:.2f}%, {sr_chg:+.2f}%p) — 완화 기대"
            impl = "완화기대"
        else:
            interp = f"단기금리 안정 ({sr:.2f}%)"
            impl = "중립"
        results.append(AssetSignal("shortRate", "단기금리", sr, sr_chg, interp, impl))

    # 2. 장기금리 (10년물) — DKW 분해로 "왜" 해석
    lr = indicators.get("long_rate")
    lr_chg = indicators.get("long_rate_change")
    bei_chg = indicators.get("bei_change")
    rr_chg = indicators.get("real_rate_change")
    if lr is not None:
        if lr_chg is not None and abs(lr_chg) > 0.3:
            # DKW 분해: BEI 변화 vs 실질금리 변화로 주도 요인 판별
            driver = ""
            if bei_chg is not None and rr_chg is not None:
                if abs(bei_chg) > abs(rr_chg):
                    driver = f" (BEI {bei_chg:+.2f}%p 주도 → 인플레 기대 변화)"
                else:
                    driver = f" (실질금리 {rr_chg:+.2f}%p 주도 → 성장 기대 변화)"
            if lr_chg > 0.3:
                impl = "인플레기대↑" if (bei_chg and bei_chg > rr_chg if rr_chg else True) else "성장기대↑"
                interp = f"장기금리 상승 ({lr:.2f}%, {lr_chg:+.2f}%p){driver}"
            else:
                impl = "인플레기대↓" if (bei_chg and bei_chg < rr_chg if rr_chg else True) else "경기둔화"
                interp = f"장기금리 하락 ({lr:.2f}%, {lr_chg:+.2f}%p){driver}"
        else:
            interp = f"장기금리 안정 ({lr:.2f}%)"
            impl = "중립"
        results.append(AssetSignal("longRate", "장기금리", lr, lr_chg, interp, impl))

    # 3. 환율 (원/달러) — 금리차 교차 해석
    fx = indicators.get("fx_usdkrw")
    fx_chg = indicators.get("fx_change_pct")
    indicators.get("rate_diff")  # US금리 - KR금리
    rate_diff_chg = indicators.get("rate_diff_change")
    if fx is not None:
        # 기본 방향 해석
        if fx_chg is not None and fx_chg > 3:
            base = f"원화 약세 ({fx:,.0f}원, {fx_chg:+.1f}%)"
            impl = "위험회피"
        elif fx_chg is not None and fx_chg < -3:
            base = f"원화 강세 ({fx:,.0f}원, {fx_chg:+.1f}%)"
            impl = "위험선호"
        else:
            base = f"환율 안정 ({fx:,.0f}원)"
            impl = "중립"

        # 금리차 교차 해석: 금리차 확대→자본유출→원화약세, 축소→유입→강세
        rate_context = ""
        if rate_diff_chg is not None:
            if rate_diff_chg > 0.2:
                rate_context = f" — 한미 금리차 확대({rate_diff_chg:+.2f}%p), 자본유출 압력"
            elif rate_diff_chg < -0.2:
                rate_context = f" — 한미 금리차 축소({rate_diff_chg:+.2f}%p), 자본유입 기대"

        interp = base + rate_context
        results.append(AssetSignal("fx", "환율", fx, fx_chg, interp, impl))

    # 4. 금
    gold = indicators.get("gold")
    goldYoy = indicators.get("gold_yoy")
    if gold is not None:
        if goldYoy is not None and goldYoy > 15:
            interp = f"금 급등 (${gold:,.0f}, YoY {goldYoy:+.1f}%) — 인플레·불안심리"
            impl = "위험회피"
        elif goldYoy is not None and goldYoy < -5:
            interp = f"금 하락 (${gold:,.0f}, YoY {goldYoy:+.1f}%) — 위험자산 선호"
            impl = "위험선호"
        else:
            interp = f"금 안정 (${gold:,.0f})"
            impl = "중립"
        results.append(AssetSignal("gold", "금", gold, goldYoy, interp, impl))

    # 5. VIX
    vix = indicators.get("vix")
    vix_chg = indicators.get("vix_change")
    if vix is not None:
        if vix > 30:
            interp = f"VIX 급등 ({vix:.1f}) — 극단적 공포"
            impl = "공포"
        elif vix > 20:
            interp = f"VIX 상승 ({vix:.1f}) — 불확실성 확대"
            impl = "불확실성"
        elif vix < 15:
            interp = f"VIX 안정 ({vix:.1f}) — 시장 낙관"
            impl = "낙관"
        else:
            interp = f"VIX 보통 ({vix:.1f})"
            impl = "중립"
        results.append(AssetSignal("vix", "VIX", vix, vix_chg, interp, impl))

    return results


# ══════════════════════════════════════
# 멀티플 밴드
# ══════════════════════════════════════


def calcMultipleBand(
    values: list[float],
    current: float,
    metric: str = "PER",
) -> MultipleBand | None:
    """과거 멀티플 시계열에서 정규분포 밴드 계산.

    Args:
        values: 과거 멀티플 값 리스트 (최소 5개)
        current: 현재 멀티플
        metric: "PER" | "PBR" | "EV/EBITDA" 등

    Returns:
        MultipleBand 또는 데이터 부족 시 None
    """
    # 유효값 필터 (0 이하, 극단값 제거)
    valid = [v for v in values if v is not None and 0 < v < 200]
    if len(valid) < 5:
        return None

    mean = sum(valid) / len(valid)
    variance = sum((v - mean) ** 2 for v in valid) / len(valid)
    std = math.sqrt(variance) if variance > 0 else 0.01

    if std == 0:
        return None

    # z-score
    z = (current - mean) / std

    # 정규분포 CDF 근사 (Abramowitz & Stegun)
    percentile = _normCdf(z) * 100

    # zone 판정 (+-1 표준편차)
    if z < -1:
        zone, zLabel = "cheap", "저평가"
    elif z > 1:
        zone, zLabel = "expensive", "고평가"
    else:
        zone, zLabel = "fair", "적정"

    return MultipleBand(
        metric=metric,
        current=current,
        mean=round(mean, 2),
        std=round(std, 2),
        percentile=round(percentile, 1),
        zone=zone,
        zLabel=zLabel,
    )


# ══════════════════════════════════════
# 금리 전망
# ══════════════════════════════════════


def rateOutlook(indicators: dict[str, float | None]) -> dict:
    """금리·물가·고용 → Fed/BOK 정책 금리 방향 전망 (인상/동결/인하).

    Capabilities:
        Taylor rule 단순화 — CPI/Core CPI + 실업률 + payrolls 변화로 인플레
        압력과 고용 강도를 합산하여 정책금리 방향 (hike/hold/cut) 과 신뢰도
        산출. macro/summary 의 rates 축이 직접 호출.

    Args:
        indicators: 매크로 dict. 지원 키:
            - ``fed_funds`` 또는 ``base_rate`` (%): 현 정책금리
            - ``cpi_yoy`` (%): CPI YoY
            - ``core_cpi_yoy`` (%): Core CPI YoY
            - ``unemployment`` (%): 실업률
            - ``payrolls_change`` (천명): 비농업고용 변화

    Returns:
        dict:
            - ``direction`` (str): ``"hike"``/``"hold"``/``"cut"``
            - ``directionLabel`` (str): 한국어
            - ``confidence`` (str): high/medium/low
            - ``reasoning`` (list[str]): 판정 근거 라인
            - ``bias`` (int): 양수=인상 / 음수=인하

    Raises:
        없음.

    Example:
        >>> r = rateOutlook({"fed_funds": 5.5, "cpi_yoy": 3.2,
        ...                  "unemployment": 3.7, "payrolls_change": 200})
        >>> r["direction"]
        'hold'

    Guide:
        Taylor rule: r* = neutral + 1.5(π - 2) + 0.5(u_natural - u). 본 함수는
        간소화 — 인상 bias 누적 (CPI>3, payrolls 강세 등) - 인하 bias (CPI<2,
        unemp 상승). bias > +2 = hike, < -2 = cut, 그 외 hold.

    SeeAlso:
        - ``classifyCycle``: 사이클 4 국면 (rateOutlook 와 함께 종합)
        - ``decomposeLongRate``: 장기금리 BEI/real rate 분해

    Requires:
        없음 (순수 함수). indicators 일부 키만 있어도 동작.

    AIContext:
        direction + reasoning 함께 인용. confidence=low 시 다음 분기 재호출
        권장 (전환기). bias 절댓값 작으면 (|bias|<2) hold 가 default.

    LLM Specifications:
        AntiPatterns:
            - 단일 지표 (CPI 만) 로 direction 판정 — Taylor rule 은 인플레 +
              고용 동시 고려.
            - 한국 base_rate 호출에 미국 fed_funds 표준 적용 — KR/US 별
              neutral rate 다름 (한국 ~2.5%, 미국 ~3%).
        OutputSchema:
            ``{direction, directionLabel, confidence, reasoning, bias}``.
        Prerequisites:
            indicators 에 (fed_funds 또는 base_rate) + cpi_yoy 권장.
        Freshness:
            CPI 월간 (10 일 발표), 고용 월간 (첫 금요일).
        Dataflow:
            indicators → CPI bias + 고용 bias + 실업 bias 누적 → 합산 →
            direction 분류 + confidence.
        TargetMarkets: US (Fed funds + CPI + payrolls), KR (BOK base + KOSIS).
    """
    ff = indicators.get("fed_funds") or indicators.get("base_rate")
    cpi = indicators.get("cpi_yoy")
    core_cpi = indicators.get("core_cpi_yoy")
    unemp = indicators.get("unemployment")
    payrolls = indicators.get("payrolls_change")

    reasoning: list[str] = []
    bias = 0  # 양수 = 인상 방향, 음수 = 인하 방향

    if cpi is not None:
        if cpi > 3.0:
            bias += 2
            reasoning.append(f"CPI {cpi:.1f}% > 3% — 인상 압력")
        elif cpi < 2.0:
            bias -= 1
            reasoning.append(f"CPI {cpi:.1f}% < 2% — 인하 여지")
        else:
            reasoning.append(f"CPI {cpi:.1f}% — 목표 부근")

    if core_cpi is not None:
        if core_cpi > 3.0:
            bias += 1
            reasoning.append(f"Core CPI {core_cpi:.1f}% — 기조적 인플레")

    if unemp is not None:
        if unemp > 5.0:
            bias -= 2
            reasoning.append(f"실업률 {unemp:.1f}% > 5% — 고용 약화, 인하 압력")
        elif unemp < 4.0:
            bias += 1
            reasoning.append(f"실업률 {unemp:.1f}% < 4% — 고용 강함")

    if payrolls is not None:
        if payrolls < 100:
            bias -= 1
            reasoning.append(f"비농업고용 +{payrolls:.0f}K — 둔화")
        elif payrolls > 250:
            bias += 1
            reasoning.append(f"비농업고용 +{payrolls:.0f}K — 강함")

    if bias >= 2:
        direction = "hike"
        dLabel = "인상 가능"
    elif bias <= -2:
        direction = "cut"
        dLabel = "인하 가능"
    else:
        direction = "hold"
        dLabel = "동결 유지"

    confidence = "high" if abs(bias) >= 3 else "medium" if abs(bias) >= 2 else "low"

    return {
        "currentRate": ff,
        "direction": direction,
        "directionLabel": dLabel,
        "confidence": confidence,
        "reasoning": reasoning,
        "biasScore": bias,
    }


# ══════════════════════════════════════
# 전환 시퀀스 감지
# ══════════════════════════════════════

# 각 전환에 대한 자산 신호 시퀀스 (발현 순서대로)
_TRANSITION_SEQUENCES: dict[tuple[str, str], tuple[str, ...]] = {
    # 침체→회복: HY스프레드 축소 → 금 하락 → 장기금리 상승
    ("contraction", "recovery"): (
        "hy_spread_declining",
        "gold_declining",
        "long_rate_rising",
    ),
    # 회복→확장: VIX 안정 → 수익률곡선 정상화 → BEI 상승(인플레 동반) → HY 안정
    ("recovery", "expansion"): (
        "vix_stable",
        "term_spread_normalizing",
        "bei_rising",
        "hy_spread_stable",
    ),
    # 확장→둔화: HY스프레드 확대 → BEI 급등(물가 과열) → 수익률곡선 평탄화 → VIX 상승
    ("expansion", "slowdown"): (
        "hy_spread_widening",
        "bei_overheating",
        "term_spread_flattening",
        "vix_rising",
    ),
    # 둔화→침체: VIX 급등 → 수익률곡선 역전 → 금 급등
    ("slowdown", "contraction"): (
        "vix_spiking",
        "term_spread_inverted",
        "gold_surging",
    ),
}


def detectTransitionSequence(
    currentPhase: str,
    indicators: dict[str, float | None],
    history: dict[str, list[tuple[str, float]]] | None = None,
) -> TransitionSignal | None:
    """현재 국면에서 다음 국면으로의 전환 시퀀스를 감지.

    Args:
        currentPhase: 현재 사이클 국면
        indicators: 매크로 지표 dict (classifyCycle과 동일 키 + 추가)
            - hy_spread_3m_change: HY 스프레드 3개월 변화 (bp)
            - gold_yoy: 금 가격 YoY (%)
            - long_rate_change: 장기금리 3개월 변화 (%p)
            - vix: VIX 수준
            - term_spread: 장단기 스프레드 (%)
        history: 시계열 이력 — {시리즈명: [(날짜str, 값), ...]} 형태.
            시퀀스 순서 검증에 사용. None이면 순서 검증 생략.
            예: {"hy_spread": [("2025-01", 450), ("2025-02", 420), ...],
                 "gold_yoy": [("2025-01", 5.2), ...]}

    Returns:
        TransitionSignal 또는 전환 징후 없으면 None
    """
    phases = ["contraction", "recovery", "expansion", "slowdown"]
    if currentPhase not in phases:
        return None

    idx = phases.index(currentPhase)
    nextPhase = phases[(idx + 1) % len(phases)]
    key = (currentPhase, nextPhase)
    sequence = _TRANSITION_SEQUENCES.get(key)
    if sequence is None:
        return None

    # 각 신호의 발현 여부 판정
    triggered: list[str] = []
    pending: list[str] = []

    hy_chg = indicators.get("hy_spread_3m_change")
    goldYoy = indicators.get("gold_yoy")
    lr_chg = indicators.get("long_rate_change")
    vix = indicators.get("vix")
    ts = indicators.get("term_spread")
    bei = indicators.get("bei_10y")

    signalChecks: dict[str, bool] = {
        "hy_spread_declining": hy_chg is not None and hy_chg < -30,
        "hy_spread_widening": hy_chg is not None and hy_chg > 50,
        "hy_spread_stable": hy_chg is not None and abs(hy_chg) < 30,
        "gold_declining": goldYoy is not None and goldYoy < -3,
        "gold_surging": goldYoy is not None and goldYoy > 15,
        "long_rate_rising": lr_chg is not None and lr_chg > 0.2,
        "vix_stable": vix is not None and vix < 18,
        "vix_rising": vix is not None and vix > 22,
        "vix_spiking": vix is not None and vix > 30,
        "term_spread_normalizing": ts is not None and ts > 0.5,
        "term_spread_flattening": ts is not None and 0 < ts < 0.5,
        "term_spread_inverted": ts is not None and ts < 0,
        # 인플레이션 전환 신호
        "bei_rising": bei is not None and bei > 2.3,  # 회복→확장: 인플레 동반
        "bei_overheating": bei is not None and bei > 2.8,  # 확장→둔화: 물가 과열
    }

    for signal_name in sequence:
        if signalChecks.get(signal_name, False):
            triggered.append(signal_name)
        else:
            pending.append(signal_name)

    if not triggered:
        return None

    progress = round(len(triggered) / len(sequence) * 100)

    # 시계열 이력이 있으면 각 신호의 최초 발현 시점 추적 + 순서 검증
    sequence_order: list[tuple[str, str | None]] = []
    order_valid: bool | None = None

    if history and len(triggered) >= 2:
        first_dates = _findFirstTriggerDates(sequence, signalChecks, history)
        sequence_order = [(sig, first_dates.get(sig)) for sig in triggered]
        # 발현 시점이 있는 신호들만 순서 검증
        dated = [(sig, d) for sig, d in sequence_order if d is not None]
        if len(dated) >= 2:
            order_valid = all(dated[i][1] <= dated[i + 1][1] for i in range(len(dated) - 1))

    return TransitionSignal(
        fromPhase=currentPhase,
        toPhase=nextPhase,
        progress=progress,
        triggered=tuple(triggered),
        pending=tuple(pending),
        sequenceOrder=tuple(sequence_order),
        orderValid=order_valid,
    )


# ══════════════════════════════════════
# 장기금리 DKW 근사 분해
# ══════════════════════════════════════


def decomposeLongRate(
    nominal: float,
    bei: float,
    tips: float,
    acmTermPremium: float | None = None,
) -> RateDecomposition:
    """10년 명목금리를 3요소로 분해 (DKW 모델 근사).

    Args:
        nominal: 10년 명목금리 DGS10 (%)
        bei: 10년 BEI T10YIE (%)  — 기대인플레이션
        tips: 10년 TIPS DFII10 (%) — 실질금리
        acm_term_premium: Adrian-Crump-Moench 10년 기간프리미엄 (%).
            FRED THREEFYTP10에서 수집. None이면 잔차 근사.

    Returns:
        RateDecomposition
    """
    if acmTermPremium is not None:
        # ACM 모델 기간프리미엄 사용 (NY Fed 추정치)
        term_premium = acmTermPremium
    else:
        # 잔차 근사: 명목 - BEI - TIPS
        term_premium = nominal - bei - tips
    return RateDecomposition(
        nominal=round(nominal, 3),
        expectedInflation=round(bei, 3),
        realRate=round(tips, 3),
        termPremium=round(term_premium, 3),
    )


# ══════════════════════════════════════
# 금 3요인 해석
