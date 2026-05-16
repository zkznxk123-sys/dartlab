"""macro/crisis/detectors Dalio Part 1 도메인 분리.

macro/crisis/detectors.py 가 803 줄 god module 이라 Dalio Big Debt Cycle 분리.
identity 보존을 위해 detectors.py 가 본 모듈에서 re-export 한다.

함수 + 상수:
- _DALIO_PHASE_LABELS — 6 단계 한국어 라벨
- _SUB_PHASE_LABELS — Beautiful Deleveraging 내부 4 단계 라벨
- _VARIANT_LABELS — Deflationary/Inflationary 변종 라벨
- dalioDebtCyclePhase — 부채 사이클 6 단계 판정
- dalioPolicyLeverStatus — 정책 4 레버 (monetary/fiscal/credit/fx) 소진도
"""

from __future__ import annotations

from dartlab.macro.crisis._detectorsHelpers import (
    _beautifulDeleveragingSubPhase,
    _dalioRegimeVariant,
)
from dartlab.macro.crisis._detectorTypes import DalioPhaseResult, DalioPolicyLeverResult

# ══════════════════════════════════════
# Dalio — Big Debt Crises Part 1 템플릿
# ══════════════════════════════════════


_DALIO_PHASE_LABELS = {
    "earlyBoom": "초기 확장기",
    "lateBoom": "후기 확장기",
    "topBubble": "거품 정점",
    "deflationaryDepression": "디플레이션 공황",
    "beautifulDeleveraging": "아름다운 디레버리징",
    "reflationary": "재팽창기",
}


# ══════════════════════════════════════════════════════════════════════
# Dalio Part 1 세부 — Beautiful Deleveraging 내부 4단계 + Regime Variant
# ══════════════════════════════════════════════════════════════════════
#
# beautifulDeleveraging 단계의 내부 4 순서 (Dalio Part 1):
#   austerity (긴축) → defaultRestructuring (디폴트) → moneyPrinting (화폐발행)
#   → wealthTransfer (재분배)
#
# regimeVariant: 환율/기축통화/외화부채에 따라 deflationary vs inflationary


_SUB_PHASE_LABELS = {
    "austerity": "긴축",
    "defaultRestructuring": "디폴트/구조조정",
    "moneyPrinting": "화폐발행",
    "wealthTransfer": "재분배",
}

_VARIANT_LABELS = {
    "deflationary": "디플레이션형",
    "inflationary": "인플레이션형",
}


def dalioDebtCyclePhase(
    *,
    totalDebtToGdp: float | None = None,
    debtServiceYoY: float | None = None,
    creditGap: float | None = None,
    realRate: float | None = None,
    gdpGrowth: float | None = None,
    # subPhase 판정용 (beautifulDeleveraging 에서만 활성)
    m2GrowthYoy: float | None = None,
    npl: float | None = None,
    hySpread: float | None = None,
    fiscalDeficitPctGdp: float | None = None,
    # regimeVariant 판정용
    fxFlexibility: str | None = None,
    reserveCurrency: bool | None = None,
    foreignDebtPct: float | None = None,
) -> DalioPhaseResult:
    """Dalio 부채사이클 6단계 판정 (Big Debt Crises Part 1 템플릿).

    실험 053 검증: 8개 역사 케이스 중 7개 (88%) 정확.
    팬데믹급 급전환은 transition — 단일 enum 한계. 해석 시
    `policyLeverStatus` 와 조합 권장.

    Parameters
    ----------
    totalDebtToGdp : 총부채/GDP (%). 일반 선진국 100~300.
    debtServiceYoY : 부채서비스(이자/소득) YoY 변화 (%p).
    creditGap : BIS Credit-to-GDP gap (%p). >8 과열.
    realRate : 실질금리 (%).
    gdpGrowth : 실질 GDP 성장률 (%).

    Returns
    -------
    DalioPhaseResult
        phase enum + 한국어 라벨 + 판정 신호 + 종합 설명.
    """
    signals: list[str] = []

    # 입력 결측 → earlyBoom 기본값
    if gdpGrowth is None and creditGap is None and realRate is None:
        return DalioPhaseResult(
            phase="earlyBoom",
            phaseLabel=_DALIO_PHASE_LABELS["earlyBoom"],
            signals=["데이터 부족 — 기본값"],
            description="입력 부족으로 기본값(초기 확장기) 반환",
        )

    g = gdpGrowth if gdpGrowth is not None else 0.0
    cg = creditGap if creditGap is not None else 0.0
    rr = realRate if realRate is not None else 0.0
    ds = debtServiceYoY if debtServiceYoY is not None else 0.0

    # 1. 디플레이션 공황
    if g < -1.0 and cg < 0:
        signals.append(f"GDP 성장 {g:+.1f}% + 신용갭 {cg:+.1f}%p 음전환")
        phase = "deflationaryDepression"
    # 2. Reflationary
    elif rr < -2.0 and g >= -2.0:
        signals.append(f"실질금리 {rr:+.1f}% 깊은 마이너스 + 성장 회복 중")
        phase = "reflationary"
    # 3. Top Bubble
    elif cg >= 8.0 and g > 0 and rr < 2.0:
        signals.append(f"신용갭 {cg:+.1f}%p 과열 + 성장 {g:+.1f}% + 실질금리 {rr:+.1f}%")
        phase = "topBubble"
    # 4. Late Boom
    elif cg >= 2.0 and ds > 0 and g > 0:
        signals.append(f"신용갭 {cg:+.1f}%p 상승 + 부채서비스 {ds:+.1f}%p 악화")
        phase = "lateBoom"
    # 5. Beautiful Deleveraging
    elif ds < 0 and g > 0:
        signals.append(f"부채서비스 {ds:+.1f}%p 개선 + 성장 {g:+.1f}% 양호")
        phase = "beautifulDeleveraging"
    # 6. Early Boom (기본)
    else:
        signals.append("신용 완만 + 성장 건강")
        phase = "earlyBoom"

    if totalDebtToGdp is not None:
        signals.append(f"총부채/GDP {totalDebtToGdp:.0f}%")

    label = _DALIO_PHASE_LABELS[phase]
    desc = f"Dalio 부채사이클: {label} ({phase})"

    # subPhase: beautifulDeleveraging 에서만 세분화
    subPhase = None
    subPhaseLab = None
    if phase == "beautifulDeleveraging":
        subPhase = _beautifulDeleveragingSubPhase(
            realRate=realRate,
            m2GrowthYoy=m2GrowthYoy,
            debtServiceYoY=ds,
            npl=npl,
            hySpread=hySpread,
            fiscalDeficitPctGdp=fiscalDeficitPctGdp,
        )
        subPhaseLab = _SUB_PHASE_LABELS.get(subPhase) if subPhase else None
        if subPhase:
            signals.append(f"deleveraging sub: {subPhase}")

    # regimeVariant: 환율/기축통화 기반
    variant = _dalioRegimeVariant(
        fxFlexibility=fxFlexibility,
        reserveCurrency=reserveCurrency,
        realRate=realRate,
        foreignDebtPct=foreignDebtPct,
    )
    variantLab = _VARIANT_LABELS.get(variant) if variant else None
    if variant:
        signals.append(f"regime: {variant}")

    return DalioPhaseResult(
        phase=phase,
        phaseLabel=label,
        signals=signals,
        description=desc,
        subPhase=subPhase,
        subPhaseLabel=subPhaseLab,
        regimeVariant=variant,
        regimeVariantLabel=variantLab,
    )


