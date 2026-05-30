"""DART 본문 XML 의 TABLE-GROUP ACLASS / TITLE / AASSOCNOTE 추출.

5 baseline 실측 (005930 2026Q1 zip):
    - 95 unique ACLASS / 95 TABLE-GROUP / 127 ATOCID-bearing TITLE
    - top-level: COVER / PB_VAL / {XBRL}BS_C / {XBRL}IS_C2 / {XBRL}IS_C3 /
                 {XBRL}EF_C / {XBRL}CF_C
    - nested (EF_C 안): {XBRL}NT_C_D810000 / D800600 / D822430 / D826380 등

LLM Specifications:
    AntiPatterns:
        - 텍스트 itertext concat 후 regex 로 ACLASS 추출 금지 — etree iter
          으로 element-level 직접 추출 (속도 + 정확도).
        - nested TABLE-GROUP skip 금지 — NT_C_D###### 가 각 주석 단위 entry,
          이게 핵심 cross-company canonical key.
        - DOCUMENT-NAME ACODE attribute 와 혼동 금지 — 본 스캐너는 TABLE-GROUP
          의 ACLASS 만.
    OutputSchema:
        - ``extractAclassEntries(xml: str) -> list[dict]`` 각 dict:
          ``rawId`` (str, "{XBRL}" prefix strip) / ``rawTitleCanonical`` (str) /
          ``parentRawId`` (str | None) / ``hasATOCID`` (bool, 신/옛 양식 판별).
    Prerequisites:
        - lxml. utf-8 decoded XML string.
    Freshness:
        - XML 양식 변경 시 5 baseline re-scan + count 비교.
    Dataflow:
        - xml string → lxml parse (recover=True) → BODY descendant 의
          TABLE-GROUP iter → ACLASS / TITLE / parent 추출.
    TargetMarkets:
        - KR (DART). 2023Q4+ ACLASS 박힘, ~2023Q3 ACLASS 없거나 다름.
"""

from __future__ import annotations

from typing import Iterator

from lxml import etree

from .titleNormalizer import normalizeTitle

_XBRL_PREFIX = "{XBRL}"


def _stripXbrlPrefix(aclass: str) -> str:
    """ACLASS attribute 의 ``{XBRL}`` namespace prefix 제거.

    Examples:
        >>> _stripXbrlPrefix("{XBRL}NT_C_D810000")
        'NT_C_D810000'
        >>> _stripXbrlPrefix("COVER")
        'COVER'
        >>> _stripXbrlPrefix("")
        ''
    """
    if aclass.startswith(_XBRL_PREFIX):
        return aclass[len(_XBRL_PREFIX) :]
    return aclass


def _titleOf(tg) -> str:
    """TABLE-GROUP element 의 직속 TITLE / HEAD/TITLE itertext.

    Args:
        tg: TABLE-GROUP lxml element.

    Returns:
        TITLE 의 itertext concat. 없으면 ``""``.

    NOTE:
        DART XML 의 TABLE-GROUP 구조 (005930 2026Q1 실측):
            <TABLE-GROUP ACLASS="{XBRL}NT_C_D810000">
              <TITLE ATOC="Y" ATOCID="572">1. 일반적 사항 (연결)</TITLE>
              <TABLE>...</TABLE>
              <P>...</P>
              ...
            </TABLE-GROUP>
    """
    title = tg.find("./TITLE")
    if title is None:
        title = tg.find("./HEAD/TITLE")
    if title is None:
        return ""
    return "".join(title.itertext()).strip()  # noqa: E501  # element.itertext OK


def _hasATOCID(root) -> bool:
    """본문에 ``<TITLE ATOCID>`` 존재 여부 = 양식 판별.

    Returns:
        True = 2023Q4+ 신 양식 (ATOCID 박힘).
        False = ~2023Q3 옛 양식 (AASSOCNOTE 만).
    """
    return root.find(".//TITLE[@ATOCID]") is not None


def iterTableGroups(root) -> Iterator[tuple[etree._Element, etree._Element | None]]:
    """root element 내 모든 TABLE-GROUP iter — (element, parent_tg or None).

    nested TABLE-GROUP 도 emit. parent_tg 가 None 이면 top-level.

    Args:
        root: lxml 의 root element (또는 BODY).

    Yields:
        ``(tg, parent_tg | None)`` — parent_tg 는 가장 가까운 ancestor TABLE-GROUP.
        없으면 None (top-level).

    Raises:
        없음 — lxml root 를 가정, iter/getparent 만 사용.

    Example:
        >>> for tg, parent in iterTableGroups(root):  # doctest: +SKIP
        ...     pass

    SeeAlso:
        - ``extractAclassEntries`` — 본 iter 로 ref entry 생산.

    Requires:
        - lxml.

    Capabilities:
        - nested 포함 전 TABLE-GROUP 열거 + parent 관계 → ACLASS 계층 추출.

    Guide:
        - extractAclassEntries 내부에서 호출 — 직접 호출 X.

    AIContext:
        - 순수 iter — tree 변경 0.

    LLM Specifications:
        AntiPatterns:
            - nested TABLE-GROUP skip 금지 — 주석 단위 entry 손실.
        OutputSchema:
            - ``Iterator[tuple[etree._Element, etree._Element | None]]``.
        Prerequisites:
            - lxml root.
        Freshness:
            - XML 양식 변경 시 검증.
        Dataflow:
            - root → iter("TABLE-GROUP") → ancestor TABLE-GROUP 탐색 → (tg, parent).
        TargetMarkets:
            - KR (DART).
    """
    # BODY 또는 root 어디든 동작. ancestor traversal 로 parent_tg 결정.
    for tg in root.iter("TABLE-GROUP"):
        parent = tg.getparent()
        while parent is not None and parent.tag != "TABLE-GROUP":
            parent = parent.getparent()
        yield tg, parent


