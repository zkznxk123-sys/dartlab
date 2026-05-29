"""sections row walker — 손실 0 + 중복 0 정공법.

알고리즘:
    1. container = SECTION-N + wrapper TABLE-GROUP (nested TABLE-GROUP 보유).
    2. emit 대상 = container 의 직속 자식 중 container 가 아닌 element.
       (SECTION-N / wrapper TABLE-GROUP / TITLE / HEAD 본인은 emit X)
    3. contentRaw = etree.tostring 그대로 (P/SPAN/USERMARK/TABLE/COLSPAN/data-*
       모든 태그 100% 보존).
    4. xbrlClass — TABLE-GROUP 만:
       - v2/v1.5 ACLASS 있으면 직접 사용
       - v1 (ACLASS 없음) 옛 양식: ref table token Jaccard 매칭
    5. P / TABLE / IMAGE / PGBRK / 기타 narrative = xbrlClass null.

원칙 (사용자 요구 #5/#6 + memory/feedback_no_content_plain_precompute):
    - 원본 본문 100% 보존 (raw XML tag string 단일 columnar 정렬)
    - 가공 0 (content_plain 류 derive 컬럼 신설 금지)
    - 손실 0 (emit 안 한 leaf element 없음)
    - 중복 0 (같은 element 두 번 emit 금지)

LLM Specifications:
    AntiPatterns:
        - TABLE-GROUP 만 emit 금지 — narrative P / TABLE / IMAGE 동일 권리.
        - wrapper TABLE-GROUP 의 직속 자식 (preamble P 등) 누락 금지 — wrapper
          는 container 로 동작해 자식 단위 emit.
        - 같은 element 를 walker 이중 호출로 emit 중복 금지.
        - SECTION-N stack 추적 시 ancestor 만 사용 — descendant 검사 금지.
    OutputSchema:
        - ``walkSections(root, era, refDf) -> iter[dict]`` 10 col row.
        - cols: chapter / sectionLeaf / blockLeaf / xbrlClass / xbrlMatched /
                xbrlMatchScore / atocId / aassocnote / contentRaw / blockOrder.
    Prerequisites:
        - lxml etree root. refDf (v1/v1.5 fuzzy match 용).
    Freshness:
        - DART XML 양식 변경 시 wrapper TABLE-GROUP 감지 룰 재검증.
    Dataflow:
        - root → 1pass wrapper 식별 → iterwalk → emit 조건 만족 시 row yield.
    TargetMarkets:
        - KR (DART). EDGAR 는 별도 walker.
"""

from __future__ import annotations

import re
from typing import Iterator

import polars as pl
from lxml import etree

from dartlab.filings.dart.build.refScan.aclassExtractor import (
    _hasATOCID,
    _stripXbrlPrefix,
)
from dartlab.filings.dart.build.refScan.refMatcher import matchToRef
from dartlab.filings.dart.build.refScan.titleNormalizer import (
    normalizeTitle,
)

_MULTISPACE_RE = re.compile(r"\s+")


def detectSchemaEra(root) -> str:
    """양식 자동 감지.

    Returns:
        ``"v2"`` = 2023Q4+ 신 양식 (ATOCID 박힘).
        ``"v1.5"`` = ACLASS 있는 옛 양식.
        ``"v1"`` = AASSOCNOTE only (~2015~2023Q3).

    Examples:
        >>> from lxml import etree
        >>> root = etree.fromstring(b'<BODY><TITLE ATOCID="3">Hi</TITLE></BODY>')
        >>> detectSchemaEra(root)
        'v2'
    """
    if _hasATOCID(root):
        return "v2"
    if root.find(".//TABLE-GROUP[@ACLASS]") is not None:
        return "v1.5"
    return "v1"


def _titleText(el) -> str:
    """element 의 itertext concat + multispace 정리."""
    if el is None:
        return ""
    raw = "".join(el.itertext()).strip()
    return _MULTISPACE_RE.sub(" ", raw)


