"""학습된 rules 기반 sections 수평화 runtime."""

from __future__ import annotations

import re

from dartlab.providers.dart.docs.sections.artifacts import loadProjectionRules
from dartlab.providers.dart.docs.sections.sectionsBase import RE_SPLIT_SUFFIX

_RE_MAJOR_HEADING = re.compile(r"^([가-힣])\.\s*(.+)$")
_RE_TABLE_SEP = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
from dartlab.core.mappers.parserMapper import loadSections

_CHAPTER_BY_MAJOR = {int(k): v for k, v in loadSections().get("chapterByMajor", {}).items()}
_CHAPTER_II_SPLIT_SOURCE = "주요제품및원재료등"
_CHAPTER_II_SPLIT_FALLBACK_TARGETS = ("productService", "rawMaterial")
_ATOMIC_SEMANTIC_TOPICS = {
    "segmentSemiconductor",
    "segmentIct",
    "segmentDigitalMedia",
    "segmentHomeAppliance",
    "segmentDisplay",
    "segmentHarman",
    "segmentOther",
    "marketRisk",
    "creditRisk",
    "liquidityRisk",
    "capitalRisk",
    "fxRisk",
    "interestRateRisk",
    "fairValueRisk",
    "derivativeExposure",
}
_SEC = loadSections()
_DETAIL_TOPIC_MAP = _SEC.get("detailTopicMap", {})
_DETAIL_TOPIC_KEYWORDS = {k: tuple(v) for k, v in _SEC.get("detailTopicKeywords", {}).items()}


def chapterFromMajorNum(majorNum: int) -> str | None:
    """정수 장번호 → 로마숫자 chapter 매핑 (1→"I" / 2→"II" / 3→"III" ...).

    Capabilities:
        - ``_CHAPTER_BY_MAJOR`` (parserMapper 가 load 한 ``chapterByMajor`` 매핑) 으로 단순 lookup.
        - 매핑 외 값 (예 0/8 이상) → None.
        - 정기보고서 chapter 정렬 (예 II=사업의 내용 / III=재무에 관한 사항) 의 SSOT.

    Args:
        majorNum: 정수 장번호 (1~7 사이가 일반적, parserMapper 매핑에 따라 달라짐).

    Returns:
        str | None — 로마숫자 chapter ("I"/"II"/"III"/...). 매핑 없음 → None.

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import chapterFromMajorNum
        >>> chapterFromMajorNum(2)
        'II'
        >>> chapterFromMajorNum(999) is None
        True

    Guide:
        - "사업의 내용 (장 2) 가 무엇인지" → ``chapterFromMajorNum(2)`` → "II".
        - "raw majorNum 정수만 알고 chapter 문자열 필요" → 본 함수.
        - 역방향 (chapter → majorNum) 은 ``_CHAPTER_BY_MAJOR`` 의 inverse map 필요.

    SeeAlso:
        - ``dartlab.core.mappers.parserMapper.loadSections`` — ``chapterByMajor`` SSOT.
        - ``applyProjections`` — chapter II 합산 topic 분배 시 본 매핑 사용.
        - ``detailTopicForTopic`` / ``semanticTopicForLabel`` — 같은 sections runtime API 집합.

    Requires:
        - dartlab.core.mappers.parserMapper — chapter 매핑 source (module top-level load).

    AIContext:
        Ask Workbench 가 "사업의 내용 어디에 있냐"/"III 장 본문" 질문 처리 시 호출. AI 가
        사람에게 chapter 표기 일관성 유지 (II/2 혼용 X). None 반환 = 비정상 majorNum,
        sections 파이프라인 버그 의심 — 그대로 무시 X, 로깅 필요.

    LLM Specifications:
        AntiPatterns:
            - 부동소수 majorNum (예 2.5) → KeyError 아닌 None (dict.get).
            - chapter 매핑이 동적 (parserMapper 갱신) → 본 함수 결과도 모듈 load 시점 의존.
        OutputSchema:
            - 1 스칼라. str | None.
        Prerequisites:
            - ``loadSections().chapterByMajor`` 가 비어 있지 않아야 한다 (parserMapper 정상).
        Freshness:
            - parserMapper 의 chapter 매핑 갱신 시 갱신 (현재 정기보고서 표준).
        Dataflow:
            - parserMapper.chapterByMajor → 본 함수 → applyProjections / caller (AI).
        TargetMarkets:
            - KR (DART) 정기보고서 한정. EDGAR 10-K item 구조와 무관.

    Raises:
        없음.
    """
    return _CHAPTER_BY_MAJOR.get(majorNum)


