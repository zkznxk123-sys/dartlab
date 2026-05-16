"""credit/features/narrative 추세 라인 + 인과 사슬 빌더.

credit/features/narrative.py 가 934 줄이라 trend 라인 5 + 인과 빌더 3 분리.
identity 보존을 위해 narrative.py 가 본 모듈에서 re-export 한다.

추세 라인 헬퍼:
- _trendRevenueLine — 매출 전년비
- _trendOpIncomeLine — 영업이익 전년비 (|>30%|)
- _trendDebtEbitdaLine — Debt/EBITDA 변화
- _trendDebtRatioLine — 부채비율 변화 (|>5pp|)
- _trendMultiYearStoryLine — 3~5년 시계열 V자/연속 추세

인과 사슬 빌더:
- _buildCausalChainParts — 매출/이익/현금/부채 인과 체인
- _buildCreditIntroSentence — 등급 도입 문장
- _buildStrengthWeaknessSentences — 강점/약점 문장
"""

from __future__ import annotations

from dartlab.core.formatting import formatKr
from dartlab.credit.features._narrativeTypes import AxisNarrative


def _fmtTril(v) -> str:
    return formatKr(v, withWon=True, nullStr="N/A")


def _trendRevenueLine(h0: dict, h1: dict) -> str | None:
    """매출 전년비."""
    rev0, rev1 = h0.get("revenue"), h1.get("revenue")
    if not (rev0 and rev1 and rev1 != 0):
        return None
    chg = (rev0 - rev1) / abs(rev1) * 100
    direction = "증가" if chg > 0 else "감소"
    return f"매출 전년비 {'+' if chg > 0 else ''}{chg:.0f}% {direction}"


def _trendOpIncomeLine(h0: dict, h1: dict) -> str | None:
    """영업이익 전년비 (|>30%|)."""
    oi0, oi1 = h0.get("operatingIncome"), h1.get("operatingIncome")
    if not (oi0 and oi1 and oi1 != 0):
        return None
    chg = (oi0 - oi1) / abs(oi1) * 100
    if abs(chg) <= 30:
        return None
    direction = "대폭 개선" if chg > 0 else "대폭 악화"
    return f"영업이익 {'+' if chg > 0 else ''}{chg:.0f}% ({direction})"


def _trendDebtEbitdaLine(h0: dict, h1: dict) -> str | None:
    """Debt/EBITDA 변화."""
    de0, de1 = h0.get("debtToEbitda"), h1.get("debtToEbitda")
    if de0 is None or de1 is None:
        return None
    if de0 < de1:
        return f"Debt/EBITDA {de1:.1f}→{de0:.1f}배로 개선"
    if de0 > de1 * 1.2:
        return f"Debt/EBITDA {de1:.1f}→{de0:.1f}배로 악화"
    return None


def _trendDebtRatioLine(h0: dict, h1: dict) -> str | None:
    """부채비율 변화 (|>5pp|)."""
    dr0, dr1 = h0.get("debtRatio"), h1.get("debtRatio")
    if dr0 is None or dr1 is None:
        return None
    delta = dr0 - dr1
    if abs(delta) <= 5:
        return None
    direction = "상승" if delta > 0 else "하락"
    return f"부채비율 {dr1:.0f}%→{dr0:.0f}%로 {direction}"


def _trendMultiYearStoryLine(history: list[dict]) -> str | None:
    """3~5년 Debt/EBITDA 시계열 스토리 (V자 or 연속 개선/악화)."""
    if len(history) < 4:
        return None
    deList = [h.get("debtToEbitda") for h in history[:5]]
    validDe = [(i, v) for i, v in enumerate(deList) if v is not None]
    if len(validDe) < 3:
        return None
    values = [v for _, v in validDe]
    peak = max(values)
    trough = min(values)
    peakIdx = values.index(peak)
    troughIdx = values.index(trough)
    periods = [h.get("period", "") for h in history[:5]]
    if peak > trough * 2 and peakIdx > troughIdx:
        return (
            f"Debt/EBITDA가 {periods[troughIdx]}년 {trough:.1f}배에서 "
            f"{periods[peakIdx]}년 {peak:.1f}배까지 악화 후 "
            f"{periods[0]}년 {values[0]:.1f}배로 회복."
        )
    if all(values[i] >= values[i + 1] for i in range(len(values) - 1)):
        return f"Debt/EBITDA가 {len(values)}개년 연속 개선 추세."
    if all(values[i] <= values[i + 1] for i in range(len(values) - 1)):
        return f"Debt/EBITDA가 {len(values)}개년 연속 악화 추세."
    return None


