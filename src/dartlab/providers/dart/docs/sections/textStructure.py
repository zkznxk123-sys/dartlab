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
# 한글 heading prefix — 한 글자 + . 다음 공백 *optional*. 한국콜마 같이 "가.연결대상..."
# 처럼 parquet 본문에서 공백 없이 박힌 경우도 매칭. closing 명사 split 이 후속 분리.
_RE_KOREAN = re.compile(r"^(?:[가-힣])\.\s*(.+)$")
_RE_PAREN_NUM = re.compile(r"^\((\d+)\)\s*(.+)$")
_RE_PAREN_KOR = re.compile(r"^\(([가-힣])\)\s*(.+)$")
_RE_CIRCLED = re.compile(r"^([①-⑳])\s*(.+)$")
_RE_BRACKET = re.compile(r"^\[(.+?)\]$|^【(.+?)】$")
_RE_SHORT_PAREN = re.compile(r"^\(([^)]+)\)$")
# ▣ / ▶ / ◈ — DART 정기보고서 본문 안 회사명/카테고리 sub-section marker.
# 옛 룰 _RE_HEADING_NOISE 가 ◆/■ 같은 marker 제외하지 않아 본문 첫 한 줄이 heading
# 으로 잡힐 위험은 단어 길이 제한 (≤ 60) + 한글-only 정의로 mitigate.
_RE_BULLET_MARKER = re.compile(r"^[▣▶◈]\s*(.+)$")
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
        "연결대상회사의당기중변동내용": "연결대상변동내용",
        "당기중연결대상회사의변동내용": "연결대상변동내용",
        "당기중연결대상회사의변동현황": "연결대상변동내용",
        "당기연결대상회사의변동현황": "연결대상변동내용",
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


# bracket caption 안 period-variable 부분 strip — date + 회사수 suffix.
# 회귀 사례 (000660 companyOverview "기업집단에 소속된 회사" bracket):
#   "기업집단에소속된회사 20171231 기준계열사 95개사" (95 사)
#   "기업집단에소속된회사 20181231 기준계열사 100개사" (100 사)
#   ...
# 모두 같은 의미 bracket 인데 date + 회사수 가 period 마다 변동 → path period-locked.
# semantic key 에서 strip.
_RE_PERIOD_DATE = re.compile(r"\d{8}|\d{4}\d{0,4}기준|\d{4}[\.\-/]\d{1,2}[\.\-/]\d{1,2}")
_RE_COUNT_SUFFIX = re.compile(r"\d+개사?")


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
    # period-variable date + 회사수 strip
    key = _RE_PERIOD_DATE.sub("", key)
    key = _RE_COUNT_SUFFIX.sub("", key)

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
    # "주요" 제거 — modifier 로 자주 쓰임 ("주요 사업의 내용", "주요 계약"). closing noun
    # 로 split 시 "바. 주요 사업의 내용" → "바. 주요" + "사업의 내용" 의 부적절 truncation.
    "소재지",
    "홈페이지",
    "사업부문",
    "보유현황",
)
# split positions — *공백 또는 닫는 괄호 또는 한글* 후 paren marker (\d+) / (한글) 시리즈
# 시작. 아모레/롯데쇼핑/한화생명 같이 "...100 (한강로2가)(2) 전화번호..." 처럼 `)(2)`
# 공백 없이 이어진 본문 안 multi-marker split.
# 한국 법인격 약자 — heading prefix 가 아니라 본문 명사 (회사명 부분). _RE_PAREN_KOR
# false positive 차단용 (예 "(주)에서 푸본현대생명보험..." 본문 fragment 가 heading 으로
# 잘못 분류되던 회귀 차단).
_PAREN_CORPORATE_ABBREV = frozenset({"주", "사", "유", "재", "합", "조", "학", "의"})

# 한국 조사 prefix — heading label 검증용. label 이 조사로 시작하면 본문 fragment 일
# 확률 압도적. 회귀 사례: "은 다음과 같습니다.", "의 환산에서 발생하는...", "기준" (closing
# noun split 잔재) 같은 body fragment 가 heading 으로 박혀 textPath 오염.
_HEADING_JOSA_PREFIX = re.compile(r"^(?:에서|로서|로|는|은|이|가|을|를|의|도|만|과|와|및|또는|이며|에게|에게서)\s")