def baseChunkPath(path: str) -> str:
    """chunk path에서 분할 접미사를 제거하여 기본 경로를 반환한다.

    Args:
        path: 인자.

    Raises:
        없음.

    Example:
        >>> baseChunkPath(...)

    Returns:
        <TODO: return desc> (str)

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
    return RE_SPLIT_SUFFIX.sub("", path)


def chapterTeacherTopics(rows: list[dict[str, object]]) -> dict[str, set[str]]:
    """chapter별로 등장하는 topic 집합을 수집한다.

    Args:
        rows: 인자.

    Raises:
        없음.

    Example:
        >>> chapterTeacherTopics(...)

    Returns:
        <TODO: return desc> (dict[str, set[str]])

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
    teacher: dict[str, set[str]] = {}
    for row in rows:
        chapter = row["chapter"]
        topic = row["topic"]
        if not isinstance(chapter, str) or not isinstance(topic, str):
            continue
        teacher.setdefault(chapter, set()).add(topic)
    return teacher


def projectionSuppressedTopics() -> dict[str, set[str]]:
    """projection 규칙에 의해 억제되는 chapter별 topic 집합을 반환한다.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> projectionSuppressedTopics(...)

    Returns:
        <TODO: return desc> (dict[str, set[str]])

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
    rules = loadProjectionRules("chapterII")
    suppressed = set(rules.keys())
    suppressed.add(_CHAPTER_II_SPLIT_SOURCE)
    return {"II": suppressed}


def splitByMajorHeading(text: str) -> list[tuple[str, str]]:
    """텍스트를 ``가./나./다.`` 한글 한 글자 + 점 + 공백 + 제목 패턴 기준으로 분리.

    Capabilities:
        - 정규식 ``^([가-힣])\\.\\s*(.+)$`` 으로 라인 단위 매칭.
        - 매칭된 라인을 새 segment 시작 (label = 매칭 라인 자체).
        - 미매칭 라인은 현 segment 의 body 누적.
        - 빈 라인은 skip, body 가 빈 segment 는 제외.
        - 첫 segment label = ``"(root)"`` (heading 등장 전 본문).

    Args:
        text: 분리 대상 다중 라인 텍스트. 정기보고서 본문 chunk 단위가 일반적.

    Returns:
        list[tuple[str, str]] — ``[(label, body), ...]``. body 가 빈 항목은 제외.
        heading 자체가 없으면 ``[("(root)", text)]`` (root 만 1 개).

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import splitByMajorHeading
        >>> text = "가. 개요\\n본문 1\\n나. 상세\\n본문 2"
        >>> result = splitByMajorHeading(text)
        >>> len(result) == 2 and result[0][0].startswith("가.")
        True

    Guide:
        - "사업의 내용 chunk 를 의미 단위로 쪼개기" → 본 함수.
        - heading 이 영문/숫자 (예 "1. ")라면 매칭 안 됨 — 한글 한 글자 (``가-힣``) 만.
        - 분리 후 각 segment 를 ``semanticTopicForLabel`` 로 분류해 최종 topic 결정.

    SeeAlso:
        - ``extractSemanticUnits`` — 본 함수를 wrap 해 부문/리스크 topic 한정 사용.
        - ``semanticTopicForLabel`` — 분리된 label 의 semantic 분류 진행.
        - ``applyProjections`` — chapter II ``주요제품및원재료등`` 분할 시 본 함수 활용.

    Requires:
        - re (stdlib) — ``_RE_MAJOR_HEADING`` 정규식.
        - 외부 dependency 없음 — 순수 텍스트 처리.

    AIContext:
        Workbench 가 "이 회사 사업의 내용 II장 어떤 항목 있냐" 류 질문 처리 시 sections 파이프
        내부에서 호출. 단독 노출은 드물고 ``applyProjections`` 내부에서 ``주요제품및원재료등``
        합산 chunk 를 ``productService`` / ``rawMaterial`` 로 쪼개기 위해 사용.

    LLM Specifications:
        AntiPatterns:
            - heading 이 한글 한 글자 + 점 패턴 외 → 미분리 → ``[("(root)", text)]``.
            - 본문 안 ``가.`` 같은 우연 매칭 (예 일반 문장 시작) → 잘못된 segment 분리 가능성.
              caller 가 결과 검토 필요.
        OutputSchema:
            - row: N segment = N heading + 1 (root) 또는 root 만 1.
            - tuple: (label: str, body: str), body 는 ``"\\n"`` join.
        Prerequisites:
            - 입력 text 가 ``\\n`` 라인 분리 가능. UTF-8 정상 디코딩 가정.
        Freshness:
            - 정적 정규식. SEC 양식 변경 무관 (KR 한정).
        Dataflow:
            - chunker / parser → 본 함수 → semanticTopicForLabel / applyProjections.
        TargetMarkets:
            - KR (DART) 정기보고서. 다른 언어 heading 패턴은 별도 함수 필요.

    Raises:
        없음.
    """
    lines = [line.rstrip() for line in text.splitlines()]
    segments: list[tuple[str, list[str]]] = []
    currentLabel = "(root)"
    currentLines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _RE_MAJOR_HEADING.match(stripped):
            if currentLines:
                segments.append((currentLabel, currentLines))
            currentLabel = stripped
            currentLines = []
            continue
        currentLines.append(stripped)

    if currentLines:
        segments.append((currentLabel, currentLines))

    return [(label, "\n".join(body).strip()) for label, body in segments if body]


def extractSemanticUnits(topic: str, text: str) -> list[tuple[str, str]]:
    """부문/리스크 topic의 텍스트를 의미 단위 (label, body) 쌍으로 추출한다.

    Args:
        topic: 인자.
        text: 인자.

    Raises:
        없음.

    Example:
        >>> extractSemanticUnits(...)

    Returns:
        <TODO: return desc> (list[tuple[str, str]])

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
    if topic in {"segmentOverview", "segmentFinancialSummary", "riskDerivative"}:
        return splitByMajorHeading(text)
    return []


