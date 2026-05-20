from __future__ import annotations

import hashlib
import html
import re
from functools import lru_cache
from typing import Any, Literal

from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle, stripSectionPrefix

TextNodeType = Literal["heading", "body"]

_MULTISPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[\s\-–—:：;,]+$")
_RE_ROMAN = re.compile(r"^(?:[IVXivx]+)\.\s+(.+)$")
_RE_NUMERIC = re.compile(r"^(?:\d+)\.\s+(.+)$")
_RE_KOREAN = re.compile(r"^(?:[가-힣])\.\s+(.+)$")
_RE_PAREN_NUM = re.compile(r"^\((\d+)\)\s*(.+)$")
_RE_PAREN_KOR = re.compile(r"^\(([가-힣])\)\s*(.+)$")
_RE_CIRCLED = re.compile(r"^([①-⑳])\s*(.+)$")
_RE_BRACKET = re.compile(r"^\[(.+?)\]$|^【(.+?)】$")
_RE_SHORT_PAREN = re.compile(r"^\(([^)]+)\)$")
_RE_HEADING_NOISE = re.compile(
    r"^(?:"
    r"단위|주\d|참고|출처|비고"
    r"|계속|전문|요약|이하\s*여백"
    r"|연결|별도|연결기준|별도기준"
    r"|첨부|주석\s*참조"
    r")\b"
)
_RE_NONWORD = re.compile(r"[^0-9A-Za-z가-힣]+")
_RE_TEMPORAL_MARKER = re.compile(
    r"^(?:"
    r"\d{4}년(?:\s*\d{1,2}월(?:\s*\d{1,2}일)?)?"
    r"|\d{4}[./]\d{1,2}(?:[./]\d{1,2})?"
    r"|제\s*\d+\s*기(?:\s*\d*\s*분기)?"
    r"|(?:당|전|전전)(?:기|반기|분기)"
    r"|\d{4}년\s*(?:\d분기|상반기|하반기)"
    r"|FY\s*\d{4}"
    r")$"
)
_RE_SUFFIX_EGWANHAN = re.compile(r"에관한사항$")

_TOPIC_SEGMENT_ALIASES: dict[str, dict[str, str]] = {
    "companyOverview": {
        "연결대상종속기업개황": "연결대상종속사현황",
        "연결대상종속회사개황": "연결대상종속사현황",
        "연결대상종속기업현황": "연결대상종속사현황",
        "연결대상종속회사현황": "연결대상종속사현황",
        "연결대상종속회사현황요약": "연결대상종속사현황",
        "연결대상종속회사개황요약": "연결대상종속사현황",
        "연결대상종속기업개황요약": "연결대상종속사현황",
        "연결대상종속기업현황요약": "연결대상종속사현황",
        "연결대상회사의변동내용": "연결대상변동내용",
        "연결대상회사의변동현황": "연결대상변동내용",
        "당기중종속기업변동내용": "연결대상변동내용",
        "당기연결대상회사의변동내용": "연결대상변동내용",
        "본사의주소전화번호및홈페이지": "본사의주소전화번호홈페이지",
        "본사의주소전화번호및홈페이지주소": "본사의주소전화번호홈페이지",
        "본사의주소전화번호홈페이지주소": "본사의주소전화번호홈페이지",
    },
    "businessOverview": {
        "생산및설비에관한사항": "생산및설비",
        "매출에관한사항": "매출",
        "주요원재료에관한사항": "주요원재료",
        "영업의개황등": "영업현황",
        "국내외시장여건등": "시장여건",
        "산업의특성등": "산업의특성",
        "사업부문별현황": "사업부문현황",
    },
    "mdna": {
        "재무상태및영업실적연결기준": "재무상태및영업실적",
        "조직개편": "조직변경",
        "조직의변경": "조직변경",
        "조직변경등": "조직변경",
        "자산손상인식": "자산손상",
        "유동성및자금조달과지출": "유동성및자금조달",
        "환율변동영향": "환율변동",
    },
    "auditSystem": {
        "감사위원회에관한사항": "감사위원회",
        "감사위원회의위원의독립성": "감사위원회위원의독립성",
        "감사위원회의주요활동내역": "감사위원회주요활동내역",
        "준법지원인등지원조직현황": "준법지원인지원조직현황",
    },
}


_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;?|&#\d+;?")