# 본문 conjunction adverb 단독 — "또한", "그러나", "그리고", "이러한", "다만" 등이 단독
# 또는 첫 단어로 등장 시 본문 절 conjunction. heading 명사구 아님.
_HEADING_CONJ_PREFIX = re.compile(r"^(?:또한|그러나|그리고|이러한|다만|아울러|특히|한편|이에|그러므로|따라서)(?:\s|$)")


def _gateHeadingLabel(level: int, label: str) -> tuple[int, str, bool] | None:
    """heading label gate — label 이 본문 fragment 같으면 None 반환.

    fragment 시그널:
    - 조사 prefix 시작 (예 "은 다음과 같습니다.")
    - closing noun 단독 + 너무 짧음 (예 "기준" / "사항")
    - 끝이 마침표/물음표/느낌표 종결 + 한국어 종결어미 ("다.", "요.", "까?", "오.")
    - 너무 긴 label (>80 글자) — 본문 한 문장 길이 — heading 은 명사구 짧음
    - 본문 verb-ending mid-sentence 패턴 ("하여 ...", "되어 ...") 포함 — 절 conjunction
    """
    if not label or len(label) > 80:
        return None
    if _HEADING_JOSA_PREFIX.match(label):
        return None
    if _HEADING_CONJ_PREFIX.match(label):
        return None
    # 종결문 검출 — heading 은 명사구 (체언) 가 일반. "...니다." / "...됩니다." 등 종결어미는 fragment.
    if re.search(r"(?:니다|됩니다|입니다|하였습니다|있습니다|없습니다|같습니다|바랍니다)\.?$", label):
        return None
    # 본문 절 conjunction — 한 절 안 verb-ending + 후속 절 (heading 은 단일 명사구)
    if re.search(r"(?:하여|되어|함으로|함에|되면|하면|함을|되었으며|하였으며)\s", label):
        return None
    # 명사형 종결사 "...함" / "...됨" / "...임" / "...있음" / "...없음" — 본문 절 nominalizer
    # 명사형 종결사 단독은 정상이지만 (예 "조달함") long label 의 끝이면 보고형 본문.
    if len(label) > 20 and re.search(
        r"(?:분석함|평가함|판단함|기록함|관리함|운영함|적용함|구성됨|반영됨|기재됨)\.?$", label
    ):
        return None
    return (level, label, True)