def semanticTopicForLabel(topic: str, label: str) -> str | None:
    """sourceTopic + label 텍스트의 키워드 매칭으로 세분 semantic topic 판별.

    Capabilities:
        - ``_ATOMIC_SEMANTIC_TOPICS`` (segment*/리스크 17 개) 는 입력 topic 그대로 반환.
        - ``segmentOverview``/``segmentFinancialSummary`` 입력 → ``반도체/DS``/``DX/MX``/
          ``디지털미디어/VD``/``DA``/``디스플레이``/``하만/Harman``/``기타`` 키워드 매칭으로 7 세분 topic.
        - ``riskDerivative`` 입력 → ``시장위험``/``신용위험``/``유동성``/``자본``/``환위험``/
          ``금리위험``/``공정가치``/``파생상품`` 키워드 매칭으로 8 세분 topic.
        - 기타 topic → None.

    Args:
        topic: 상위 topic. ``segmentOverview``/``riskDerivative``/``segmentFinancialSummary``
            이외는 대부분 None.
        label: heading 텍스트 (``splitByMajorHeading`` 결과의 첫 요소).

    Returns:
        str | None — 세분 semantic topic ID. 매칭 없음 → None.

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import semanticTopicForLabel
        >>> semanticTopicForLabel("segmentOverview", "가. 반도체부문")
        'segmentSemiconductor'
        >>> semanticTopicForLabel("randomTopic", "label") is None
        True

    Guide:
        - "삼성전자 segment 별로 쪼개기" → ``splitByMajorHeading`` → 각 label 에 본 함수 적용.
        - "리스크 derivative 항목 분류" → ``topic="riskDerivative"`` 로 호출.
        - 회사가 삼성전자/하만 등 특정 segment 표기를 쓰지 않으면 None — caller fallback.

    SeeAlso:
        - ``semanticTopicForBlock`` — 본 함수 결과 None 시 block 본문/table cell 도 검사.
        - ``_ATOMIC_SEMANTIC_TOPICS`` (모듈 상수) — 세분 topic ID set.
        - ``extractSemanticUnits`` — 본 함수의 일반적 호출 컨텍스트.

    Requires:
        - 외부 dependency 없음 — 순수 키워드 매칭.

    AIContext:
        Workbench 가 "삼성전자 반도체 segment 실적" 질문 처리 시 sections 파이프 안에서 호출.
        키워드 매칭이 회사별 표기 (예 "Display Solutions" 아닌 "디스플레이") 에 의존 — 회사
        commenter (수동 등록) 가 잡지 못한 표기는 None. caller 가 None 결과를 "분류 불가"
        로 fallback 처리.

    LLM Specifications:
        AntiPatterns:
            - 매핑이 삼성전자 등 대형 segment 명에 편향. 중소형주 segment 표기는 미커버.
            - "반도체" 키워드가 본문 어디에든 있으면 매칭 → false positive 가능.
            - 키워드 우선순위 = 함수 안 if 순서. 동시 매칭 시 첫 매칭만.
        OutputSchema:
            - 1 스칼라. str | None.
        Prerequisites:
            - topic 입력이 정의된 6 범주 중 1 이어야 의미 있음 (나머지는 None).
        Freshness:
            - 정적 키워드 매핑. segment 표기 변화 (예 사명 변경) 시 본 함수 수정 필요.
        Dataflow:
            - splitByMajorHeading → 본 함수 → segment 단위 row 생성.
        TargetMarkets:
            - KR (DART) 한정. KR 대형주 위주 키워드 set.

    Raises:
        없음.
    """
    if topic in _ATOMIC_SEMANTIC_TOPICS:
        return topic
    joined = f"{topic}\n{label}"
    if topic in {"segmentOverview", "segmentFinancialSummary"}:
        if any(keyword in joined for keyword in ("반도체", "DS")):
            return "segmentSemiconductor"
        if any(keyword in joined for keyword in ("정보통신", "DX", "MX", "네트워크")):
            return "segmentIct"
        if any(keyword in joined for keyword in ("디지털미디어", "VD", "영상디스플레이")):
            return "segmentDigitalMedia"
        if any(keyword in joined for keyword in ("생활가전", "DA")):
            return "segmentHomeAppliance"
        if "디스플레이" in joined:
            return "segmentDisplay"
        if any(keyword in joined for keyword in ("하만", "Harman")):
            return "segmentHarman"
        if "기타" in joined:
            return "segmentOther"
        return None

    if topic == "riskDerivative":
        if "시장위험" in joined:
            return "marketRisk"
        if "신용위험" in joined:
            return "creditRisk"
        if "유동성위험" in joined:
            return "liquidityRisk"
        if "자본위험" in joined:
            return "capitalRisk"
        if any(keyword in joined for keyword in ("환위험", "환율")):
            return "fxRisk"
        if any(keyword in joined for keyword in ("금리위험", "이자율")):
            return "interestRateRisk"
        if "공정가치" in joined:
            return "fairValueRisk"
        if "파생상품" in joined:
            return "derivativeExposure"
        return None

    return None


