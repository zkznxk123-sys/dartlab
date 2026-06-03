"""iXBRL instance 파서 — primary HTML 의 inline facts + ``<xbrli:context>`` 해소 (자급).

DART 의 ``<TE ACODE ACONTEXT>`` 셀 추출 + ACONTEXT 디코드의 EDGAR 미러. 단 EDGAR 는 fact 가
``<ix:nonFraction name=us-gaap:X contextRef=…>`` 로 표시되고 기간·차원은 문서-전역 ``<xbrli:context>``
간접참조 → fact 추출 + context 해소를 **분리**한다. ``extractFacts`` = 본문 inline fact(concept·value·
contextRef), ``extractContexts`` = contextRef → (instant|start/end, dimension members).

LLM Specifications:
    AntiPatterns:
        - scale/sign 미적용 raw 텍스트 금지 — valueRaw 는 해소 numeric(scale×10^n, sign 적용).
        - nil fact 를 0 으로 금지 — "" (미공시).
        - context member 누락 금지 — explicitMember dimension→member 전부 수집(axisPath truth).
    OutputSchema:
        - ``extractFacts(html) -> list[dict]`` (concept/namespace/contextRef/unitRef/valueRaw/factType).
        - ``extractContexts(html) -> dict[str, dict]`` (ref → {instant|start/end, members}).
    Prerequisites:
        - 없음 (순수 regex 파싱).
    Freshness:
        - 순수 — 입력 HTML 외 의존 0.
    Dataflow:
        - html → ix:non* finditer(facts) + xbrli:context finditer(contexts 해소).
    TargetMarkets:
        - US (iXBRL inline us-gaap).
"""

from __future__ import annotations

import re

_FACT_RE = re.compile(
    r"<ix:non(fraction|numeric)\b([^>]*?)(?:/>|>(.*?)</ix:non(?:fraction|numeric)>)",
    re.IGNORECASE | re.DOTALL,
)
# prefix-optional — inline HTML(xbrli:)·EX-101.INS(무prefix) 양쪽 흡수.
_CONTEXT_RE = re.compile(
    r"<(?:\w+:)?context\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</(?:\w+:)?context>", re.IGNORECASE | re.DOTALL
)
_INSTANT_RE = re.compile(r"<(?:\w+:)?instant>\s*([0-9-]+)\s*</(?:\w+:)?instant>", re.IGNORECASE)
_START_RE = re.compile(r"<(?:\w+:)?startDate>\s*([0-9-]+)\s*</(?:\w+:)?startDate>", re.IGNORECASE)
_END_RE = re.compile(r"<(?:\w+:)?endDate>\s*([0-9-]+)\s*</(?:\w+:)?endDate>", re.IGNORECASE)
_MEMBER_RE = re.compile(
    r"<(?:\w+:)?(?:explicitMember|typedMember)\b[^>]*\bdimension=\"([^\"]+)\"[^>]*>([^<]*)</(?:\w+:)?", re.IGNORECASE
)
# EX-101.INS native fact — <ns:Concept contextRef=... unitRef=...>value</ns:Concept> (inline 아님).
_INSTANCE_FACT_RE = re.compile(r"<([A-Za-z][\w.-]*:[A-Za-z]\w*)\b([^>]*?)(?:/>|>([^<]*)</\1\s*>)", re.DOTALL)
_NS_SKIP = frozenset({"xbrli", "xbrldi", "link", "xlink", "xsi", "xsd", "xbrll", "iso4217"})
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _attr(tagAttrs: str, name: str) -> str | None:
    """tag 속성 문자열에서 ``name="..."`` 값 추출 (없으면 None)."""
    m = re.search(rf'\b{re.escape(name)}="([^"]*)"', tagAttrs, re.IGNORECASE)
    return m.group(1) if m else None