def _findTitle(tg) -> "etree._Element | None":
    """TABLE-GROUP / SECTION-N 의 직속 TITLE element."""
    titleEl = tg.find("./TITLE")
    if titleEl is None:
        titleEl = tg.find("./HEAD/TITLE")
    return titleEl


def _isWrapperTableGroup(tg: "etree._Element") -> bool:
    """TABLE-GROUP 가 wrapper (nested TABLE-GROUP 보유) 인지."""
    for desc in tg.iter("TABLE-GROUP"):
        if desc is tg:
            continue
        return True
    return False


_CONTAINER_MARK = "_dlContainer"  # attribute key — emit 제외 마커
_TABLE_OPAQUE_TAGS = {"TABLE"}  # TABLE 안의 SECTION/TG 는 rogue (XML 구조 이상)


def _hasTableAncestor(el) -> bool:
    """element 가 TABLE 후손인지 — XML 구조 이상으로 nested 된 SECTION-N 식별용."""
    cur = el.getparent()
    while cur is not None:
        if isinstance(cur.tag, str) and cur.tag in _TABLE_OPAQUE_TAGS:
            return True
        cur = cur.getparent()
    return False


def _markContainers(root) -> None:
    """container = subtree 에 SECTION-N 또는 wrapper TABLE-GROUP 가 있는 element.

    Boundary = SECTION-N + wrapper TG (자식 TG 보유). 이들 + 모든 ancestor 가 container.
    BODY / DOCUMENT 같은 root wrapper 도 자동으로 container 가 되어 emit 제외.

    구현 note: ``id(element)`` 는 lxml 의 동일 element 라도 iter 호출마다 wrapper
    객체가 새로 생성되어 불안정 → element attribute 로 mark (안정).
    """
    # 1단계 — boundary (SECTION-N + wrapper TG) 마킹.
    # TABLE 내부 (rogue) SECTION-N / wrapper TG 는 제외 — XML 구조 이상이라 외부
    # TABLE 의 1 row 로 통째 emit (그 안 contentRaw 에 포함).
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.startswith("SECTION-"):
            if _hasTableAncestor(el):
                continue  # rogue
            el.set(_CONTAINER_MARK, "1")
        elif el.tag == "TABLE-GROUP" and _isWrapperTableGroup(el):
            if _hasTableAncestor(el):
                continue  # rogue
            el.set(_CONTAINER_MARK, "1")
    # 2단계 — boundary 의 모든 ancestor 도 마킹 (BODY / DOCUMENT 자동 포함).
    # TABLE 만나면 차단 (TABLE 은 container 안 되고 1 row 로 emit).
    for el in root.iter():
        if el.get(_CONTAINER_MARK) == "1":
            cur = el.getparent()
            while cur is not None:
                if cur.get(_CONTAINER_MARK) == "1":
                    break
                if isinstance(cur.tag, str) and cur.tag in _TABLE_OPAQUE_TAGS:
                    break  # TABLE 차단
                cur.set(_CONTAINER_MARK, "1")
                cur = cur.getparent()
    # 3단계 — root 자체도 container (BODY/DOCUMENT 가 SECTION-N 포함 시 이미 마킹됐지만 보장).
    root.set(_CONTAINER_MARK, "1")


def _unmarkContainers(root) -> None:
    """emit 후 attribute 청소 — contentRaw 에 잔재 방지 (안전망)."""
    for el in root.iter():
        if isinstance(el.tag, str):
            if el.get(_CONTAINER_MARK) is not None:
                del el.attrib[_CONTAINER_MARK]


