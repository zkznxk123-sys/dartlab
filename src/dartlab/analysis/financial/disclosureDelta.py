"""5-2 공시변화감지 -- 이 회사의 공시가 뭐가 달라졌는가.

sections diff 인프라를 활용하여 기간간 공시 텍스트 변화를 정량화한다.
"""

from __future__ import annotations

from dartlab.core.memory import memoizedCalc

# ── 공시변화 종합 요약 ──


@memoizedCalc
def calcDisclosureChangeSummary(company, *, basePeriod: str | None = None) -> dict | None:
    """전체 topic 변화 요약 -- 변화량 상위 topic + 총 변화 건수.

    Capabilities:
        - 전체 topic 변화 건수/비중 + 변화율 상위 10 topic 추출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간 (현재 미사용).

    Returns:
        dict | None: totalChanges/totalTopics/changedTopics/unchangedTopics/
        topChanged 키. 변화 없을 시 None.

    Guide:
        ``company.diff()`` 결과 (sections diff 인프라) 기반 — 텍스트 변화의
        정량적 요약.

    When:
        공시 변화 패턴 전수 진단·이상 topic 식별 시.

    How:
        ``_safeDiffResult`` → summaries 기반 카운트 집계 + topChanged(10).

    Requires:
        sections diff 인프라 (company.diff()).

    Raises:
        없음.

    Example:
        >>> calcDisclosureChangeSummary(Company("005930"))
        {"totalChanges": 5, "topChanged": [...]}

    SeeAlso:
        - ``calcKeyTopicChanges``: 6 핵심 topic
        - ``calcChangeIntensity``: 바이트 변화량

    AIContext:
        AI 답변에서 공시 변화 한 줄 요약 인용 시.
    """
    diffResult = _safeDiffResult(company)
    if diffResult is None:
        return None

    summaries = diffResult.summaries
    if not summaries:
        return None

    topChanged = diffResult.topChanged(10)
    totalChanges = diffResult.totalChanges
    totalTopics = len(summaries)
    changedTopics = sum(1 for s in summaries if s.changedCount > 0)

    top = []
    for s in topChanged:
        if s.changedCount == 0:
            continue
        top.append(
            {
                "topic": s.topic,
                "chapter": s.chapter,
                "totalPeriods": s.totalPeriods,
                "changedCount": s.changedCount,
                "changeRate": round(s.changeRate, 3),
            }
        )

    return (
        {
            "totalChanges": totalChanges,
            "totalTopics": totalTopics,
            "changedTopics": changedTopics,
            "unchangedTopics": totalTopics - changedTopics,
            "topChanged": top,
        }
        if top
        else None
    )


# ── 핵심 공시 변화 추적 ──


_KEY_TOPICS = [
    "businessOverview",
    "riskFactors",
    "accountingPolicy",
    "contingencies",
    "relatedPartyTransactions",
    "segmentInfo",
]


@memoizedCalc
def calcKeyTopicChanges(company, *, basePeriod: str | None = None) -> dict | None:
    """핵심 공시 topic 변화 추적.

    Capabilities:
        - 분석상 중요한 6 topic (businessOverview/riskFactors/accountingPolicy/
          contingencies/relatedPartyTransactions/segmentInfo) 의 변화 정보 추출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간 (현재 미사용).

    Returns:
        dict | None: keyTopics 키에 topic 별 변화 정보. summary 부재 시 None.

    Guide:
        topic 가용 여부는 ``company.topics`` 에서 확인 후 누락 topic 은 skip.

    When:
        분석상 중요한 공시 항목의 변화 시계열 추적이 필요할 때.

    How:
        ``_safeDiffResult`` summaries 를 topic 키로 매핑 → 6 핵심 topic 필터링.

    Requires:
        sections diff 인프라 + topics 열거.

    Raises:
        없음.

    Example:
        >>> calcKeyTopicChanges(Company("005930"))
        {"keyTopics": [{"topic": "riskFactors", "changeRate": 0.4, ...}]}

    SeeAlso:
        - ``calcDisclosureChangeSummary``: 전체 요약

    AIContext:
        AI 답변에서 핵심 공시 변화 인용 시.
    """
    diffResult = _safeDiffResult(company)
    if diffResult is None:
        return None

    summaryMap = {s.topic: s for s in diffResult.summaries}
    topicsAttr = getattr(company, "topics", None)
    if topicsAttr is not None and hasattr(topicsAttr, "get_column"):
        availableTopics = set(topicsAttr.get_column("topic").to_list())
    elif isinstance(topicsAttr, list):
        availableTopics = set(topicsAttr)
    else:
        availableTopics = set(summaryMap.keys())

    results = []
    for topic in _KEY_TOPICS:
        if topic not in availableTopics:
            continue
        s = summaryMap.get(topic)
        if s is None:
            continue
        results.append(
            {
                "topic": topic,
                "chapter": s.chapter,
                "totalPeriods": s.totalPeriods,
                "changedCount": s.changedCount,
                "stableCount": s.stableCount,
                "changeRate": round(s.changeRate, 3),
            }
        )

    return {"keyTopics": results} if results else None


# ── 변화 크기 분석 ──


