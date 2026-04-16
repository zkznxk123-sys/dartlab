"""NarrativeDiff — claim 별 가치 기여도 히트맵 (Phase 10 G3).

ICLR 2026 "Thought Anchors" 이론 기반:
조직적 framing 문장이 수치 문장보다 counterfactual importance 높음.
즉, narrative 에서 특정 claim 을 제거했을 때 dFV 가 얼마나 변하는지 측정.

Damodaran "Narrative and Numbers" 의 sensitivity axis 를
"숫자 그리드" 가 아닌 "narrative 그리드" 로 확장.
"""

from __future__ import annotations

from typing import Any


_CLAIM_NEUTRAL_OVERRIDES: dict[str, dict] = {
    # 주요 claim 별 "이 서술이 없다면" 에 해당하는 중립 override
    "매출성장": {"highGrowthRate": 3.0},           # 성장 → 평균
    "마진확장": {"operatingMargin": None},          # 마진 → 현재 유지 (확장 없음)
    "자본효율": {"roic": None},                    # ROIC 프리미엄 → 중립
    "사이클호전": {"terminalGrowthRate": 2.0},
    "경쟁우위지속": {"wacc": 10.0},                # 프리미엄 없는 WACC
    "턴어라운드성공": {"operatingMargin": 5.0},     # 보수적 마진
    "부채감축": {"terminalGrowthRate": 2.0},
}


def computeImpact(
    company: Any,
    *,
    baseline: float | None = None,
    claims: list[str] | None = None,
) -> list[dict]:
    """각 claim 제거 시 dFV 변화 — 가치 기여도 히트맵.

    Parameters
    ----------
    company : Company
    baseline : 기준 dFV (None 이면 계산)
    claims : 분석 claim 리스트 (None 이면 전체)

    Returns
    -------
    list[dict]
        claim : str — 평가 대상 서사
        dFV_neutral : float | None — 중립화 시 dFV
        delta_abs : float — 절대 변화
        delta_pct : float — % 변화
        contribution : float — 이 claim 이 baseline 에 기여한 가치 (%)
    """
    try:
        from dartlab.analysis.valuation.dFV import calcDFV
    except ImportError:
        return []

    # baseline
    if baseline is None:
        base = calcDFV(company)
        if not base or not base.get("dFV"):
            return []
        baseline = base["dFV"]

    targets = claims or list(_CLAIM_NEUTRAL_OVERRIDES.keys())
    results = []

    for claim in targets:
        ov_raw = _CLAIM_NEUTRAL_OVERRIDES.get(claim, {})
        ov = {k: v for k, v in ov_raw.items() if v is not None}
        if not ov:
            continue
        try:
            neutral = calcDFV(company, overrides=ov)
            neutral_dfv = neutral["dFV"] if neutral and neutral.get("dFV") else None
        except (AttributeError, ValueError, TypeError, KeyError):
            neutral_dfv = None

        if neutral_dfv is None:
            results.append({
                "claim": claim,
                "dFV_neutral": None,
                "delta_abs": None,
                "delta_pct": None,
                "contribution": None,
                "error": "neutral DCF 실패",
            })
            continue

        delta_abs = baseline - neutral_dfv
        delta_pct = delta_abs / baseline * 100 if baseline else 0
        contribution = delta_pct  # = 이 claim 이 baseline 에 기여한 %

        results.append({
            "claim": claim,
            "dFV_neutral": neutral_dfv,
            "delta_abs": round(delta_abs, 0),
            "delta_pct": round(delta_pct, 2),
            "contribution": round(contribution, 2),
        })

    # 기여도 절대값 내림차순
    results.sort(key=lambda r: abs(r.get("contribution") or 0), reverse=True)
    return results


def narrateDiff(impacts: list[dict], *, top: int = 5) -> str:
    """NarrativeDiff 결과 → 요약 한 단락."""
    if not impacts:
        return "NarrativeDiff 계산 실패."

    valid = [i for i in impacts if i.get("contribution") is not None]
    if not valid:
        return "가치 기여도 평가 불가 — override 체인 미반영."

    top_claims = valid[:top]
    parts = []
    for i in top_claims:
        sign = "+" if (i["contribution"] or 0) > 0 else ""
        parts.append(f"{i['claim']} {sign}{i['contribution']:.1f}%")
    return f"Top {top} 가치 기여 claim — " + " / ".join(parts)