def walkSections(
    root,
    era: str,
    refDf: pl.DataFrame | None = None,
    *,
    matchThreshold: float = 0.70,
) -> Iterator[dict]:
    """root → leaf content unit row iterator (손실 0 / 중복 0).

    "Leaf content unit" 정의:
        parent 가 container (SECTION-N 또는 wrapper TABLE-GROUP) 이고
        본인은 container 가 아닌 element. TITLE / HEAD 도 제외.

    Args:
        root: lxml etree root (BODY 또는 DOCUMENT).
        era: "v2" / "v1.5" / "v1" (detectSchemaEra 결과).
        refDf: Layer 1 ref table (옛 양식 fuzzy match 용).
        matchThreshold: fuzzy match Jaccard threshold (검증 0.70).

    Yields:
        row dict (10 keys, schema 동결):
            chapter, sectionLeaf, blockLeaf, xbrlClass, xbrlMatched,
            xbrlMatchScore, atocId, aassocnote, blockOrder, contentRaw.
    """
    # 1-pass — container attribute mark (SECTION-N / wrapper TG / 그 ancestor).
    _markContainers(root)

    chapterStack: list[str] = []  # 현재 SECTION-N TITLE stack
    blockOrder = 0

    for evt, el in etree.iterwalk(root, events=("start", "end")):
        if not isinstance(el.tag, str):
            continue
        tag = el.tag

        # SECTION-N — stack push/pop, emit 안 함.
        # rogue (TABLE 안 nested) SECTION-N 은 stack 무시 — 외부 TABLE 의 contentRaw 통째 보존.
        if tag.startswith("SECTION-"):
            if el.get(_CONTAINER_MARK) == "1":
                if evt == "start":
                    titleEl = _findTitle(el)
                    chapterStack.append(_titleText(titleEl))
                else:
                    if chapterStack:
                        chapterStack.pop()
            continue

        # 본 사이클은 end event 에서만 처리 (top-down 순서 보존).
        if evt != "end":
            continue

        # TITLE / HEAD 도 emit — raw element 보존 원칙. chapter / sectionLeaf 컬럼은
        # 메타데이터 (SECTION-N stack 추적), TITLE 자체는 row 콘텐츠.

        # container 본인은 emit 안 함 (wrapper TG / BODY / DOCUMENT / 그 외 ancestor).
        if el.get(_CONTAINER_MARK) == "1":
            continue

        # emit 조건: parent 가 container 여야 함.
        parent = el.getparent()
        if parent is None:
            continue
        if parent.get(_CONTAINER_MARK) != "1":
            continue

        # row 빌드.
        xbrlClass: str | None = None
        xbrlMatched = False
        xbrlMatchScore: float = 0.0
        atocId = ""
        aassocnote = ""
        blockLeaf = ""

        if tag == "TABLE-GROUP":
            # leaf TABLE-GROUP (wrapper 가 아님 — 위에서 이미 wrapper continue).
            acls = (el.get("ACLASS", "") or "").strip()
            titleEl = _findTitle(el)
            titleRaw = _titleText(titleEl)
            atocId = (titleEl.get("ATOCID", "") if titleEl is not None else "") or ""
            aassocnote = (el.get("AASSOCNOTE", "") or "").strip()
            blockLeaf = normalizeTitle(titleRaw)

            if acls:
                xbrlClass = _stripXbrlPrefix(acls)
                xbrlMatched = True
                xbrlMatchScore = 1.0
            elif era != "v2" and refDf is not None and not refDf.is_empty() and titleRaw:
                matched, score = matchToRef(titleRaw, refDf, threshold=matchThreshold)
                if matched is not None:
                    xbrlClass = matched
                    xbrlMatched = False  # fuzzy flag
                    xbrlMatchScore = score

        chapter = chapterStack[0] if chapterStack else ""
        sectionLeaf = chapterStack[-1] if chapterStack else ""

        try:
            contentRaw = etree.tostring(el, encoding="unicode")
        except (ValueError, TypeError):
            contentRaw = ""
        if not contentRaw.strip():
            continue

        yield {
            "chapter": chapter,
            "sectionLeaf": sectionLeaf,
            "blockLeaf": blockLeaf,
            "xbrlClass": xbrlClass,
            "xbrlMatched": xbrlMatched,
            "xbrlMatchScore": xbrlMatchScore,
            "atocId": atocId,
            "aassocnote": aassocnote,
            "blockOrder": blockOrder,
            "contentRaw": contentRaw,
        }
        blockOrder += 1