@memoizedCalc
def calcChangeIntensity(company, *, basePeriod: str | None = None) -> dict | None:
    """변화 크기(바이트) 분석 -- 어떤 topic이 얼마나 크게 바뀌었나.

    Capabilities:
        - topic 별 abs(toLen - fromLen) 누적 바이트 변화량 + 상위 10.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간 (현재 미사용).

    Returns:
        dict | None: topByDelta + totalDeltaBytes. entries 부재 시 None.

    Guide:
        변화 빈도 (rate) 대신 변화 크기 (byte) 관점. 큰 보수공시 변경 식별.

    When:
        대규모 공시 본문 개정 (사업보고서 리뉴얼·신규 사업 추가) 추적 시.

    How:
        ``_safeDiffResult`` entries 순회 → topic 별 delta 합산 → 정렬 top 10.

    Requires:
        sections diff 인프라.

    Raises:
        없음.

    Example:
        >>> calcChangeIntensity(Company("005930"))
        {"topByDelta": [{"topic": "...", "totalDeltaBytes": 12345}, ...]}

    SeeAlso:
        - ``calcDisclosureChangeSummary``: 변화율 (frequency)

    AIContext:
        AI 답변에서 공시 본문 대규모 개정 인용 시.
    """
    diffResult = _safeDiffResult(company)
    if diffResult is None:
        return None

    entries = diffResult.entries
    if not entries:
        return None

    # topic별 누적 변화량
    topicDelta: dict[str, int] = {}
    for e in entries:
        delta = abs(e.toLen - e.fromLen)
        topicDelta[e.topic] = topicDelta.get(e.topic, 0) + delta

    if not topicDelta:
        return None

    ranked = sorted(topicDelta.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "topByDelta": [{"topic": topic, "totalDeltaBytes": delta} for topic, delta in ranked],
        "totalDeltaBytes": sum(topicDelta.values()),
    }


# ── 플래그 ──


@memoizedCalc
def calcDisclosureDeltaFlags(company, *, basePeriod: str | None = None) -> list[tuple[str, str]]:
    """공시변화감지 경고/기회 플래그.

    Capabilities:
        - 변화 없음 (보일러플레이트)·핵심 topic 빈번 변화·회계정책 변경 등을
          (메시지, severity) 튜플 리스트로 산출.

    Args:
        company: 분석 대상 기업.
        basePeriod: 기준 기간 (현재 미사용).

    Returns:
        list[tuple[str, str]]: 각 원소는 (한국어 플래그, "warning"|"opportunity").

    Guide:
        flag 신호 — keyTopic changeRate ≥ 80%, 3 기 연속 무변화, 회계정책
        변경 감지.

    When:
        보고서·UI 위험 배너에 공시 신뢰성 경고 한 줄 표시.

    How:
        ``calcDisclosureChangeSummary`` + ``calcKeyTopicChanges`` 결과를
        임계와 비교 후 (메시지, severity) 생성.

    Requires:
        하위 2 calc 가용성.

    Raises:
        없음.

    Example:
        >>> calcDisclosureDeltaFlags(Company("005930"))
        [("회계정책 공시 변경 ...", "warning")]

    SeeAlso:
        - ``calcDisclosureChangeSummary``: 본 함수 입력

    AIContext:
        AI 답변에서 공시 신뢰성 위험 인용 시.
    """
    flags: list[tuple[str, str]] = []

    summary = calcDisclosureChangeSummary(company)
    if summary is None:
        return flags

    # 변화 없는 회사
    if summary["changedTopics"] == 0:
        flags.append(("전 기간 공시 텍스트 변화 없음 -- 보일러플레이트 가능성", "warning"))
        return flags

    # 핵심 topic 변화 감지
    keyChanges = calcKeyTopicChanges(company)
    if keyChanges and keyChanges["keyTopics"]:
        for kt in keyChanges["keyTopics"]:
            topic = kt["topic"]
            rate = kt["changeRate"]
            if rate >= 0.8:
                flags.append((f"{topic}: 변화율 {rate:.0%} -- 빈번한 공시 변경", "warning"))
            elif rate == 0:
                if kt["totalPeriods"] >= 3:
                    flags.append((f"{topic}: {kt['totalPeriods']}기 연속 무변화", "warning"))

    # 상위 변화 topic
    topChanged = summary.get("topChanged", [])
    if topChanged:
        top = topChanged[0]
        if top["changeRate"] >= 0.8:
            flags.append((f"최다 변화 topic: {top['topic']} (변화율 {top['changeRate']:.0%})", "warning"))

    # 회계정책 변경 감지
    if keyChanges and keyChanges["keyTopics"]:
        acctPolicy = next(
            (kt for kt in keyChanges["keyTopics"] if kt["topic"] == "accountingPolicy"),
            None,
        )
        if acctPolicy and acctPolicy["changedCount"] > 0:
            flags.append(("회계정책 공시 변경 감지 -- 정책 변경 여부 확인 필요", "warning"))

    return flags


# ── 내부 헬퍼 ──


def _safeDiffResult(company):
    """providers.dart.sections.sectionsWide(panel 섹션)에서 DiffResult를 안전하게 얻는다.

    docs.parquet 농장 은퇴 → panel 섹션 wide(topic×period) SSOT 경유. 결과를
    company._cache에 저장하여 4개 calc 함수가 공유.
    """
    cache = getattr(company, "_cache", None)
    _KEY = "_diffResult"
    if cache is not None and _KEY in cache:
        return cache[_KEY]

    result = None
    try:
        code = getattr(company, "stockCode", None)
        if code:
            from dartlab.providers._common.diff import sectionsDiff
            from dartlab.providers.dart.sections import sectionsWide

            wide = sectionsWide(code)
            if wide is not None:
                result = sectionsDiff(wide)
    except (AttributeError, ValueError, KeyError, TypeError, ImportError):
        pass

    if cache is not None:
        cache[_KEY] = result
    return result
