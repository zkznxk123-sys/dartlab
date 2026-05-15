"""credit engine notch 보정 규칙 SSOT.

credit/engine.py 가 1319 줄 god module 이라 notch 도메인 분리.
identity 보존을 위해 engine.py 가 본 모듈에서 re-export 한다.

7 규칙 (모두 ``list[tuple[notch_int, reason_str]]`` 반환):
- _notchForRevenue — 매출 규모 기반 시장 지위
- _notchForPublicCorp — 공기업/정부 보호
- _notchForCaptive — 캡티브 금융 별도 D/EBITDA
- _notchForHolding — 지주사 별도 부채비율
- _notchForCapex — CAPEX 집약 OCF 양수
- _notchForMarketCap — 시가총액 상위 시장 지위
- _notchForConsecutiveProfit — 장기 연속 흑자

집계:
- _NOTCH_RULES — 규칙 리스트
- _calcNotchAdjustment — 총 notch 산출 (size cap + A 범위 cap)
"""

from __future__ import annotations

from dartlab.credit._engineConfig import _CONFIG


def _notchForRevenue(latest, **_) -> list[tuple[int, str]]:
    """규칙 1: 기업 규모 (매출 기준)."""
    revenue = latest.get("revenue") or 0
    if revenue > _CONFIG["revenue_mega"]:
        return [(3, f"대형기업 (매출 {revenue / 1e12:.0f}조)")]
    if revenue > _CONFIG["revenue_large"]:
        return [(1, f"중대형기업 (매출 {revenue / 1e12:.0f}조)")]
    return []


def _notchForPublicCorp(company, **_) -> list[tuple[int, str]]:
    """규칙 2: 공기업/정부 보호."""
    corpName = getattr(company, "corpName", "") or ""
    if any(k in corpName for k in _CONFIG["public_corps"]) or "한국전력" in corpName:
        return [(3, "공기업 (정부 보증/규제 보호)")]
    return []


def _notchForCaptive(captive, sepMetrics, **_) -> list[tuple[int, str]]:
    """규칙 3: 캡티브 금융 — 별도 D/EBITDA가 양호하면 상향."""
    if captive and sepMetrics:
        sepDE = sepMetrics.get("separateDebtToEbitda")
        if sepDE is not None and sepDE < 3:
            return [(2, f"캡티브금융 별도 D/EBITDA {sepDE:.1f}x (양호)")]
    return []


def _notchForHolding(holding, sepMetrics, **_) -> list[tuple[int, str]]:
    """규칙 4: 지주사 — 별도 부채비율이 양호하면 상향."""
    if holding and sepMetrics:
        sepDR = sepMetrics.get("separateDebtRatio")
        if sepDR is not None and sepDR < 100:
            return [(2, f"지주사 별도 부채비율 {sepDR:.0f}% (양호)")]
    return []


def _notchForCapex(latest, **_) -> list[tuple[int, str]]:
    """규칙 5: CAPEX 집약 but OCF 양수."""
    ocf = latest.get("ocf") or 0
    fcf = latest.get("fcf") or 0
    if ocf > 0 and fcf < 0 and abs(fcf) > 0:
        return [(1, "CAPEX집약 OCF양수 (투자 사이클)")]
    return []


def _notchForMarketCap(company, **_) -> list[tuple[int, str]]:
    """규칙 6: 시가총액 상위 = 시장이 인정한 시장 지위."""
    try:
        priceData = company.gather("price") if hasattr(company, "gather") else None
        if priceData is None or len(priceData) == 0:
            return []
        epsResult = company.select("IS", ["기본주당이익", "당기순이익"])
        from dartlab.core.utils.helpers import toDict as _tdNotch

        epsParsed = _tdNotch(epsResult)
        if not epsParsed:
            return []
        ed, ep = epsParsed
        eps = (ed.get("기본주당이익", {}) or {}).get(ep[0] if ep else "")
        niE = (ed.get("당기순이익", {}) or {}).get(ep[0] if ep else "")
        closeCol = "close" if "close" in priceData.columns else "종가"
        if not (eps and abs(eps) > 0 and niE and closeCol in priceData.columns):
            return []
        shares = abs(niE / eps)
        latestClose = priceData[closeCol].drop_nulls().to_list()[-1]
        mktCap = shares * latestClose
        if mktCap > _CONFIG["mktcap_top30"]:
            return [(3, f"시가총액 {mktCap / 1e12:.0f}조 (시장 지위)")]
        if mktCap > _CONFIG["mktcap_top100"]:
            return [(1, f"시가총액 {mktCap / 1e12:.0f}조")]
    except (TypeError, ValueError, KeyError, AttributeError, IndexError, ZeroDivisionError):
        pass
    return []


def _notchForConsecutiveProfit(metrics, **_) -> list[tuple[int, str]]:
    """규칙 7: 장기 상장 + 연속 흑자 = 경영 역량 대리."""
    histLen = len(metrics.get("history", []))
    if histLen >= 5:
        niHistory = [h.get("operatingIncome") for h in metrics["history"][:5]]
        allPositive = all(v is not None and v > 0 for v in niHistory)
        if allPositive:
            return [(1, f"연속 {histLen}기 영업흑자 (경영 안정성)")]
    return []


_NOTCH_RULES = [
    _notchForRevenue,
    _notchForPublicCorp,
    _notchForCaptive,
    _notchForHolding,
    _notchForCapex,
    _notchForMarketCap,
    _notchForConsecutiveProfit,
]


def _calcNotchAdjustment(
    company,
    grade: str,
    score: float,
    latest: dict,
    metrics: dict,
    holding: bool,
    captive: bool,
    sepMetrics: dict | None,
) -> dict:
    """v3 Notch Adjustment — 기업 특성 기반 등급 보정.

    정량 점수만으로는 반영 불가능한 요소를 notch 단위로 보정:
    - 기업 규모/시장 지위
    - 공기업/규제 보호
    - 캡티브 금융 별도 부채 양호
    - 지주사 별도 부채 양호
    - CAPEX 집약 OCF 양수

    총 ±5 notch cap. score notch_gate_score 이하에는 미적용 (퇴행 방지).
    """
    if score <= _CONFIG["notch_gate_score"]:
        return {"totalNotch": 0, "reasons": []}

    ctx = dict(company=company, latest=latest, metrics=metrics, holding=holding, captive=captive, sepMetrics=sepMetrics)
    notches: list[tuple[int, str]] = []
    for rule in _NOTCH_RULES:
        notches.extend(rule(**ctx))

    # 총 notch 합산 — 규모별 cap 차등 (과대평가 방지)
    revenue = latest.get("revenue") or 0
    if revenue > _CONFIG["revenue_large"]:
        sizeCap = _CONFIG["notch_cap_large"]
    elif revenue > 1e12:
        sizeCap = _CONFIG["notch_cap_medium"]
    else:
        sizeCap = _CONFIG["notch_cap_small"]

    totalNotch = min(sum(n for n, _ in notches), sizeCap)

    # A 범위: 과보정 방지
    if score <= _CONFIG["notch_a_range_score"]:
        totalNotch = min(totalNotch, _CONFIG["notch_a_range_cap"])

    return {"totalNotch": totalNotch, "reasons": [r for _, r in notches]}
