"""XBRL 링크베이스 파서 — EX-101.PRE(presentation 구조) + EX-101.LAB(라벨) (자급).

DART 의 ACLASS(정부 발행 Link Role, 재무제표 구조 identity)의 EDGAR 미러. EDGAR 는 presentation
linkbase 의 ``<presentationLink xlink:role="…role URI…">`` 이 재무제표를 정의 — role URI 가 어떤
statement(BS/IS/CF)인지, 그 안 concept 순서·계층을 담는다. ``parsePresentation`` 이
role→ordered concepts 를, ``parseLabels`` 가 concept→라벨을 추출. 둘 다 ``.txt`` 안 EX-101 블록에서
자급(전 history, 네트워크 0).

LLM Specifications:
    AntiPatterns:
        - lxml 네임스페이스 가정 금지 — link:/default prefix 양쪽 regex 흡수.
        - arc order 무시 금지 — presentationArc order 로 concept 표시순(cellOrder) 결정.
    OutputSchema:
        - ``parsePresentation(xml) -> dict[str, list[dict]]`` (roleURI → [{conceptKey, concept, order}]).
        - ``parseLabels(xml) -> dict[str, str]`` (conceptKey → 대표 라벨).
    Prerequisites:
        - 없음 (순수 regex 파싱).
    Freshness:
        - 순수.
    Dataflow:
        - EX-101.PRE → presentationLink/loc/arc → role→concept 순서. EX-101.LAB → loc/arc/label chain.
    TargetMarkets:
        - US (XBRL 2.1 linkbase).
"""

from __future__ import annotations

import re

_PRES_LINK_RE = re.compile(
    r"<(?:\w+:)?presentationLink\b[^>]*\brole=\"([^\"]+)\"[^>]*>(.*?)</(?:\w+:)?presentationLink>",
    re.IGNORECASE | re.DOTALL,
)
_LOC_TAG_RE = re.compile(r"<(?:\w+:)?loc\b([^>]*)/?>", re.IGNORECASE)
_PRES_ARC_RE = re.compile(r"<(?:\w+:)?presentationArc\b([^>]*)/?>", re.IGNORECASE)
_LABEL_ARC_RE = re.compile(r"<(?:\w+:)?labelArc\b([^>]*)/?>", re.IGNORECASE)
_LABEL_RE = re.compile(
    r"<(?:\w+:)?label\b([^>]*\brole=\"([^\"]+)\"[^>]*)>(.*?)</(?:\w+:)?label>", re.IGNORECASE | re.DOTALL
)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_STD_LABEL_ROLE = "http://www.xbrl.org/2003/role/label"


def _arcAttr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{re.escape(name)}="([^"]*)"', attrs, re.IGNORECASE)
    return m.group(1) if m else None


def _locAttrs(body: str) -> dict[str, str]:
    """linkbase loc 태그들 → ``xlink:label`` label to href fragment map.

    SEC 파일은 ``xlink:label``/``xlink:href`` 순서가 일정하지 않으므로 태그 속성 문자열에서
    개별 attr 를 해소한다.
    """
    out: dict[str, str] = {}
    for m in _LOC_TAG_RE.finditer(body):
        attrs = m.group(1) or ""
        label = _arcAttr(attrs, "label")
        href = _arcAttr(attrs, "href")
        if not label or not href or "#" not in href:
            continue
        out[label] = href.rsplit("#", 1)[-1]
    return out


def _fragmentToConcept(fragment: str) -> tuple[str, str]:
    """링크베이스 href fragment ("us-gaap_Assets") → (ns, local) ("us-gaap","Assets")."""
    ns, _, local = fragment.partition("_")
    return (ns, local) if local else ("", ns)


