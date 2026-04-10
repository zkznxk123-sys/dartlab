"""5-1 지배구조 분석 -- 이 회사의 주인은 누구이며, 감시는 작동하는가.

report 데이터(최대주주, 임원, 감사의견)에서 지배구조 핵심 지표를 추출한다.
"""

from __future__ import annotations

from dartlab.analysis.financial._helpers import MAX_RATIO_YEARS
from dartlab.analysis.financial._memoize import memoized_calc

# ── 최대주주 지분 시계열 ──


@memoized_calc
def calcOwnershipTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """최대주주 지분율 시계열 + 최근 주주 구성.

    report.majorHolder에서 연도별 합산 지분율 추이와
    최신 시점 개별 주주(top 10)를 추출한다.

    Returns
    -------
    dict | None
        None: majorHolder 데이터 없음.
        history : list[dict] — 연도별 지분율 추이
            year : str — 연도
            ratio : float — 합산 지분율 (%)
            change : float — 전기 대비 변동 (%p)
        latestHolders : list[dict] — 최근 주주 구성 (상위 10명)
            name : str — 주주명
            relate : str — 관계
            ratio : float — 지분율 (%)
            shares : int — 보유 주식수
    """
    result = _safePivotMajorHolder(company)
    if result is None:
        return None

    years = result.years[-MAX_RATIO_YEARS:]
    ratios = result.totalShareRatio[-MAX_RATIO_YEARS:]

    history = []
    for i, y in enumerate(years):
        r = ratios[i] if i < len(ratios) else None
        prevR = ratios[i - 1] if i > 0 and (i - 1) < len(ratios) else None
        change = round(r - prevR, 2) if r is not None and prevR is not None else None
        history.append({"year": y, "ratio": r, "change": change})

    holders = result.latestHolders[:10] if result.latestHolders else []

    return (
        {
            "history": history,
            "latestHolders": holders,
        }
        if history
        else None
    )


# ── 이사회 구성 ──


@memoized_calc
def calcBoardComposition(company, *, basePeriod: str | None = None) -> dict | None:
    """이사회 구성 -- 사외이사비율, 전체 임원 수.

    report.executive에서 최신 분기 기준 이사회 구성을 추출한다.

    Returns
    -------
    dict
        totalCount : int — 전체 임원 수
        registeredCount : int — 등기임원 수
        outsideCount : int — 사외이사 수
        outsideRatio : float — 사외이사비율 (%)
    """
    result = _safePivotExecutive(company)
    if result is None:
        return None

    total = result.totalCount
    registered = result.registeredCount
    outside = result.outsideCount
    if total == 0:
        return None

    outsideRatio = round(outside / total * 100, 1) if total > 0 else None

    return {
        "totalCount": total,
        "registeredCount": registered,
        "outsideCount": outside,
        "outsideRatio": outsideRatio,
    }


# ── 감사의견 시계열 ──


@memoized_calc
def calcAuditOpinionTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """감사의견 + 감사인 시계열.

    report.audit에서 연도별 감사의견과 감사인을 추출한다.
    감사인 변경도 감지한다.

    Returns
    -------
    dict | None
        None: audit 데이터 없음.
        history : list[dict] — 연도별 감사 이력
            year : str — 연도
            opinion : str — 감사의견
            auditor : str — 감사인
            auditorChanged : bool — 감사인 변경 여부
    """
    result = _safePivotAudit(company)
    if result is None:
        return None

    years = result.years[-MAX_RATIO_YEARS:]
    opinions = result.opinions[-MAX_RATIO_YEARS:]
    auditors = result.auditors[-MAX_RATIO_YEARS:]

    history = []
    for i, y in enumerate(years):
        opinion = opinions[i] if i < len(opinions) else None
        auditor = auditors[i] if i < len(auditors) else None
        prevAuditor = auditors[i - 1] if i > 0 and (i - 1) < len(auditors) else None
        auditorChanged = auditor is not None and prevAuditor is not None and auditor != prevAuditor
        history.append(
            {
                "year": y,
                "opinion": opinion,
                "auditor": auditor,
                "auditorChanged": auditorChanged,
            }
        )

    return {"history": history} if history else None


# ── 플래그 ──


@memoized_calc
def calcGovernanceFlags(company, *, basePeriod: str | None = None) -> list[tuple[str, str]]:
    """지배구조 경고/기회 플래그.

    Returns
    -------
    list[tuple[str, str]]
        (message, severity) 쌍 목록. severity: "warning" | "opportunity"
    """
    flags: list[tuple[str, str]] = []

    # 최대주주 지분
    ownership = calcOwnershipTrend(company)
    if ownership and ownership["history"]:
        latest = ownership["history"][-1]
        r = latest.get("ratio")
        if r is not None:
            if r > 50:
                flags.append((f"최대주주 지분율 {r:.1f}% -- 과반 지배", "warning"))
            elif r < 20:
                flags.append((f"최대주주 지분율 {r:.1f}% -- 경영권 방어 취약", "warning"))

        # 지분 변동 추이
        history = ownership["history"]
        if len(history) >= 3:
            changes = [h["change"] for h in history[-3:] if h.get("change") is not None]
            if len(changes) >= 2 and all(c < -1.0 for c in changes):
                flags.append(("최대주주 지분 2기 연속 감소 -- 지분 희석 주의", "warning"))

    # 이사회 구성
    board = calcBoardComposition(company)
    if board:
        outsideRatio = board.get("outsideRatio")
        if outsideRatio is not None:
            if outsideRatio < 25:
                flags.append((f"사외이사비율 {outsideRatio:.0f}% -- 이사회 독립성 취약", "warning"))
            elif outsideRatio >= 50:
                flags.append((f"사외이사비율 {outsideRatio:.0f}% -- 이사회 독립성 양호", "opportunity"))

    # 감사의견
    audit = calcAuditOpinionTrend(company)
    if audit and audit["history"]:
        latest = audit["history"][-1]
        opinion = latest.get("opinion")
        if opinion and opinion != "적정의견" and opinion != "적정":
            flags.append((f"최근 감사의견: {opinion}", "warning"))

        # 감사인 변경
        changes = [h for h in audit["history"] if h.get("auditorChanged")]
        if len(changes) >= 2:
            flags.append(("감사인 잦은 변경 -- 감사 독립성 점검 필요", "warning"))

    return flags


# ── 내부 헬퍼 ──


def _safePivotMajorHolder(company):
    """report.majorHolder를 안전하게 가져온다."""
    try:
        result = company._report.majorHolder
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


def _safePivotExecutive(company):
    """report.executive를 안전하게 가져온다."""
    try:
        result = company._report.executive
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


def _safePivotAudit(company):
    """report.audit를 안전하게 가져온다."""
    try:
        result = company._report.audit
        if result is None:
            return None
        return result
    except (AttributeError, ValueError, KeyError, TypeError):
        return None