def _resolveValue(inner: str, *, sign: str | None, scale: str | None, nil: bool) -> str:
    """inner 텍스트 + sign/scale → 해소 numeric 문자열 (nil → "", companyfacts val 동치).

    iXBRL 규약: 표시값에 scale(×10^scale)·sign(음수) 별도 attribute. 본 함수가 적용해 실제 값을 낸다.
    괄호/△ 음수 표기도 흡수. 정수면 정수 문자열, 아니면 float 문자열.
    """
    if nil:
        return ""
    text = _WS_RE.sub("", _TAG_STRIP_RE.sub("", inner or ""))
    if not text:
        return ""
    neg = sign == "-"
    if text.startswith("(") and text.endswith(")"):
        neg = True
        text = text[1:-1]
    text = text.replace(",", "").replace("△", "-").replace("∆", "-").lstrip("+")
    try:
        val = float(text)
    except ValueError:
        return text  # 비-numeric (nonNumeric text fact)
    if scale:
        try:
            val *= 10 ** int(scale)
        except ValueError:
            pass
    if neg:
        val = -abs(val)
    return str(int(val)) if val == int(val) else repr(val)


def extractFacts(html: str) -> list[dict]:
    """primary HTML → inline fact list (concept·contextRef·해소 valueRaw).

    ``<ix:nonFraction>``(numeric) / ``<ix:nonNumeric>``(text) 전부 수집. concept 는 ``name`` 속성
    (예 "us-gaap:Revenues" → namespace="us-gaap", concept="Revenues").

    Args:
        html: primary iXBRL HTML.

    Returns:
        list[dict] — ``{concept, namespace, contextRef, unitRef, valueRaw, factType}``.

    Raises:
        없음.

    Example:
        >>> facts = extractFacts(html)  # doctest: +SKIP
        >>> facts[0]["concept"], facts[0]["contextRef"]  # doctest: +SKIP

    SeeAlso:
        - ``extractContexts`` — contextRef 해소.
        - ``cell.buildCells`` — facts×context×role → 셀.

    Requires:
        - 없음.

    Capabilities:
        - inline us-gaap fact 를 concept·기간참조·해소값으로 — DART TE 셀 추출 미러.

    Guide:
        - builder 가 호출. 순수.

    AIContext:
        - scale/sign 적용으로 valueRaw 는 실제 값(companyfacts 비교 가능).

    When:
        - 재무표 셀 분해 재료가 필요할 때.

    How:
        - ix:non* finditer → attr 추출 → _resolveValue.

    LLM Specifications:
        AntiPatterns:
            - 속성 순서 가정 금지 — name/contextRef 등 개별 regex.
        OutputSchema:
            - ``list[dict]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - html → ix finditer → fact dict.
        TargetMarkets:
            - US.
    """
    facts: list[dict] = []
    for m in _FACT_RE.finditer(html):
        kind = m.group(1).lower()
        attrs = m.group(2) or ""
        inner = m.group(3) or ""
        name = _attr(attrs, "name")
        ctxRef = _attr(attrs, "contextRef") or _attr(attrs, "contextref")
        if not name or not ctxRef:
            continue
        nil = (_attr(attrs, "xsi:nil") or _attr(attrs, "xs:nil") or _attr(attrs, "nil") or "").lower() == "true"
        ns, _, local = name.partition(":")
        if not local:
            ns, local = "", ns
        facts.append(
            {
                "concept": local,
                "namespace": ns,
                "contextRef": ctxRef,
                "unitRef": _attr(attrs, "unitRef") or _attr(attrs, "unitref"),
                "valueRaw": _resolveValue(inner, sign=_attr(attrs, "sign"), scale=_attr(attrs, "scale"), nil=nil),
                "factType": "numeric" if kind == "fraction" else "text",
            }
        )
    return facts