# parquet 본문 줄바꿈 누락 복원 — DART HTML→parquet 변환 시 일부 회사 (현대모비스/
# 하나금융/신한지주 등) 의 본문 줄바꿈 정보 손실. 한국어 종결사 ("입니다.", "습니다.",
# "표기합니다." 등) 후 *한 글자 한글 + . + 공백/한글* (heading prefix) 가 이어지면
# 줄바꿈 삽입. 의례적 종결사 매칭 — false positive 최소화.
_RE_LINE_BREAK_REPAIR = re.compile(r"(?<=니다\.)(?=[가-힣]\.[\s가-힣])")


def _repairLineBreaks(text: str) -> str:
    return _RE_LINE_BREAK_REPAIR.sub("\n", text)


def _cleanLine(line: str) -> str:
    # HTML entity \ub514\ucf54\ub4dc \u2014 DART \uc6d0\ubb38\uc5d0 `&cr`, `&cr;&cr` \uac19\uc740 raw entity \uac00 \ub0a8\uc544
    # textPath / segmentKey \uc624\uc5fc\uc2dc\ud0a4\ub294 \ud68c\uadc0 \ucc28\ub2e8. html.unescape \ub294 \ud45c\uc900 entity
    # \ub514\ucf54\ub4dc, raw `&cr` (named entity \uc544\ub2d8) \uc740 \ubcc4\ub3c4 strip.
    decoded = html.unescape(line)
    decoded = _HTML_ENTITY_RE.sub("", decoded)
    return decoded.replace("\u00a0", " ").replace("\t", " ").rstrip()


@lru_cache(maxsize=2048)
def _normalizeHeadingText(text: str) -> str:
    cleaned = stripSectionPrefix(text.strip())
    cleaned = cleaned.strip("[]【】")
    m = _RE_SHORT_PAREN.match(cleaned)
    if m:
        cleaned = m.group(1).strip()
    cleaned = cleaned.replace("ㆍ", "·")
    cleaned = _MULTISPACE_RE.sub(" ", cleaned)
    cleaned = _TRAILING_PUNCT_RE.sub("", cleaned)
    return cleaned.strip()


@lru_cache(maxsize=2048)
def _headingKey(text: str) -> str:
    normalized = _normalizeHeadingText(text)
    normalized = normalized.replace("·", "").replace("ㆍ", "")
    normalized = _RE_NONWORD.sub("", normalized)
    return normalized.strip()


def _canonicalHeadingKey(
    labelText: str,
    labelKey: str,
    *,
    level: int,
    topic: str | None,
) -> str:
    if level <= 3 and isinstance(topic, str) and topic:
        mapped = mapSectionTitle(labelText)
        if mapped == topic:
            return f"@topic:{topic}"
    return labelKey


@lru_cache(maxsize=4096)
def _semanticSegmentKey(labelKey: str, *, topic: str | None) -> str:
    if not labelKey or labelKey.startswith("@"):
        return labelKey

    key = labelKey

    aliasMap = _TOPIC_SEGMENT_ALIASES.get(str(topic or ""), {})
    if key in aliasMap:
        key = aliasMap[key]

    key = _RE_SUFFIX_EGWANHAN.sub("", key)
    key = key.replace("종속기업", "종속사").replace("종속회사", "종속사")

    if isinstance(topic, str) and topic == "businessOverview":
        key = key.replace("영업의개황", "영업현황")
    if isinstance(topic, str) and topic == "mdna":
        key = key.replace("환율변동영향", "환율변동")

    return key


@lru_cache(maxsize=512)
def _isTemporalMarker(text: str) -> bool:
    normalized = _normalizeHeadingText(text)
    return bool(_RE_TEMPORAL_MARKER.fullmatch(normalized))