def extractAclassEntries(xml: str) -> list[dict]:
    """본문 XML → TABLE-GROUP 단위 ref entry list.

    Args:
        xml: utf-8 decoded DART 본문 XML.

    Returns:
        각 TABLE-GROUP 에 대해:
            ``rawId`` (ACLASS attribute, "{XBRL}" prefix 제거)
            ``rawTitleRaw`` (TITLE itertext 원본, NFKC 적용 안 함)
            ``rawTitleCanonical`` (titleNormalizer.normalizeTitle 결과)
            ``parentRawId`` (parent TABLE-GROUP 의 rawId or None)
            ``hasATOCID`` (해당 TABLE-GROUP 의 TITLE 에 ATOCID 있는지)
            ``schemaEra`` ("v2" if ATOCID 박혀있음 else "v1")
        ACLASS 가 빈 entry 는 skip.

    Examples:
        >>> xml = '''<BODY><TABLE-GROUP ACLASS="{XBRL}EF_C">
        ...   <TITLE ATOCID="572">III. 재무</TITLE>
        ...   <TABLE-GROUP ACLASS="{XBRL}NT_C_D810000">
        ...     <TITLE ATOCID="573">1. 일반</TITLE>
        ...   </TABLE-GROUP>
        ... </TABLE-GROUP></BODY>'''
        >>> entries = extractAclassEntries(xml)
        >>> len(entries)
        2
        >>> entries[0]["rawId"], entries[0]["parentRawId"]
        ('EF_C', None)
        >>> entries[1]["rawId"], entries[1]["parentRawId"]
        ('NT_C_D810000', 'EF_C')

    Raises:
        없음 — XML parse 실패는 ``[]`` 반환.

    SeeAlso:
        - ``iterTableGroups`` — TABLE-GROUP 열거.
        - ``zipScanWorker.scanZipFiles`` — 본 entry 를 ref table 로 집계.

    Requires:
        - lxml. utf-8 decoded XML string.

    Capabilities:
        - 본문 ACLASS+TITLE truth 추출 → bridge-learning(회사간·세계마켓간) 입력 ref.

    Guide:
        - refScan 내부에서 호출 — 직접 호출 X.

    AIContext:
        - 데이터 추출 — 손수 regex 0, ACLASS attribute 직접.

    LLM Specifications:
        AntiPatterns:
            - XML parse 실패 시 raise 금지 — return [] (caller 가 skip 가능).
            - parent_tg 검색 시 ancestor chain 너무 깊이 가지 마라 — 보통
              2 단 (BODY > TABLE-GROUP > TABLE-GROUP). 더 깊으면 [추측] DART
              양식 위반 가능성.
        OutputSchema:
            - ``list[dict]`` 6 keys (rawId/rawTitleRaw/rawTitleCanonical/
              parentRawId/hasATOCID/schemaEra).
        Prerequisites:
            - lxml. utf-8 string.
        Freshness:
            - XML 양식 변경 시 hasATOCID detect rule 재검증.
        Dataflow:
            - xml → lxml parse → iterTableGroups → ACLASS/TITLE/parent 추출 → entry list.
        TargetMarkets:
            - KR (DART). EDGAR 는 별도.
    """
    if not xml:
        return []
    parser = etree.XMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(xml.encode("utf-8"), parser)
    except (etree.XMLSyntaxError, ValueError):
        return []
    if root is None:
        return []

    era = "v2" if _hasATOCID(root) else "v1"
    entries: list[dict] = []
    for tg, parent_tg in iterTableGroups(root):
        aclass = (tg.get("ACLASS", "") or "").strip()
        if not aclass:
            continue
        rawId = _stripXbrlPrefix(aclass)
        titleRaw = _titleOf(tg)
        titleCanonical = normalizeTitle(titleRaw)
        parentRawId: str | None = None
        if parent_tg is not None:
            parentAclass = (parent_tg.get("ACLASS", "") or "").strip()
            if parentAclass:
                parentRawId = _stripXbrlPrefix(parentAclass)
        titleEl = tg.find("./TITLE")
        if titleEl is None:
            titleEl = tg.find("./HEAD/TITLE")
        tgHasATOCID = titleEl is not None and bool(titleEl.get("ATOCID", "").strip())
        entries.append(
            {
                "rawId": rawId,
                "rawTitleRaw": titleRaw,
                "rawTitleCanonical": titleCanonical,
                "parentRawId": parentRawId,
                "hasATOCID": tgHasATOCID,
                "schemaEra": era,
            }
        )
    return entries