def dalioPolicyLeverStatus(
    *,
    policyRate: float | None = None,
    publicDebtToGdp: float | None = None,
    creditGap: float | None = None,
    fxFlexibility: str | None = None,
) -> DalioPolicyLeverResult:
    """Dalio 정책 4 레버 소진도 판정 (Big Debt Crises Ch.3).

    위기 대응 시 정부가 쓸 수 있는 수단이 얼마나 남아있는가 — 가장
    중요한 것은 "여유 레버가 남아있나" 이다 (Dalio).

    Parameters
    ----------
    policyRate : 기준금리 (%). <= 0.5% → maxed, <= 2% → partial, 그 외 spare.
    publicDebtToGdp : 공공부채/GDP (%). >= 120 → maxed, >= 80 → partial, 그 외 spare.
    creditGap : BIS credit-to-GDP gap (%p). >= 8 → maxed, >= 2 → partial, 그 외 spare.
    fxFlexibility : "flexible"|"managed"|"pegged" — peg/관리 = maxed, 자유변동 = spare.

    Returns
    -------
    DalioPolicyLeverResult
        4 레버 상태 + 소진도 점수 (3=maxed, 2=partial, 1=spare, 합계 0~12).
    """
    signals: list[str] = []

    def _ratePhase(v: float | None) -> str:
        if v is None:
            return "spare"
        if v <= 0.5:
            return "maxed"
        if v <= 2.0:
            return "partial"
        return "spare"

    def _debtPhase(v: float | None) -> str:
        if v is None:
            return "spare"
        if v >= 120:
            return "maxed"
        if v >= 80:
            return "partial"
        return "spare"

    def _creditPhase(v: float | None) -> str:
        if v is None:
            return "spare"
        if v >= 8:
            return "maxed"
        if v >= 2:
            return "partial"
        return "spare"

    def _fxPhase(v: str | None) -> str:
        if v is None:
            return "spare"
        if v == "pegged":
            return "maxed"
        if v == "managed":
            return "partial"
        return "spare"

    monetary = _ratePhase(policyRate)
    fiscal = _debtPhase(publicDebtToGdp)
    credit = _creditPhase(creditGap)
    fx = _fxPhase(fxFlexibility)

    if policyRate is not None:
        signals.append(f"기준금리 {policyRate:.2f}% — 통화정책 {monetary}")
    if publicDebtToGdp is not None:
        signals.append(f"공공부채/GDP {publicDebtToGdp:.0f}% — 재정정책 {fiscal}")
    if creditGap is not None:
        signals.append(f"신용갭 {creditGap:+.1f}%p — 신용정책 {credit}")
    if fxFlexibility is not None:
        signals.append(f"환율 체제 {fxFlexibility} — fx 레버 {fx}")

    scoreMap = {"maxed": 3, "partial": 2, "spare": 1}
    score = scoreMap[monetary] + scoreMap[fiscal] + scoreMap[credit] + scoreMap[fx]
    return DalioPolicyLeverResult(
        monetary=monetary,
        fiscal=fiscal,
        credit=credit,
        fx=fx,
        exhaustionScore=score,
        signals=signals,
    )


__all__ = [
    "_DALIO_PHASE_LABELS",
    "_SUB_PHASE_LABELS",
    "_VARIANT_LABELS",
    "dalioDebtCyclePhase",
    "dalioPolicyLeverStatus",
]