@lru_cache(maxsize=8192)
def _bodyAnchor(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "empty"
    anchor = normalized[:96]
    return hashlib.blake2b(anchor.encode("utf-8"), digest_size=8).hexdigest()[:12]


_LABEL_CLOSING_NOUNS = (
    "개황",
    "사항",
    "내역",
    "내용",
    "현황",
    "여부",
    "개요",
    "연혁",
    "이력",
    "구성",
    "변동",
    "변경",
    "특징",
    "구조",
    "체계",
    "기준",
    "방침",
    "정책",
    "결과",
    "분석",
    "동향",
    "전망",
    "계획",
    "성과",
    "진척",
    "수준",
    "추이",
    "명칭",
    "기간",
    "주소",
    "번호",
    "주요",
    "소재지",
    "홈페이지",
    "사업부문",
    "보유현황",
)
_RE_INLINE_PAREN_NUM = re.compile(r"(?<=\s)(?=\(\d+\)\s)")
_RE_INLINE_PAREN_KOR = re.compile(r"(?<=\s)(?=\([가-힣]\)\s)")
_RE_INLINE_KOR_DASH_NUM = re.compile(r"(?<!^)(?=[가-힣]-\d+\.)")
_RE_LINE_HEAD_KOREAN = re.compile(r"^[가-힣]\.\s+(.+)$")
_RE_LINE_HEAD_NUMERIC = re.compile(r"^\d+\.\s+(.+)$")


def _splitInlineMultiHeading(line: str) -> list[str]:
    """한 줄 안 multi-heading split — 반복 적용으로 N 개 prefix 모두 분리."""
    parts = [line]
    for _ in range(20):  # iteration limit
        newParts: list[str] = []
        changed = False
        for p in parts:
            sub = _splitInlineMultiHeadingOnce(p)
            if len(sub) > 1:
                changed = True
            newParts.extend(sub)
        parts = newParts
        if not changed:
            break
    return parts


def _splitInlineMultiHeadingOnce(line: str) -> list[str]:
    """한 줄 안 multi-heading prefix split.

    DART parquet 본문이 일부 회사 (하나금융/신한지주/현대모비스 등) 에서 한 줄에 여러
    heading prefix 가 줄바꿈 없이 박혀 있음. sections layer 가 정규화 책임 — split 처리.

    잡는 패턴:
      - "공백 + (1) " / "공백 + (가) " → split (case 2 — 하나금융)
      - "한글-숫자." (가-1./나-2./...) → split (case 3 — 신한지주)
      - 한글/numeric heading label 의 *알려진 closing 명사* 직후 한글 단어 시작 → split
        (case 1 — 현대모비스 "개황연결대상...")

    Args:
        line: 본문 한 줄 (stripped).

    Returns:
        list[str] — split 된 sub-line 들. split 없으면 [line].
    """
    if not line or line.startswith("|") or len(line) < 10:
        return [line]

    positions: set[int] = {0}
    for pat in (_RE_INLINE_PAREN_NUM, _RE_INLINE_PAREN_KOR, _RE_INLINE_KOR_DASH_NUM):
        for m in pat.finditer(line):
            if m.start() > 0:
                positions.add(m.start())

    # case 1 — 한글/numeric heading 의 closing 명사 + 한글 단어 시작 (공백 없이도)
    head_match = _RE_LINE_HEAD_KOREAN.match(line) or _RE_LINE_HEAD_NUMERIC.match(line)
    if head_match:
        labelPart = head_match.group(1)
        labelStart = line.index(labelPart)
        # label 안 closing 명사의 *모든 위치* 검사 (rfind 단일 위치는 본문 안 같은 명사
        # repeat 시 false positive — 예: "본사의 주소, 전화번호, 홈페이지 주소법인 ...
        # 본점 주소지는..." 의 "주소" rfind 가 "주소지" 잡음). 첫 valid 위치 (다음
        # 글자 한글 + 잔여 5자 이상) 만 split — 본문 순서 보존 + iterative loop 가
        # 후속 split 처리.
        bestSplitPos: int | None = None
        for noun in _LABEL_CLOSING_NOUNS:
            for m in re.finditer(re.escape(noun), labelPart):
                idx = m.start()
                afterNoun = idx + len(noun)
                if afterNoun >= len(labelPart):
                    continue
                nextChar = labelPart[afterNoun]
                if not ("가" <= nextChar <= "힣"):
                    continue
                rest = labelPart[afterNoun:]
                if len(rest) < 5:
                    continue
                candidatePos = labelStart + afterNoun
                if bestSplitPos is None or candidatePos < bestSplitPos:
                    bestSplitPos = candidatePos
                break  # 이 명사의 첫 valid 위치만
        if bestSplitPos is not None:
            positions.add(bestSplitPos)

    if len(positions) <= 1:
        return [line]
    sorted_pos = sorted(positions)
    sorted_pos.append(len(line))
    parts: list[str] = []
    for a, b in zip(sorted_pos[:-1], sorted_pos[1:]):
        seg = line[a:b].strip()
        if seg:
            parts.append(seg)
    return parts or [line]


@lru_cache(maxsize=16384)
def _detectHeading(line: str) -> tuple[int, str, bool] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("|"):
        return None
    if len(stripped) > 120:
        return None

    # level 매핑 — 작을수록 root 권위. DART 정기보고서 본문 위계:
    #   Roman "I."     = 챕터 (level 1, top)
    #   Numeric "1."   = 섹션 (level 2)
    #   Korean "가."   = 서브섹션 (level 3)
    #   Paren "(1)"    = 서브-서브 (level 4)
    #   Paren "(가)"   = level 5
    #   Circled ①     = level 5
    #   Short paren   = level 6 (인라인 마커)
    #   Bracket "[X]"  = level 7 (표 caption / 인라인 anchor — 최하위)
    # 이전 매핑은 bracket=1 (top) 이라 표 caption 이 chapter 권위로 stack 비워
    # ancestor chain 깨졌음. semantic 회복 — bracket 을 가장 깊은 level 로.
    m = _RE_ROMAN.match(stripped)
    if m:
        return (1, m.group(1).strip(), True)

    m = _RE_NUMERIC.match(stripped)
    if m:
        return (2, m.group(1).strip(), True)

    m = _RE_KOREAN.match(stripped)
    if m:
        return (3, m.group(1).strip(), True)

    m = _RE_PAREN_NUM.match(stripped)
    if m:
        return (4, m.group(2).strip(), True)

    m = _RE_PAREN_KOR.match(stripped)
    if m:
        return (5, m.group(2).strip(), True)

    m = _RE_CIRCLED.match(stripped)
    if m:
        return (5, m.group(2).strip(), True)

    m = _RE_SHORT_PAREN.match(stripped)
    if m:
        inner = m.group(1).strip()
        if inner and len(inner) <= 48 and not _RE_HEADING_NOISE.match(inner):
            structural = not _isTemporalMarker(inner)
            return (6, inner, structural)

    m = _RE_BRACKET.match(stripped)
    if m:
        text = m.group(1) or m.group(2) or ""
        structural = not _isTemporalMarker(text)
        return (7, text.strip(), structural)

    return None


def parseTextStructureWithState(
    text: str,
    *,
    sourceBlockOrder: int,
    topic: str | None = None,
    initialHeadings: list[dict[str, Any]] | None = None,
    promoteKorean: bool | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, Any]], bool]:
    """텍스트를 소제목 계층 구조로 파싱하고, 최종 heading stack도 함께 반환한다.

    Args:
        text: 인자.
        sourceBlockOrder: 인자.
        topic: 인자.
        initialHeadings: 인자.

    Raises:
        없음.

    Example:
        >>> parseTextStructureWithState(...)

    Returns:
        tuple[list[dict], list[dict]] — (노드, 엣지) 페어.

    SeeAlso:
        - ``mapper`` / ``runtime`` — sections 분석 호출자.

    Requires:
        - dartlab
        - functools
        - hashlib

    Capabilities:
        - sections 본문 텍스트 → 노드 (heading/body) 분류 + 정규식 패턴 매칭.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal text structure — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections runtime/analysis 위임.
        OutputSchema:
            - dict / str / list — 함수별.
        Prerequisites:
            - sections 본문 텍스트.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - text → 정규식 매칭 → 노드 분류 (heading/body) → 결과.
        TargetMarkets:
            - KR (DART) sections text structure.
    """
    nodes: list[dict[str, object]] = []
    stack: list[dict[str, object]] = [dict(item) for item in (initialHeadings or [])]
    bodyLines: list[str] = []
    segmentOrder = 0

    def flushBody() -> None:
        """flushBody — TODO 한국어 동작 설명.

        Raises:
            없음.

        Example:
            >>> flushBody(...)

        SeeAlso:
            - ``mapper`` / ``runtime`` — sections 호출자.

        Requires:
            - dartlab
            - functools
            - hashlib

        Capabilities:
            - sections 본문 텍스트 → 노드 분류 + 정규식 매칭.

        Guide:
            - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

        AIContext:
            internal text structure — AI 직접 호출 X.
        """
        nonlocal bodyLines, segmentOrder
        body = "\n".join(bodyLines).strip()
        bodyLines = []
        if not body:
            return

        pathLabels = [str(item["label"]) for item in stack]
        pathKeys = [str(item["key"]) for item in stack if str(item["key"])]
        semanticPathKeys = [str(item["semanticKey"]) for item in stack if str(item["semanticKey"])]
        pathText = " > ".join(pathLabels) if pathLabels else None
        pathKey = " > ".join(pathKeys) if pathKeys else None
        parentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
        semanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
        semanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
        level = int(stack[-1]["level"]) if stack else 0
        anchor = _bodyAnchor(body)
        # Text row identity should follow outline path first.
        # Raw coarse block order is preserved separately as sourceBlockOrder.
        stableKeyBase = f"body|p:{semanticPathKey}" if semanticPathKey else f"body|lv:{level}|a:{anchor}"
        nodes.append(
            {
                "textNodeType": "body",
                "textStructural": True,
                "textLevel": level,
                "textPath": pathText,
                "textPathKey": pathKey,
                "textParentPathKey": parentPathKey,
                "textSemanticPathKey": semanticPathKey,
                "textSemanticParentPathKey": semanticParentPathKey,
                "segmentOrder": segmentOrder,
                "segmentKeyBase": stableKeyBase,
                "text": body,
            }
        )
        segmentOrder += 1

    # parquet 본문 줄바꿈 누락 회사 (현대모비스 등) — 한국어 종결사 후 한글 heading
    # prefix 등장 시 줄바꿈 복원. 정규화 후 line 단위 처리.
    text = _repairLineBreaks(text)
    rawLines = text.splitlines()
    splitLines: list[str] = []
    for rawLine in rawLines:
        cleaned = _cleanLine(rawLine)
        s = cleaned.strip()
        if not s:
            splitLines.append("")
            continue
        # parquet 본문 줄바꿈 누락 회사 (하나금융/신한지주/현대모비스 등) 정규화 —
        # 한 줄 안 multi-heading prefix 를 별 line 으로 분리.
        splitLines.extend(_splitInlineMultiHeading(s))

    # chunk 내 위계 추론 — 첫 detected heading 의 prefix 가 한글이면 한글이 contextual
    # root, numeric "1./2." 는 한글의 child (level 4) 로 강등. DART 본문 위계 표준
    # (numeric > 한글) 이 비표준 본문 (현대차/LG/삼성물산 등 "가. ... / 1. ...
    # sub-numbering" 구조) 에서 역전되어 후속 한글 sibling 들이 numeric 의 sub 로
    # 박히는 회귀 차단. Roman 은 항상 chapter top 이라 강등 대상 X.
    # promoteKorean 파라미터: None = chunk 첫 heading 으로 결정, True/False = 강제
    # (topic-level sticky). expansion.py 가 topic 단위 sticky 보관.
    effectivePromoteKorean: bool
    if promoteKorean is None:
        effectivePromoteKorean = False
        for s in splitLines:
            if not s:
                continue
            h = _detectHeading(s)
            if h is None:
                continue
            firstLevel = h[0]
            if firstLevel == 3:  # 한글이 chunk root
                effectivePromoteKorean = True
            break  # 첫 heading 만 봄
    else:
        effectivePromoteKorean = bool(promoteKorean)

    for stripped in splitLines:
        if not stripped:
            if bodyLines:
                bodyLines.append("")
            continue

        heading = _detectHeading(stripped)
        if heading is None:
            bodyLines.append(stripped)
            continue

        flushBody()
        level, label, structural = heading
        # 한글 contextual root chunk 안 numeric heading → 한글 (level 3) 의 child (4)
        if effectivePromoteKorean and level == 2:
            level = 4
        labelText = _normalizeHeadingText(label)
        labelKey = _headingKey(label)
        stackKey = _canonicalHeadingKey(labelText, labelKey, level=level, topic=topic)
        semanticStackKey = _semanticSegmentKey(stackKey, topic=topic)
        # @topic alias 가 stack 의 *어느 위치든* 중복이면 alias marker 처리.
        # 이전 룰은 stack[-1] 만 검사 → 다른 heading 사이에 끼인 같은 @topic alias 가
        # stack 깊은 위치에 살아있어도 다시 push 되어 "@topic > X > @topic" 같은
        # 누적 chain 발생. semantic 위배. stack 전체 검사로 차단.
        redundantTopicAlias = (
            structural
            and bool(stack)
            and str(stackKey).startswith("@topic:")
            and any(str(item["key"]) == stackKey for item in stack)
        )

        if structural and not redundantTopicAlias:
            while stack and int(stack[-1]["level"]) >= level:
                stack.pop()
            stack.append({"level": level, "label": labelText, "key": stackKey, "semanticKey": semanticStackKey})
            pathLabels = [str(item["label"]) for item in stack]
            pathKeys = [str(item["key"]) for item in stack if str(item["key"])]
            semanticPathKeys = [str(item["semanticKey"]) for item in stack if str(item["semanticKey"])]
            pathText = " > ".join(pathLabels) if pathLabels else None
            pathKey = " > ".join(pathKeys) if pathKeys else None
            parentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
            semanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
            semanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
            segmentKeyBase = f"heading|lv:{level}|p:{semanticPathKey or semanticStackKey}"
        else:
            # redundantTopicAlias 인 경우 — 같은 @topic alias 의 sibling heading.
            # stack 의 해당 entry label 을 latest 로 갱신 → 자식 heading 들 textPath 에 형제
            # 위치의 정확한 label 반영. 예: 가/나/다/라 가 모두 같은 @topic:companyOverview
            # alias 일 때 마지막 들어온 라의 label 이 stack 에 들어가야 다음 [DX 부문] 의
            # textPath="라. 주요 사업의 내용 > DX 부문" 으로 정확. 회귀 사례 — 갱신
            # 없으면 stack 의 첫 push 가의 label 이 그대로 유지되어 [DX] textPath 가
            # "가. 회사의 법적·상업적 명칭 > DX" 로 misattribute.
            if redundantTopicAlias:
                for item in stack:
                    if str(item["key"]) == stackKey:
                        item["label"] = labelText
                        break
            currentPathKeys = [str(item["key"]) for item in stack if str(item["key"])]
            currentSemanticPathKeys = [str(item["semanticKey"]) for item in stack if str(item["semanticKey"])]
            pathText = labelText
            keyPrefix = "@alias" if redundantTopicAlias else "@marker"
            pathKey = f"{keyPrefix}:{labelKey}"
            parentPathKey = " > ".join(currentPathKeys) if currentPathKeys else None
            semanticPathKey = pathKey
            semanticParentPathKey = " > ".join(currentSemanticPathKeys) if currentSemanticPathKeys else None
            segmentKind = "alias" if redundantTopicAlias else "marker"
            segmentKeyBase = f"heading|{segmentKind}|lv:{level}|p:{pathKey}"
        nodes.append(
            {
                "textNodeType": "heading",
                "textStructural": structural and not redundantTopicAlias,
                "textLevel": level,
                "textPath": pathText,
                "textPathKey": pathKey,
                "textParentPathKey": parentPathKey,
                "textSemanticPathKey": semanticPathKey,
                "textSemanticParentPathKey": semanticParentPathKey,
                "segmentOrder": segmentOrder,
                "segmentKeyBase": segmentKeyBase,
                "text": stripped,
            }
        )
        segmentOrder += 1

    flushBody()
    return nodes, [dict(item) for item in stack], effectivePromoteKorean