def parsePresentation(xml: str) -> dict[str, list[dict]]:
    """EX-101.PRE → ``roleURI → [{conceptKey, concept, order}]`` (표시순).

    각 ``<presentationLink role=URI>`` 의 loc(label→concept) + presentationArc(from/to/order)를 엮어
    role 별 concept 순서 리스트 산출. role URI 가 statement 식별(mapper.roleToStatement), order 가 cellOrder.

    Args:
        xml: EX-101.PRE presentation linkbase XML.

    Returns:
        dict — ``roleURI → [{"conceptKey": "us-gaap:Assets", "concept": "Assets", "order": float}]``
        (order 정렬).

    Raises:
        없음 — 빈/파싱불가 role 은 skip.

    Example:
        >>> roles = parsePresentation(preXml)  # doctest: +SKIP
        >>> any("BalanceSheet" in r for r in roles)  # doctest: +SKIP
        True

    SeeAlso:
        - ``mapper.roleToStatement`` — roleURI → BS/IS/CF/CIS/EF.
        - ``walker.buildStatementConcepts`` — role concept 순서로 보드 앵커링.

    Requires:
        - 없음.

    Capabilities:
        - 재무제표 구조(role→concept 순서)를 링크베이스에서 — DART ACLASS 구조 identity 미러.

    Guide:
        - builder 가 호출. 순수.

    AIContext:
        - regex 로 prefix 무관 파싱. concept 미등장(loc 부재) arc 는 skip.

    When:
        - 재무표 셀의 statement 귀속·표시순이 필요할 때.

    How:
        - presentationLink 별 loc map + arc 정렬 → concept 순서.

    LLM Specifications:
        AntiPatterns:
            - 동일 role 다중 link 병합 누락 금지 — role 키로 누적.
        OutputSchema:
            - ``dict[str, list[dict]]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - PRE → link/loc/arc → role→concept.
        TargetMarkets:
            - US.
    """
    roles: dict[str, list[dict]] = {}
    for lm in _PRES_LINK_RE.finditer(xml):
        roleUri = lm.group(1)
        body = lm.group(2)
        locMap = _locAttrs(body)
        entries: list[dict] = []
        seen: set[str] = set()
        for am in _PRES_ARC_RE.finditer(body):
            attrs = am.group(1)
            toLabel = _arcAttr(attrs, "to")
            if not toLabel or toLabel not in locMap:
                continue
            frag = locMap[toLabel]
            ns, local = _fragmentToConcept(frag)
            conceptKey = f"{ns}:{local}" if ns else local
            if conceptKey in seen:
                continue
            seen.add(conceptKey)
            orderStr = _arcAttr(attrs, "order")
            try:
                order = float(orderStr) if orderStr else 0.0
            except ValueError:
                order = 0.0
            entries.append({"conceptKey": conceptKey, "concept": local, "order": order})
        if entries:
            entries.sort(key=lambda e: e["order"])
            roles.setdefault(roleUri, []).extend(entries)
    return roles


def parseLabels(xml: str) -> dict[str, str]:
    """EX-101.LAB → ``conceptKey → 대표 라벨`` (loc→labelArc→label chain, standard label 우선).

    Args:
        xml: EX-101.LAB label linkbase XML.

    Returns:
        dict — ``conceptKey("us-gaap:Assets") → label("Total assets")``. 표준 label role 우선,
        없으면 첫 라벨. 미해소 concept 은 부재(호출측 concept local-name fallback).

    Raises:
        없음.

    Example:
        >>> labels = parseLabels(labXml)  # doctest: +SKIP
        >>> labels.get("us-gaap:Assets")  # doctest: +SKIP
        'Total assets'

    SeeAlso:
        - ``parsePresentation`` — presentation role 구조.

    Requires:
        - 없음.

    Capabilities:
        - concept 인간 라벨 추출.

    Guide:
        - builder 가 호출. 순수. 라벨은 best-effort(미해소 fallback).

    AIContext:
        - loc(label→concept) → labelArc(from→to) → label(role,text) 3단 chain.

    When:
        - 셀 label 표시명이 필요할 때.

    How:
        - loc/labelArc/label 파싱 → chain → conceptKey→text(standard role 우선).

    LLM Specifications:
        AntiPatterns:
            - 비표준 라벨 role 무조건 채택 금지 — standard label 우선.
        OutputSchema:
            - ``dict[str, str]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - LAB → loc/arc/label chain → conceptKey→label.
        TargetMarkets:
            - US.
    """
    # loc: locLabel → conceptKey
    locToConcept: dict[str, str] = {}
    for label, frag in _locAttrs(xml).items():
        ns, local = _fragmentToConcept(frag)
        locToConcept[label] = f"{ns}:{local}" if ns else local
    # labelArc: locLabel(from) → labelResLabel(to)
    arcFromTo: list[tuple[str, str]] = []
    for am in _LABEL_ARC_RE.finditer(xml):
        attrs = am.group(1)
        fr = _arcAttr(attrs, "from")
        to = _arcAttr(attrs, "to")
        if fr and to:
            arcFromTo.append((fr, to))
    # label: labelResLabel → (role, text)
    labelRes: dict[str, list[tuple[str, str]]] = {}
    for m in _LABEL_RE.finditer(xml):
        attrs = m.group(1)
        role = m.group(2)
        text = _WS_RE.sub(" ", _TAG_STRIP_RE.sub("", m.group(3) or "")).strip()
        lbl = _arcAttr(attrs, "label")
        if lbl and text:
            labelRes.setdefault(lbl, []).append((role, text))
    out: dict[str, str] = {}
    for fr, to in arcFromTo:
        conceptKey = locToConcept.get(fr)
        cands = labelRes.get(to)
        if not conceptKey or not cands:
            continue
        std = next((t for r, t in cands if r == _STD_LABEL_ROLE), None)
        chosen = std or cands[0][1]
        out.setdefault(conceptKey, chosen)
    return out