_RE_INLINE_PAREN_NUM = re.compile(r"(?<=[\s\)\d가-힣])(?=\(\d+\)[\s가-힣])")
_RE_INLINE_PAREN_KOR = re.compile(r"(?<=[\s\)\d가-힣])(?=\([가-힣]\)[\s가-힣])")
_RE_INLINE_KOR_DASH_NUM = re.compile(r"(?<!^)(?=[가-힣]-\d+\.)")
# inline 한글 heading marker split — "{한글}{한글 가/나/다/.../하}\.\s+{한글}" 패턴.
# parquet 본문 line-break 누락 case (005380 "연구개발활동가. 연구개발활동의 개요"):
# "활동" + "가. 연구개발활동의 개요" 로 split. 마커 한글 1자 (가-하) 만 매칭.
_RE_INLINE_KOR_HEADING = re.compile(r"(?<=[가-힣])(?=[가나다라마바사아자차카타파하]\.\s+[가-힣])")
# ▣ / ▶ / ◈ 한국 DART parquet sub-section marker — 회사명/카테고리 표시. line break
# 누락된 parquet 본문 안 inline marker 로 split. 회귀 사례 (005380 businessOverview):
# "수주에 관한 사항▣ 현대로템" 같이 "▣" 가 한글 직후 line-break 없이 박힌 경우.
_RE_INLINE_BULLET_MARKER = re.compile(r"(?<!^)(?=[▣▶◈]\s*[가-힣])")
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
    for pat in (
        _RE_INLINE_PAREN_NUM,
        _RE_INLINE_PAREN_KOR,
        _RE_INLINE_KOR_DASH_NUM,
        _RE_INLINE_BULLET_MARKER,
        _RE_INLINE_KOR_HEADING,
    ):
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
        if not seg:
            continue
        # split 다음 segment 가 조사로 시작 → fragment. 이전 segment 에 흡수 (split 무효화).
        if parts and _HEADING_JOSA_PREFIX.match(seg):
            parts[-1] = parts[-1] + " " + seg
            continue
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
        return _gateHeadingLabel(2, m.group(1).strip())

    m = _RE_KOREAN.match(stripped)
    if m:
        return _gateHeadingLabel(3, m.group(1).strip())

    m = _RE_PAREN_NUM.match(stripped)
    if m:
        return _gateHeadingLabel(4, m.group(2).strip())

    m = _RE_PAREN_KOR.match(stripped)
    if m:
        inner = m.group(1).strip()
        # (주)/(사)/(유)/(재)/(합)/(조)/(학)/(의) — 한국 법인격 약자. heading prefix 가 아니라
        # 본문 명사 (회사명 약자) 일 확률 압도적. 회귀 사례 (현대모비스 005380 companyOverview
        # blockOrder 20~26): "(주)에서 푸본현대생명보험(주)로 사명이 변경됨" 본문 문장이
        # (주) level 5 heading 으로 박혀 textPath "계열회사 현황 > 에서 푸본현대생명보험"
        # 같은 fragment heading 행 생성 → 후속 wide-format row 의 textPath pollution.
        if inner in _PAREN_CORPORATE_ABBREV:
            pass
        else:
            return _gateHeadingLabel(5, m.group(2).strip())

    m = _RE_CIRCLED.match(stripped)
    if m:
        return _gateHeadingLabel(5, m.group(2).strip())

    m = _RE_SHORT_PAREN.match(stripped)
    if m:
        inner = m.group(1).strip()
        if inner and len(inner) <= 48 and not _RE_HEADING_NOISE.match(inner):
            structural = not _isTemporalMarker(inner)
            gated = _gateHeadingLabel(6, inner)
            if gated is not None:
                return (6, gated[1], structural)

    m = _RE_BRACKET.match(stripped)
    if m:
        text = (m.group(1) or m.group(2) or "").strip()
        structural = not _isTemporalMarker(text)
        gated = _gateHeadingLabel(7, text)
        if gated is not None:
            return (7, gated[1], structural)

    m = _RE_BULLET_MARKER.match(stripped)
    if m:
        # ▣/▶/◈ 회사명/카테고리 marker — level 5 (sub-section)
        text = m.group(1).strip()
        gated = _gateHeadingLabel(5, text)
        if gated is not None:
            return (5, gated[1], True)

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
            # heading segmentKey 는 path 만 — level prefix 제거 (SSOT 정공법).
            # 옛 룰 `heading|lv:{level}|p:{path}` 은 같은 path 인데 source format
            # 차이로 level 만 다른 경우 (예: 기간 A 가 "가. X" 한글 L=3, 기간 B 가
            # "1. X" numeric L=2) segmentKey 분리 → 같은 의미 다른 row 위배.
            # path 가 stack 끝 자신 포함이므로 ancestor chain + label 동일 = 같은 heading.
            segmentKeyBase = f"heading|p:{semanticPathKey or semanticStackKey}"
        else:
            # redundantTopicAlias 인 경우 — 같은 @topic alias 의 sibling sub-section.
            # 1) stack 의 해당 entry label 을 latest 로 갱신 → 자식 textPath 정확.
            # 2) 그 entry 이후의 *모든* descendant pop — 직전 sub-section 의 stack
            #    entry (L=7 bracket marker / 등) 가 새 sibling 의 descendant 로 오염되는
            #    회귀 차단.
            #
            # 회귀 사례 (000660 companyOverview bo=16): 직전 "가. 연결대상 종속회사 개황"
            # sub-section 후 [연결대상회사의 변동내용] L=7 push → stack [@topic, L:7].
            # 새 "나. 회사의 법적·상업적 명칭" alias 가 redundantTopicAlias. 옛 룰은
            # label 만 갱신 → stack [@topic(label:법적·상업적 명칭), L:7] 잔존 → 후속 body
            # textPath = "회사의 법적·상업적 명칭 > 연결대상회사의 변동내용" 오염.
            # 정공법: alias entry 이후 stack 모두 pop.
            if redundantTopicAlias:
                aliasIdx: int | None = None
                for i, item in enumerate(stack):
                    if str(item["key"]) == stackKey:
                        aliasIdx = i
                        item["label"] = labelText
                        break
                if aliasIdx is not None and aliasIdx + 1 < len(stack):
                    del stack[aliasIdx + 1 :]
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
