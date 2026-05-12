from dartlab.providers.dart.docs.finance.summary.constants import BREAKPOINT_THRESHOLD
from dartlab.providers.dart.docs.finance.summary.types import BridgeResult, Segment


def detectBreakpoints(
    pairResults: list[BridgeResult],
    sortedYears: list[str],
    threshold: float = BREAKPOINT_THRESHOLD,
) -> tuple[list[Segment], list[BridgeResult]]:
    """전환점 탐지 + 구간 분리. 매칭률이 threshold 미만이면 전환점으로 판정.

    Args:
        pairResults: 인자.
        sortedYears: 인자.
        threshold: 인자.

    Raises:
        없음.

    Example:
        >>> detectBreakpoints(...)

    Returns:
        <TODO: return desc> (tuple[list[Segment], list[BridgeResult]])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    segments: list[dict] = [{"years": [sortedYears[0]], "pairs": []}]
    breakpoints: list[BridgeResult] = []

    for pr in pairResults:
        isBreak = pr.rate < threshold
        if isBreak:
            breakpoints.append(pr)
            segments.append({"years": [pr.prevYear], "pairs": []})
        else:
            segments[-1]["years"].append(pr.prevYear)
            segments[-1]["pairs"].append(pr)

    segmentStats: list[Segment] = []
    for seg in segments:
        if not seg["pairs"]:
            segmentStats.append(
                Segment(
                    startYear=seg["years"][0],
                    endYear=seg["years"][-1],
                    nYears=len(seg["years"]),
                    matched=0,
                    total=0,
                    rate=None,
                )
            )
            continue
        segMatched = sum(p.matched for p in seg["pairs"])
        segTotal = sum(p.total for p in seg["pairs"])
        segRate = segMatched / segTotal if segTotal > 0 else 0.0
        segmentStats.append(
            Segment(
                startYear=seg["years"][0],
                endYear=seg["years"][-1],
                nYears=len(seg["years"]),
                matched=segMatched,
                total=segTotal,
                rate=segRate,
            )
        )

    return segmentStats, breakpoints
