"""iXBRL HTML 본문 walker — 서술 Item leaf + 재무제표 표 앵커링 (DART walker+leafSplit 미러).

DART walker(SECTION 구조 walk + leafSplit text/table 분리)의 EDGAR 미러. primary HTML 을 문서순서로
walk 하며 ``<table>`` = table leaf(중첩표는 바깥 1단위), 사이 텍스트 = text leaf 로 분리(blockOrder
보존). 재무제표 본표는 **statement role concept 커버리지 최대 표 1개**만 disclosureKey 앵커링
(BS/IS/CF/CIS/EF) — 같은 concept 을 일부 쓰는 note 표가 본표로 오앵커되지 않게(DART 의 표당 1 ACLASS
미러). 그 외 표·텍스트는 narrative(null). Item 헤딩 검출로 sectionLeaf 부여.

LLM Specifications:
    AntiPatterns:
        - 중첩 table 이중 emit 금지 — 최외곽 table 만(depth 가드).
        - note 표 본표 오앵커 금지 — statement 당 커버리지 최대 표 1개만(임계 가드).
        - read 표면 lxml import 금지 — 본 walker 는 build 전용(R2 무관).
    OutputSchema:
        - ``walkBody(html, *, formType, statementConcepts) -> list[dict]`` (보드 leaf 행).
        - ``buildStatementConcepts(roles) -> dict[str, set[str]]`` (statement → conceptKey set).
    Prerequisites:
        - lxml (build 전용).
    Freshness:
        - 순수 — 입력 외 의존 0.
    Dataflow:
        - html → iterwalk(text/table leaf) → 표 coverage → statement 당 best 표 앵커링.
    TargetMarkets:
        - US (iXBRL HTML 본문).
"""

from __future__ import annotations

import re

# 블록 앞부분 어디서든 "Item N. Title" 헤딩 검출(XBRL context/metadata 텍스트가 앞설 수 있어 비-anchor).
_ITEM_HEAD_RE = re.compile(r"\bitem\s+(\d+[A-Za-z]?)\b[\.\:\-–—\s]+([A-Za-z].{0,88})", re.IGNORECASE)
_FACT_NAME_RE = re.compile(r'name="([^"]+)"')
_WS_RE = re.compile(r"\s+")
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
# 본표 앵커 최소 커버리지 (note 표 오앵커 가드 — 본표는 수십 concept, note 는 소수).
_MIN_STMT_COVERAGE = 5


def _blockText(html: str) -> str:
    """블록 HTML → plain 텍스트 (태그 strip + 공백 정리, Item 헤딩 검출용)."""
    return _WS_RE.sub(" ", _TAG_STRIP_RE.sub(" ", html)).strip()


def buildStatementConcepts(roles: dict[str, list[dict]]) -> dict[str, set[str]]:
    """presentation roles → ``statement → {conceptKey}`` (본표 앵커 커버리지 기준).

    각 statement role(``roleToStatement`` 매치)의 concept 집합을 statement 별로 union. walker 가 표의
    concept ∩ 이 집합 크기로 본표 판정(커버리지). DART 의 표 ACLASS 의 EDGAR 미러(role 구조 기반).

    Args:
        roles: ``linkbase.parsePresentation`` 결과.

    Returns:
        dict — statement key → conceptKey set.

    Raises:
        없음.

    Example:
        >>> sc = buildStatementConcepts(roles)  # doctest: +SKIP
        >>> "us-gaap:Assets" in sc.get("BS", set())  # doctest: +SKIP
        True
    """
    from .mapper import roleToStatement

    out: dict[str, set[str]] = {}
    for roleUri, entries in roles.items():
        st = roleToStatement(roleUri)
        if not st:
            continue
        bucket = out.setdefault(st, set())
        for e in entries:
            bucket.add(e["conceptKey"])
    return out


