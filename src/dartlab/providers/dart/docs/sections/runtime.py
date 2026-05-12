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
    """정수 장번호를 로마숫자 chapter 문자열로 변환한다.

    Args:
        majorNum: 인자.

    Raises:
        없음.

    Example:
        >>> chapterFromMajorNum(...)
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
    """
    rules = loadProjectionRules("chapterII")
    suppressed = set(rules.keys())
    suppressed.add(_CHAPTER_II_SPLIT_SOURCE)
    return {"II": suppressed}


def splitByMajorHeading(text: str) -> list[tuple[str, str]]:
    """텍스트를 '가. 나. 다.' 등 주요 heading 기준으로 (label, body) 쌍으로 분리한다.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> splitByMajorHeading(...)
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
    """
    if topic in {"segmentOverview", "segmentFinancialSummary", "riskDerivative"}:
        return splitByMajorHeading(text)
    return []


def semanticTopicForLabel(topic: str, label: str) -> str | None:
    """topic과 label 텍스트를 기반으로 세분화된 semantic topic을 판별한다.

    Args:
        topic: 인자.
        label: 인자.

    Raises:
        없음.

    Example:
        >>> semanticTopicForLabel(...)
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
    """
    return _DETAIL_TOPIC_MAP.get(topic)


def detailTopicForBlock(
    topic: str,
    sourceTopic: str,
    label: str,
    blockType: str,
    blockText: str,
) -> str | None:
    """topic/label/본문 키워드를 종합하여 부속명세서 detail topic을 판별한다.

    Args:
        topic: 인자.
        sourceTopic: 인자.
        label: 인자.
        blockType: 인자.
        blockText: 인자.

    Raises:
        없음.

    Example:
        >>> detailTopicForBlock(...)
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
    """chapter II 합산 topic을 학습된 projection 규칙으로 개별 topic에 분배한다.

    Args:
        rows: 인자.
        teacherTopics: 인자.

    Raises:
        없음.

    Example:
        >>> applyProjections(...)
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