def parseTextStructure(
    text: str,
    *,
    sourceBlockOrder: int,
    topic: str | None = None,
) -> list[dict[str, object]]:
    """텍스트를 소제목 계층 구조로 파싱하여 노드 리스트를 반환한다.

    Args:
        text: 인자.
        sourceBlockOrder: 인자.
        topic: 인자.

    Raises:
        없음.

    Example:
        >>> parseTextStructure(...)

    Returns:
        list[dict] — 결과 dict 리스트.

    SeeAlso:
        - ``mapper`` / ``runtime`` — sections 분석 호출자.

    Requires:
        - dartlab
        - functools
        - hashlib

    Capabilities:
        - sections 본문 텍스트 → 노드 (heading/body) 분류 + 정규식 패턴 매칭.

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal text structure — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections runtime/analysis 위임.
        OutputSchema:
            - dict / str / list — 함수별.
        Prerequisites:
            - sections 본문 텍스트.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - text → 정규식 매칭 → 노드 분류 (heading/body) → 결과.
        TargetMarkets:
            - KR (DART) sections text structure.
    """
    nodes, _stack, _promote = parseTextStructureWithState(text, sourceBlockOrder=sourceBlockOrder, topic=topic)
    return nodes


__all__ = ["TextNodeType", "parseTextStructure", "parseTextStructureWithState"]