def walkBody(html: str, *, formType: str, statementConcepts: dict[str, set[str]]) -> list[dict]:
    """primary HTML 본문 → 보드 leaf 행 (서술 text/table + 재무제표 앵커링, 문서순서).

    lxml HTMLParser(prolog strip, huge_tree)로 파싱 → iterwalk 로 ``<table>``(최외곽)=table leaf,
    사이 텍스트=text leaf. 표마다 statement 별 concept 커버리지 계산 → **statement 당 커버리지 최대 표
    1개**만 disclosureKey 앵커링(≥ ``_MIN_STMT_COVERAGE``), 나머지 null. Item 헤딩 검출로 sectionLeaf.

    Args:
        html: primary iXBRL HTML.
        formType: 폼 종류 (chapter).
        statementConcepts: ``buildStatementConcepts`` 결과.

    Returns:
        list[dict] — ``{chapter, sectionLeaf, sectionPath, blockLeaf, leafType, blockOrder,
        contentRaw, disclosureKey, xbrlClass}``. 파싱 실패 시 빈 list.

    Raises:
        없음.

    Example:
        >>> rows = walkBody(html, formType="10-K", statementConcepts=sc)  # doctest: +SKIP

    SeeAlso:
        - ``providers.dart.panel.build.walker.walkSections`` — DART analog.
        - ``buildStatementConcepts`` — 커버리지 기준.

    Requires:
        - lxml (build 전용).

    Capabilities:
        - 본문 text/table leaf 무손실 분리 + 재무제표 본표 1개씩 disclosureKey 앵커링(panel급 핵심).

    Guide:
        - builder 가 호출. lxml 은 build 전용(read 표면 lxml 0 유지).

    AIContext:
        - statement 당 best 표 1개 앵커 → note 표 오병합 0. blockOrder=문서순.

    When:
        - 필링 본문을 16-col 보드 행으로.

    How:
        - 파싱 → iterwalk leaf 수집(표 coverage) → statement 당 argmax 표 앵커 → 행.

    LLM Specifications:
        AntiPatterns:
            - note 표 본표 오앵커 금지(statement 당 1개). 중첩 table 이중 금지(depth).
        OutputSchema:
            - ``list[dict]``.
        Prerequisites:
            - lxml.
        Freshness:
            - 순수.
        Dataflow:
            - html → leaf 수집 → best 표 앵커.
        TargetMarkets:
            - US.
    """
    from lxml import etree

    from .mapper import canonicalItem

    cleaned = re.sub(r"^\s*<\?xml[^>]*\?>", "", html, count=1)
    parser = etree.HTMLParser(recover=True, huge_tree=True)
    try:
        root = etree.fromstring(cleaned, parser)
    except (etree.ParserError, etree.XMLSyntaxError, ValueError):
        return []
    if root is None:
        return []
    body = root.find("body")
    if body is None:
        body = root

    # 1차 수집 — leaf 블록(text/table). 표는 statement 별 coverage 동봉.
    blocks: list[dict] = []  # {leafType, contentRaw, sectionLeaf, blockLeaf, _cov:{stmt:int}}
    order = 0
    curItem = ""
    tableDepth = 0
    textBuf: list[str] = []

    def _emitText(content: str, sectionLeaf: str, blockLeaf: str) -> None:
        if content.strip():
            blocks.append(
                {
                    "leafType": "text",
                    "contentRaw": content.strip(),
                    "sectionLeaf": sectionLeaf,
                    "blockLeaf": blockLeaf,
                    "_cov": {},
                }
            )

    def _flushText() -> None:
        nonlocal curItem
        if not textBuf:
            return
        plain = _blockText(" ".join(textBuf))  # 공백 join — 텍스트노드 경계 보존(word boundary)
        textBuf.clear()
        if not plain:
            return
        # 블록 안 **모든** Item 헤딩으로 분할 — 한 블록에 다수 item 이 뭉치지 않게(섹션검색 c.panel("Risk") 정합).
        heads = list(_ITEM_HEAD_RE.finditer(plain))
        if not heads:
            _emitText(plain, curItem or formType, "")
            return
        if heads[0].start() > 0:  # preamble (첫 헤딩 앞) — 현재 item 귀속
            _emitText(plain[: heads[0].start()], curItem or formType, "")
        for i, h in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(plain)
            leaf, _ = canonicalItem(formType, plain[h.start() : h.start() + 100])
            curItem = leaf
            _emitText(plain[h.start() : end], leaf, leaf)

    for event, el in etree.iterwalk(body, events=("start", "end")):
        tag = (el.tag if isinstance(el.tag, str) else "").lower()
        if tag == "table":
            if event == "start":
                if tableDepth == 0:
                    _flushText()
                    tableHtml = etree.tostring(el, encoding="unicode", method="html")
                    concepts = set(_FACT_NAME_RE.findall(tableHtml))
                    cov = {st: len(concepts & cs) for st, cs in statementConcepts.items()}
                    blocks.append(
                        {
                            "leafType": "table",
                            "contentRaw": tableHtml,
                            "sectionLeaf": curItem or formType,
                            "blockLeaf": "",
                            "_cov": cov,
                        }
                    )
                tableDepth += 1
            else:
                tableDepth = max(0, tableDepth - 1)
            continue
        if ":" in tag:
            continue  # xbrli:/ix:/xbrldi: XBRL 메타데이터 — 본문 텍스트 아님(context 식별자·날짜 등 제외)
        if tableDepth > 0:
            continue  # 표 내부는 atomic (별도 emit 0)
        if event == "start":
            if el.text and el.text.strip():
                textBuf.append(el.text)
        else:
            if el.tail and el.tail.strip():
                textBuf.append(el.tail)
    _flushText()

    # 2차 — statement 당 커버리지 최대 table 1개 앵커링(note 표 오병합 가드).
    bestForStmt: dict[str, tuple[int, int]] = {}  # stmt → (blockIdx, coverage)
    for idx, b in enumerate(blocks):
        if b["leafType"] != "table":
            continue
        for st, c in b["_cov"].items():
            if c < _MIN_STMT_COVERAGE:
                continue
            if st not in bestForStmt or c > bestForStmt[st][1]:
                bestForStmt[st] = (idx, c)
    anchored: dict[int, str] = {idx: st for st, (idx, _c) in bestForStmt.items()}

    rows: list[dict] = []
    for idx, b in enumerate(blocks):
        stmt = anchored.get(idx)
        sectionLeaf = stmt if stmt else b["sectionLeaf"]
        rows.append(
            {
                "chapter": formType,
                "sectionLeaf": sectionLeaf,
                "sectionPath": f"{formType}␟{sectionLeaf}",
                "blockLeaf": (stmt or b["blockLeaf"]),
                "leafType": b["leafType"],
                "blockOrder": idx,
                "contentRaw": b["contentRaw"],
                "disclosureKey": stmt,
                "xbrlClass": None,
            }
        )
    return rows