def _tableLeadCells(tableText: str) -> list[str]:
    labels: list[str] = []
    for raw in tableText.splitlines():
        line = raw.strip()
        if not line.startswith("|") or _RE_TABLE_SEP.match(line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if not first or first in {"구분", "항목", "내용", "비고"}:
            continue
        labels.append(first)
    return labels


def semanticTopicForBlock(topic: str, label: str, blockType: str, blockText: str) -> str | None:
    """label과 블록 본문(테이블 셀 포함)을 종합하여 semantic topic을 판별한다.

    Args:
        topic: 인자.
        label: 인자.
        blockType: 인자.
        blockText: 인자.

    Raises:
        없음.

    Example:
        >>> semanticTopicForBlock(...)

    Returns:
        <TODO: return desc> (str | None)

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
    direct = semanticTopicForLabel(topic, label)
    if direct:
        return direct

    if blockType == "table":
        for cellLabel in _tableLeadCells(blockText):
            mapped = semanticTopicForLabel(topic, cellLabel)
            if mapped:
                return mapped

    joined = f"{label}\n{blockText}"
    if topic == "audit" and any(keyword in joined for keyword in ("감사의견", "감사인", "검토절차")):
        return "audit"
    if topic == "auditSystem" and any(
        keyword in joined for keyword in ("감사위원회", "내부감사", "내부회계", "준법지원인")
    ):
        return "auditSystem"
    if topic == "majorHolder" and any(keyword in joined for keyword in ("최대주주", "주식소유", "5%이상")):
        return "majorHolder"
    if topic == "environmentRegulation" and any(
        keyword in joined for keyword in ("환경", "배출권", "규제", "녹색경영")
    ):
        return "environmentRegulation"
    if topic == "majorContractsAndRnd" and any(keyword in joined for keyword in ("연구개발", "R&D", "주요계약")):
        return "majorContractsAndRnd"
    return None


def detailTopicForTopic(topic: str) -> str | None:
    """topic명이 부속명세서에 해당하면 detail topic을 반환한다.

    Args:
        topic: 인자.

    Raises:
        없음.

    Example:
        >>> detailTopicForTopic(...)

    Returns:
        <TODO: return desc> (str | None)

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
    return _DETAIL_TOPIC_MAP.get(topic)


def detailTopicForBlock(
    topic: str,
    sourceTopic: str,
    label: str,
    blockType: str,
    blockText: str,
) -> str | None:
    """topic + sourceTopic + label + block 본문/table cell 의 키워드 종합 부속명세서 분류.

    Capabilities:
        - 1 차 ``detailTopicForTopic`` lookup — topic 자체가 ``_DETAIL_TOPIC_MAP`` key 면 즉시 반환.
        - 2 차 candidates 묶음 (sourceTopic + label + blockText + table lead cells) 를 ``"\\n"`` join.
        - 3 차 topic 별 키워드 매칭 — ``productService`` 11 sub-topic / ``riskDerivative``/
          ``financialNotes``/``intellectualProperty``/``majorContractsAndRnd``/``salesOrder``/
          ``affiliateGroupDetail``/``audit``/``majorHolder``/``environmentRegulation`` 별 분류.
        - 4 차 ``_DETAIL_TOPIC_KEYWORDS`` (parserMapper 의 fallback 키워드 매핑) 검사 (audit/financialNotes 한정).
        - 매칭 없음 → None.

    Args:
        topic: 현 block 의 분류 후보 topic.
        sourceTopic: chunk 의 원 topic (분할/투영 전).
        label: heading 텍스트.
        blockType: ``"text"`` 또는 ``"table"`` — table 이면 lead cell 추가 검사.
        blockText: block 본문 (text 면 paragraph, table 이면 markdown table).

    Returns:
        str | None — detail topic ID (예 ``"trustBusinessDetail"``/``"derivativeProductDetail"``).
        매칭 없음 → None.

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import detailTopicForBlock
        >>> result = detailTopicForBlock("productService", "productService", "가. 신탁업무(상세)", "text", "본문")
        >>> result
        'trustBusinessDetail'
        >>> detailTopicForBlock("randomTopic", "src", "label", "text", "본문") is None
        True

    Guide:
        - "은행 신탁업무 부속명세서 분류" → ``productService`` topic + "신탁업무(상세)" 키워드.
        - "감사보수 부속명세 vs 재무제표 주석 부속명세 구분" → 본 함수가 둘을 분리.
        - "삼성그룹 계열사 상세 분류" → ``affiliateGroupDetail`` topic + "기업집단에소속된회사(상세)".

    SeeAlso:
        - ``detailTopicForTopic`` — 본 함수의 1 차 lookup 단계.
        - ``_DETAIL_TOPIC_KEYWORDS`` (parserMapper) — 4 차 fallback 매핑 SSOT.
        - ``_tableLeadCells`` (모듈 private) — table cell 추출 헬퍼.
        - ``semanticTopicForBlock`` — 부문/리스크 분류의 자매 함수.

    Requires:
        - dartlab.core.mappers.parserMapper — ``detailTopicMap`` + ``detailTopicKeywords`` source.
        - 외부 의존 없음 — 순수 키워드 매칭.

    AIContext:
        Workbench 가 "이 회사 사업의 내용 부속명세서 (상세) 항목" 질문 처리 시 sections 파이프
        에서 호출. 부속명세서 분류가 정밀하면 AI 답변이 정확 ("이 회사 신탁업무 부속명세서는
        이 표에 있다"). None 반환 = "분류 불가, 원본 chunk 그대로". caller 는 detail
        분류 실패를 사용자에게 노출 X (기본 topic 으로 fallback).

    LLM Specifications:
        AntiPatterns:
            - 키워드가 정확 일치 X (예 띄어쓰기 "신탁 업무(상세)") → 미매칭 → None. parserMapper
              의 키워드 등록 시 띄어쓰기 동시 등록 필요.
            - topic="audit" 인데 본문에 ``auditFeeDetail`` 키워드 등장 → 본 함수가 의도적으로
              ``auditFeeDetail`` 만 통과 (다른 detail 은 audit topic 과 무관하다고 판정).
            - blockType 이 "table" 외 (예 "list") → lead cell 검사 skip.
        OutputSchema:
            - 1 스칼라. str | None.
        Prerequisites:
            - ``loadSections()`` 결과의 ``detailTopicMap``/``detailTopicKeywords`` 가 채워져 있어야.
        Freshness:
            - parserMapper 의 키워드 매핑이 정기보고서 표기 변화 따라 갱신 — 본 함수 결과도 의존.
        Dataflow:
            - chunker → block → 본 함수 → sections row 의 detailTopic 필드.
        TargetMarkets:
            - KR (DART) 한정. 금융업/제조업/IT/유통업 다양 (productService 11 sub-topic 이 금융업
              위주, 다른 산업은 별 커버 X).

    Raises:
        없음.
    """
    direct = detailTopicForTopic(topic)
    if direct:
        return direct

    candidates = [sourceTopic, label, blockText]
    if blockType == "table":
        candidates.extend(_tableLeadCells(blockText))
    haystack = "\n".join(part for part in candidates if part)

    if topic == "productService":
        if "신탁업무(상세)" in haystack:
            return "trustBusinessDetail"
        if any(keyword in haystack for keyword in ("예금업무(상세)", "예금상품(상세)")):
            return "bankDepositProductDetail"
        if any(keyword in haystack for keyword in ("대출업무(상세)", "대출상품(상세)")):
            return "bankLoanProductDetail"
        if "신용카드상품(상세)" in haystack:
            return "cardProductDetail"
        if "상품및서비스개요(상세)" in haystack:
            return "financialProductOverviewDetail"
        if any(
            keyword in haystack for keyword in ("외환/수출입서비스(상세)", "e-금융서비스(상세)", "방카슈랑스(상세)")
        ):
            return "bankServiceDetail"
        if any(keyword in haystack for keyword in ("증권거래현황(상세)", "금융투자상품의위탁매매및수수료현황(상세)")):
            return "brokerageBusinessDetail"
        if any(keyword in haystack for keyword in ("투자운용인력현황(상세)", "투자일임업무-투자운용인력현황(상세)")):
            return "assetManagementStaffDetail"

    if topic == "riskDerivative" and any(
        keyword in haystack for keyword in ("장내파생상품거래현황(상세)", "신용파생상품상세명세(상세)")
    ):
        return "derivativeProductDetail"

    if topic == "financialNotes" and any(
        keyword in haystack for keyword in ("신탁업무-재무제표(상세)", "신탁업무재무제표(상세)")
    ):
        return "trustFinancialStatementDetail"

    if topic == "intellectualProperty" and any(
        keyword in haystack for keyword in ("지적재산권보유현황", "주요지적재산권현황")
    ):
        return "ipPortfolioDetail"

    if topic == "majorContractsAndRnd" and "연구개발실적(" in haystack:
        return "rndPortfolioDetail"

    if topic == "salesOrder" and any(keyword in haystack for keyword in ("수주상황(상세)", "수주현황(상세)")):
        return "orderBacklogDetail"

    if topic == "majorContractsAndRnd" and any(
        keyword in haystack for keyword in ("경영상의주요계약(상세)", "경영상의주요계약[상세]")
    ):
        return "majorContractDetail"

    if topic == "affiliateGroupDetail" and "기업집단에소속된회사(상세)" in haystack:
        return "affiliateCompanyDetail"

    if topic not in {"financialNotes", "audit"}:
        return None

    for detailTopic, keywords in _DETAIL_TOPIC_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            if topic == "audit" and detailTopic != "auditFeeDetail":
                continue
            if topic == "financialNotes" and detailTopic == "auditFeeDetail":
                continue
            return detailTopic
    return None


def _routeChapterIISegment(sourceTopic: str, label: str, body: str) -> str | None:
    joined = f"{label}\n{body}"
    if sourceTopic != _CHAPTER_II_SPLIT_SOURCE:
        return None
    if "원재료" in joined or "생산설비" in joined:
        return "rawMaterial"
    if "제품" in joined or "서비스" in joined:
        return "productService"
    return None


def applyProjections(
    rows: list[dict[str, object]],
    teacherTopics: dict[str, set[str]],
) -> list[dict[str, object]]:
    """chapter II 합산 topic 을 학습된 projection 규칙으로 개별 topic 에 분배한다.

    Capabilities:
        - ``loadProjectionRules("chapterII")`` 가 반환한 ``{sourceTopic: [targetTopic, ...]}``
          매핑으로 chapter II row 를 복제 분배.
        - ``주요제품및원재료등`` source 는 ``splitByMajorHeading`` 으로 본문 쪼개기 → 각
          segment 를 ``_routeChapterIISegment`` 키워드 매칭 (원재료/생산설비 → rawMaterial /
          제품/서비스 → productService) 로 분류 → 분류된 buffer 를 새 row 로 생성.
        - 분류 실패 segment 가 있어도 fallback 으로 ``rawMaterial`` / ``productService`` 양쪽에
          원본 전체 복제 (teacher 토픽 set 안에 있을 때 한정).
        - 일반 source → ``rules`` 가 명시한 target 으로 직접 row 복제 (sourceTopic/projectionKind
          메타 동행).
        - 이미 존재하는 ``(chapter, topic)`` 쌍은 skip (중복 방지).

    Args:
        rows: section rows. 각 row 는 ``chapter``/``topic``/``text``/``blockType``/``blockOrder``/
            ``majorNum``/``orderSeq`` 키 보유 (모두 optional 안전 처리).
        teacherTopics: ``chapterTeacherTopics`` 결과 — ``{chapter: {topic, ...}}``. 본 함수는
            ``teacherTopics["II"]`` 만 사용 (chapter II 한정 분배).

    Returns:
        list[dict[str, object]] — rows 복사본 + 새 분배 row 추가. 입력 rows 변형 X (immutable
        가드). projection 규칙이 비면 입력 그대로 반환.

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import applyProjections
        >>> rows = [{"chapter": "II", "topic": "X", "text": "ABC", "blockType": "text", "blockOrder": 0}]
        >>> result = applyProjections(rows, {"II": {"X"}})
        >>> len(result) >= 1
        True

    Guide:
        - "정기보고서 chapter II 의 합산 topic 을 개별 항목으로 분배" → 본 함수.
        - "삼성전자 사업의 내용 II 장 product/raw 분리" → ``주요제품및원재료등`` source 가 자동
          분할 (``splitByMajorHeading`` + 키워드 라우팅).
        - 분배 후 row 는 ``sourceTopic`` + ``projectionKind`` 메타로 추적 가능.

    SeeAlso:
        - ``chapterTeacherTopics`` — 본 함수가 받는 ``teacherTopics`` 의 source.
        - ``splitByMajorHeading`` — chapter II split source 의 본문 분할 헬퍼.
        - ``loadProjectionRules`` (artifacts) — projection 매핑 SSOT (학습된 규칙).
        - ``_routeChapterIISegment`` (모듈 private) — 분할 segment 의 키워드 라우팅 로직.

    Requires:
        - dartlab.providers.dart.docs.sections.artifacts.loadProjectionRules — 매핑 source.
        - 본 모듈 함수 ``splitByMajorHeading`` / ``_routeChapterIISegment`` — 분할/라우팅.

    AIContext:
        Workbench 가 "이 회사 사업의 내용 II 장 어떤 항목들" 질문 처리 시 sections 파이프 final
        step 으로 호출. 본 함수 없으면 chapter II 가 합산 topic 1 개로 뭉뜽그려져 AI 가
        세부 topic 별 검색 불가. ``projectionKind="directRule"``/``"headingRule"`` 메타로
        분배 출처 추적 → 잘못 분배된 row 는 사용자 검토 시 trace 가능.

    LLM Specifications:
        AntiPatterns:
            - projection 매핑 (parserMapper) 가 비어 있음 → 입력 rows 그대로 반환 (silent).
            - teacherTopics["II"] 가 비어 있음 → 분배 0 (모든 후보 skip).
            - ``주요제품및원재료등`` 본문이 segment 키워드 ("제품"/"원재료") 없음 → fallback
              으로 양쪽 target 에 동일 본문 복제 → 중복성 발생 (의도된 보수적 분배).
            - input rows 변형 X — 본 함수는 list copy 후 append (caller 의 다른 사용 안전).
        OutputSchema:
            - row: 입력 N + 분배 추가 K = N+K rows. K 는 projection 매핑 + 분할 결과 의존.
            - 새 row 의 필수 필드: chapter/topic/text/blockType/blockOrder/majorNum/orderSeq/
              sourceTopic/projectionKind.
        Prerequisites:
            - loadProjectionRules 가 정상 (parserMapper 학습된 매핑 보유).
            - teacherTopics 가 chapterTeacherTopics 결과로 채워짐.
        Freshness:
            - projection 매핑은 학습 (sectioning pipeline) 결과 — 학습 갱신 시 본 함수 결과 변화.
        Dataflow:
            - sections pipeline (chunker → mapper) → chapterTeacherTopics → 본 함수 → 최종 rows
              (sections.parquet).
        TargetMarkets:
            - KR (DART) 정기보고서 chapter II ("사업의 내용") 한정. III 장 이후는 분배 X.

    Raises:
        없음.
    """
    if not rows:
        return rows

    rules = loadProjectionRules("chapterII")
    if not rules:
        return rows

    out = list(rows)
    existing = {
        (row["chapter"], row["topic"])
        for row in rows
        if isinstance(row.get("chapter"), str) and isinstance(row.get("topic"), str)
    }
    splitBuffers: dict[tuple[str, str], list[str]] = {}

    for row in rows:
        chapter = row.get("chapter")
        topic = row.get("topic")
        text = row.get("text")
        if chapter != "II" or not isinstance(topic, str) or not isinstance(text, str):
            continue

        if topic == _CHAPTER_II_SPLIT_SOURCE:
            segments = splitByMajorHeading(text) or [("(root)", text)]
            matchedTargets: set[str] = set()
            for label, body in segments:
                target = _routeChapterIISegment(topic, label, body)
                if not target or target not in teacherTopics.get("II", set()):
                    continue
                splitBuffers.setdefault((chapter, target), []).append(body)
                matchedTargets.add(target)
            for target in _CHAPTER_II_SPLIT_FALLBACK_TARGETS:
                if target not in teacherTopics.get("II", set()) or target in matchedTargets:
                    continue
                splitBuffers.setdefault((chapter, target), []).append(text)
            continue

        for target in rules.get(topic, []):
            if target not in teacherTopics.get("II", set()):
                continue
            key = (chapter, target)
            if key in existing:
                continue
            out.append(
                {
                    "chapter": chapter,
                    "topic": target,
                    "text": text,
                    "blockType": row.get("blockType", "text"),
                    "blockOrder": row.get("blockOrder", 0),
                    "majorNum": row.get("majorNum"),
                    "orderSeq": row.get("orderSeq"),
                    "sourceTopic": topic,
                    "projectionKind": "directRule",
                }
            )
            existing.add(key)

    for (chapter, target), bodies in splitBuffers.items():
        key = (chapter, target)
        if key in existing or not bodies:
            continue
        out.append(
            {
                "chapter": chapter,
                "topic": target,
                "text": "\n".join(bodies),
                "blockType": "text",
                "blockOrder": 0,
                "majorNum": 2,
                "orderSeq": 0,
                "sourceTopic": _CHAPTER_II_SPLIT_SOURCE,
                "projectionKind": "headingRule",
            }
        )
        existing.add(key)

    return out