def _buildCausalChainParts(result: dict) -> list[str]:
    """result → 매출/이익/현금/부채 인과 체인 부분 문구 리스트."""
    metricsHistory = result.get("metricsHistory", [])
    latest = metricsHistory[0] if metricsHistory else {}
    rev = latest.get("revenue")
    oi = latest.get("operatingIncome")
    ocf = latest.get("ocf")
    netDebt = latest.get("netDebt")
    debtRatio = latest.get("debtRatio")

    chainParts: list[str] = []
    if rev and rev > 0:
        chainParts.append(f"매출 {_fmtTril(rev)} 규모")
    if oi is not None and rev and rev > 0:
        margin = oi / rev * 100
        if oi > 0:
            chainParts.append(f"영업이익률 {margin:.0f}%의 수익 기반")
        else:
            chainParts.append(f"영업적자(이익률 {margin:.0f}%)의 수익 부진")
    if ocf is not None and ocf > 0:
        chainParts.append(f"OCF {_fmtTril(ocf)}의 현금창출력")
    if netDebt is not None:
        if netDebt <= 0:
            chainParts.append("부채 부담 없는 순현금 구조")
        elif debtRatio is not None and debtRatio < 100:
            chainParts.append(f"부채비율 {debtRatio:.0f}%의 안정적 자본구조")
        elif debtRatio is not None:
            chainParts.append(f"부채비율 {debtRatio:.0f}%의 레버리지 부담")
    return chainParts


def _buildCreditIntroSentence(grade: str, score: float, chainParts: list[str]) -> str:
    """인과 체인 → 등급 도입 문장."""
    if len(chainParts) < 2:
        return f"종합 신용등급 {grade} (점수 {score:.1f}/100)."
    intro = f"{grade}는 "
    if len(chainParts) >= 3:
        intro += f"[{chainParts[0]}]에서 출발하는 [{chainParts[1]}]이 [{chainParts[2]}]를 유지하게 하고, "
        if len(chainParts) >= 4:
            intro += f"[{chainParts[3]}]가 "
        intro += "등급을 뒷받침하는 구조를 반영한다."
    else:
        intro += f"[{chainParts[0]}]에서 비롯된 [{chainParts[1]}]이 등급을 뒷받침한다."
    return intro


def _buildStrengthWeaknessSentences(strengths: list[AxisNarrative], weaknesses: list[AxisNarrative]) -> list[str]:
    """강점/약점 방어/압력 문장."""
    parts: list[str] = []
    if strengths:
        sNames = ", ".join(n.axisName for n in strengths)
        if weaknesses:
            parts.append(f"핵심 강점인 {sNames}이 업황 변동 시에도 등급을 방어하는 완충 역할을 한다.")
        else:
            parts.append(f"핵심 강점인 {sNames}이 등급의 안정적 기반이다.")
    if weaknesses:
        wNames = ", ".join(n.axisName for n in weaknesses)
        parts.append(f"다만 {wNames}은 등급 하방 압력 요인으로 모니터링이 필요하다.")
    return parts


__all__ = [
    "_buildCausalChainParts",
    "_buildCreditIntroSentence",
    "_buildStrengthWeaknessSentences",
    "_trendDebtEbitdaLine",
    "_trendDebtRatioLine",
    "_trendMultiYearStoryLine",
    "_trendOpIncomeLine",
    "_trendRevenueLine",
]