def extractInstanceFacts(insXml: str) -> list[dict]:
    """EX-101.INS(분리 instance) → native fact list (separate-instance era ≈2012~2020, inline 부재).

    inline 부재 era 의 필링은 facts 가 HTML 이 아니라 별도 ``EX-101.INS`` 에 native XBRL 원소
    (``<us-gaap:Assets contextRef=... unitRef=...>1234</us-gaap:Assets>``)로 있다. ``extractFacts``
    (inline ix:) 의 native 짝 — deep history 셀의 재료. context 는 ``extractContexts`` 가 INS 에도 동작
    (prefix-optional).

    Args:
        insXml: EX-101.INS instance document XML.

    Returns:
        list[dict] — ``extractFacts`` 와 동일 schema (concept/namespace/contextRef/unitRef/valueRaw/
        factType). numeric 만 (재무 셀). 빈 INS → [].

    Raises:
        없음.

    Example:
        >>> facts = extractInstanceFacts(insXml)  # doctest: +SKIP

    SeeAlso:
        - ``extractFacts`` — inline ix: 짝 (≈2021+).
        - ``cell.buildCells`` — 두 era facts 공통 소비.
    """
    if not insXml:
        return []
    facts: list[dict] = []
    for m in _INSTANCE_FACT_RE.finditer(insXml):
        tag = m.group(1)
        attrs = m.group(2) or ""
        inner = m.group(3) or ""
        ctxRef = _attr(attrs, "contextRef") or _attr(attrs, "contextref")
        if not ctxRef:
            continue
        ns, _, local = tag.partition(":")
        if ns.lower() in _NS_SKIP or not local:
            continue
        nil = (_attr(attrs, "xsi:nil") or _attr(attrs, "nil") or "").lower() == "true"
        value = _resolveValue(inner, sign=_attr(attrs, "sign"), scale=_attr(attrs, "scale"), nil=nil)
        # numeric 셀만 — 빈/비-numeric(텍스트 블록)은 제외.
        if value == "" or not _isNumeric(value):
            continue
        facts.append(
            {
                "concept": local,
                "namespace": ns,
                "contextRef": ctxRef,
                "unitRef": _attr(attrs, "unitRef") or _attr(attrs, "unitref"),
                "valueRaw": value,
                "factType": "numeric",
            }
        )
    return facts


def _isNumeric(s: str) -> bool:
    """문자열이 numeric 으로 파싱되는지 (native 텍스트 블록 fact 배제용)."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def extractContexts(html: str) -> dict[str, dict]:
    """primary HTML → ``contextRef → {instant|start/end, members}`` 해소 (DART ACONTEXT 디코드 미러).

    ``<xbrli:context>`` 블록 파싱: period(instant=시점 / start+end=기간) + dimension members
    (``<xbrldi:explicitMember dimension=AXIS>MEMBER``). DART ACONTEXT 토큰의 날짜·축 정보를 EDGAR 의
    명시 context 정의에서 추출.

    Args:
        html: primary iXBRL HTML.

    Returns:
        dict[str, dict] — ``ref → {"instant": str|None, "start": str|None, "end": str|None,
        "members": list[tuple[axis, member]]}``.

    Raises:
        없음.

    Example:
        >>> ctxs = extractContexts(html)  # doctest: +SKIP
        >>> ctxs["As_Of_5_31_2025_..."]["instant"]  # doctest: +SKIP
        '2025-05-31'

    SeeAlso:
        - ``mapper.contextToCell`` — 해소된 context → (ctxYear, ctxQuarter, ctxMode, ctxFlow, axisPath).

    Requires:
        - 없음.

    Capabilities:
        - contextRef 간접참조를 기간·차원으로 해소 — 셀의 period/axisPath truth.

    Guide:
        - builder 가 호출. 순수.

    AIContext:
        - dimension members = DART axisPath 대응. instant=BS 시점, duration=flow 기간.

    When:
        - fact 를 기간·차원에 묶을 때.

    How:
        - xbrli:context finditer → instant/start/end + explicitMember.

    LLM Specifications:
        AntiPatterns:
            - segment member 누락 금지 — 전 explicitMember 수집.
        OutputSchema:
            - ``dict[str, dict]``.
        Prerequisites:
            - 없음.
        Freshness:
            - 순수.
        Dataflow:
            - html → context finditer → 해소 dict.
        TargetMarkets:
            - US.
    """
    ctxs: dict[str, dict] = {}
    for m in _CONTEXT_RE.finditer(html):
        cid = m.group(1)
        body = m.group(2)
        inst = _INSTANT_RE.search(body)
        start = _START_RE.search(body)
        end = _END_RE.search(body)
        members = [(ax, mem.strip()) for ax, mem in _MEMBER_RE.findall(body)]
        ctxs[cid] = {
            "instant": inst.group(1) if inst else None,
            "start": start.group(1) if start else None,
            "end": end.group(1) if end else None,
            "members": members,
        }
    return ctxs
