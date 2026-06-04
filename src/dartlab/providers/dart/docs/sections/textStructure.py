from __future__ import annotations

import hashlib
import html
import re
from functools import lru_cache
from typing import Any, Literal

from dartlab.core.textNormalize import stripPeriodMarkers
from dartlab.providers.dart.sectionTopic import mapSectionTitle, stripSectionPrefix

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
    # 핫 패스 short-circuit: 패턴 prefix "니다." 가 없으면 regex 안 돌림.
    if "니다." not in text:
        return text
    return _RE_LINE_BREAK_REPAIR.sub("\n", text)


def _cleanLine(line: str) -> str:
    # HTML entity \ub514\ucf54\ub4dc \u2014 DART \uc6d0\ubb38\uc5d0 `&cr`, `&cr;&cr` \uac19\uc740 raw entity \uac00 \ub0a8\uc544
    # textPath / segmentKey \uc624\uc5fc\uc2dc\ud0a4\ub294 \ud68c\uadc0 \ucc28\ub2e8. html.unescape \ub294 \ud45c\uc900 entity
    # \ub514\ucf54\ub4dc, raw `&cr` (named entity \uc544\ub2d8) \uc740 \ubcc4\ub3c4 strip.
    # \ud56b \ud328\uc2a4 short-circuit: `&` / `\u00a0` / `\t` \uc5b4\ub290 \uac83\ub3c4 \uc5c6\uc73c\uba74 rstrip \ub9cc.
    if "&" not in line and "\u00a0" not in line and "\t" not in line:
        return line.rstrip()
    decoded = html.unescape(line)
    decoded = _HTML_ENTITY_RE.sub("", decoded)
    return decoded.replace("\u00a0", " ").replace("\t", " ").rstrip()


# 측정 (005930 + 000660 + 005380 sequential, disk cache bypass):
#   hit=94.8% / unique=2593 entries / 종목당 ~860 unique.
# 4096 = 종목 5 개 headroom — batch 호출에서도 hit rate 90%+ 유지.
# 옛 16384 는 over-provisioned (currsize/maxsize=15% 만 사용).
@lru_cache(maxsize=4096)
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


# 측정: hit=94.5% / unique=2579 — `_normalizeHeadingText` 와 동일 domain.
@lru_cache(maxsize=4096)
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
    """heading 의 stackKey 결정.

    원칙 1 (원본 hierarchy 보존): L=1 (Roman chapter) 만 @topic alias. L≥2
    sub-section 은 normal labelKey 로 distinct stack entry push → 본문이
    chapter row 에 흡수되지 않고 sub-section row 별로 분리 유지.

    회귀 사례 (005930 companyOverview): "가. 회사의 법적·상업적 명칭" 의
    mapSectionTitle 이 "companyOverview" topic 으로 매핑되어 @topic alias 화 →
    redundantTopicAlias 로 stack push X → body 의 semanticPathKey 가 chapter
    root 와 동일 → pivot 에서 chapter row 의 cell 로 merge → sub-section row
    들은 heading marker 만 갖고 body 부재.
    """
    if level <= 1 and isinstance(topic, str) and topic:
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


# 측정: hit=93.5% / unique=3005 — heading label × topic 도메인. 4096 충분.
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
    # period-variable date + 회사수 + 한국어 날짜/분기/누계/단위 strip — cross-period
    # semantic key invariance. opt: "기준일2025년06월30일" → "기준일" (date strip).
    # 회귀: 000660 회사의 개요 "연결대상종속사현황요약 > 기준일2025년06월30일" 가
    # period 별 다른 segmentKey 로 분기 → 같은 표가 다른 row → 시각 misalign.
    key = _RE_PERIOD_DATE.sub("", key)
    key = _RE_COUNT_SUFFIX.sub("", key)
    key = stripPeriodMarkers(key)

    if isinstance(topic, str) and topic == "businessOverview":
        key = key.replace("영업의개황", "영업현황")
    if isinstance(topic, str) and topic == "mdna":
        key = key.replace("환율변동영향", "환율변동")

    return key


# 측정: hit=3.0% / 512 maxsize cap 도달 + churn. 캐시 무용 — 본문은
# `_normalizeHeadingText` (캐시됨) + precompiled regex fullmatch 만. cache 제거가
# 정답 (overhead > benefit).
def _isTemporalMarker(text: str) -> bool:
    normalized = _normalizeHeadingText(text)
    return bool(_RE_TEMPORAL_MARKER.fullmatch(normalized))


# 측정: hit=56.5% / unique=19888 (3 종목) — 종목당 ~6630 unique body anchor.
# 8192 = 1.2 종목 헤드룸. **key 가 본문 텍스트 (수백 B)** 라 maxsize × keysize 가
# 캐시 메모리 본체. 옛 32768 은 ~10 MB 잠재 + linear 누적. blake2b 8 byte 자체는
# µs 수준이라 캐시 없어도 무방하나, 56% hit 가 의미 있어서 작은 bound 유지.
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

# 1-char Korean suffix 가 closing noun 과 결합해 합성어 형성 시 split 차단.
# 회귀 사례 (005380 재무제표): "기준" + "서" → "기준서" (standard document, 1 word).
# closing noun split 시 "기준" 까지가 가짜 heading 으로 박힘 ("마. 동 기준" 2x spurious).
# 관찰 사례: 기준서/기준일/기준값/기준량/기준표/기준안/기준액/기준점, 내역서/내역표,
#           현황표/현황도/현황지, 개요서/개요도, 계획서/계획안, 결과서/결과물, 방침서, 정책서.
_LABEL_NOUN_SUFFIX_CHARS = frozenset({"서", "일", "값", "량", "표", "안", "액", "도", "지", "점", "물"})

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


# sentence-end / 동사 활용 패턴 — 컴파일 캐시 + 모듈 레벨 (re.search 매 호출 캐시 lookup 회피)
_RE_HEADING_SENTENCE_END = re.compile(r"(?:니다|됩니다|입니다|하였습니다|있습니다|없습니다|같습니다|바랍니다)\.?$")
_RE_HEADING_CLAUSE_CONJ = re.compile(r"(?:하여|되어|함으로|함에|되면|하면|함을|되었으며|하였으며)\s")
_RE_HEADING_VERB_MID = re.compile(
    r"(?:인식하|적용하|사용하|포함하|기록하|평가하|판단하|관리하|운영하|실시하|발생하|결정하|반영하|구성하|영향)\S{0,2}\s"
)
_RE_HEADING_SUBJ_MARK = re.compile(r"[은는이가]\s+\S")
_RE_HEADING_NOMINAL_END = re.compile(r"(?:분석함|평가함|판단함|기록함|관리함|운영함|적용함|구성됨|반영됨|기재됨)\.?$")


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
    # 짧은 label (< 7 chars) 은 종결사 패턴 매칭 불가능 (최소 6 char "니다." + 단어).
    if len(label) >= 5 and _RE_HEADING_SENTENCE_END.search(label):
        return None
    # 본문 절 conjunction / 동사 mid-sentence — 둘 다 공백 다음 단어 필요 (mid-sentence).
    # 짧은 label (≤ 8 chars) 은 절 분리 불가능 — skip.
    if len(label) > 8:
        if _RE_HEADING_CLAUSE_CONJ.search(label):
            return None
        if _RE_HEADING_VERB_MID.search(label):
            return None
        # 주어 마커 "은/는/이/가" 공백 + 단어 — 절 분리.
        if _RE_HEADING_SUBJ_MARK.search(label):
            return None
    # 명사형 종결사 — long label 의 끝 nominalizer 만 reject (단독은 정상).
    if len(label) > 20 and _RE_HEADING_NOMINAL_END.search(label):
        return None
    return (level, label, True)


_RE_INLINE_PAREN_NUM = re.compile(r"(?<=[\s\)\d가-힣])(?=\(\d+\)[\s가-힣])")
_RE_INLINE_PAREN_KOR = re.compile(r"(?<=[\s\)\d가-힣])(?=\([가-힣]\)[\s가-힣])")
_RE_INLINE_KOR_DASH_NUM = re.compile(r"(?<!^)(?=[가-힣]-\d+\.)")
# inline 한글 heading marker split — "{한글}{한글 가/나/다/.../하}\.\s+{한글}" 패턴.
# parquet 본문 line-break 누락 case (005380 "연구개발활동가. 연구개발활동의 개요"):
# "활동" + "가. 연구개발활동의 개요" 로 split. 마커 한글 1자 (가-하) 만 매칭.
#
# 두 false positive 가드:
# 1. marker 앞이 verb-ending 한글 (니/었/았/였/왔/갔/봤/했/혔/임/음/됨) 이면 split 차단.
#    회귀 사례 (005930): "있습니다. 또한, 대형 ..." → "다" 가 marker 로 잡혀 가짜 heading.
#    회귀 사례 (005930): "입니다. 이중 상장사는 ..." → "다. 이중 상장사는" 잘못 split.
# 2. marker 뒤 한글이 conjunction adverb (또한/그러나/...) 면 split 차단.
#
# 005380 의 정상 사례 "활동가. 연구개발활동" 은 영향 없음 (앞 "동" 은 verb-ending 아님,
# 뒤 "연구개발" 은 conjunction 아님).
_RE_INLINE_KOR_HEADING = re.compile(
    r"(?<=[가-힣])"
    r"(?<![니었았였왔갔봤했혔임음됨겠셨씁됩봅쳤])"
    r"(?=[가나다라마바사아자차카타파하]\.\s+"
    r"(?!(?:또한|그러나|그리고|이러한|다만|아울러|특히|한편|이에|그러므로|따라서|그래서|그러면|그렇기)(?:\s|,))"
    r"[가-힣])"
)
# ▣ / ▶ / ◈ 한국 DART parquet sub-section marker — 회사명/카테고리 표시. line break
# 누락된 parquet 본문 안 inline marker 로 split. 회귀 사례 (005380 businessOverview):
# "수주에 관한 사항▣ 현대로템" 같이 "▣" 가 한글 직후 line-break 없이 박힌 경우.
_RE_INLINE_BULLET_MARKER = re.compile(r"(?<!^)(?=[▣▶◈]\s*[가-힣])")
# circle number marker — ①②③④⑤⑥⑦⑧⑨⑩... 한글 직후 line-break 없이 박힌 경우 split.
# 회귀 사례 (005930 affiliateGroup): "(4) 계열회사의 지분현황① 국내법인" 같이 ① 앞에
# 한글이 line-break 없이 붙은 경우 → "(4) 계열회사의 지분현황" + "① 국내법인" 으로 split.
_RE_INLINE_CIRCLE_MARKER = re.compile(r"(?<=[가-힣\)\d])(?=[①-⑳⓪]\s*[가-힣\(\[])")
# bracket-bracket 인접 marker — "[34. 음식점업][35. 인테리어 ...]" 같이 sub-section
# bracket 이 line-break 없이 연속된 경우 → 각 bracket 별 split.
_RE_INLINE_BRACKET_ADJ = re.compile(r"(?<=\])(?=\[)")
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

    # 핫 패스 short-circuit — split trigger char (`(` / 본문 안 bullet / circled /
    # bracket) 가 line 에 없고 첫 자가 한글/숫자 prefix 도 아니면 split 후보 0 → 즉시 [line].
    # 대부분 본문 line (예: "당사는 ... 보고서를 작성합니다.") 은 이 가드로 7 regex 절약.
    if not _INLINE_SPLIT_TRIGGERS.intersection(line):
        first = line[0]
        if not ("0" <= first <= "9") and not ("가" <= first <= "힣"):
            return [line]

    positions: set[int] = {0}
    for pat in (
        _RE_INLINE_PAREN_NUM,
        _RE_INLINE_PAREN_KOR,
        _RE_INLINE_KOR_DASH_NUM,
        _RE_INLINE_BULLET_MARKER,
        _RE_INLINE_CIRCLE_MARKER,
        _RE_INLINE_BRACKET_ADJ,
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
                # 1-char Korean suffix 가 closing noun 과 합성어 형성 시 split 차단.
                # 회귀 사례 (005380 재무제표): "마. 동 기준서로 인한 회계정책..." 의 "기준"
                # closing noun + "서" suffix = "기준서" (standard document) — split 시 가짜
                # heading "마. 동 기준" 생성. 다른 유사 사례: 내역서/현황표/개요서/내용물.
                if nextChar in _LABEL_NOUN_SUFFIX_CHARS:
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


# `_splitInlineMultiHeading` short-circuit — split trigger char 가 line 에 없으면 7 regex 절약.
_INLINE_SPLIT_TRIGGERS = frozenset("(▣▶◈[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")


# first-char dispatch — 대부분 본문 line 은 첫 자만 보고 즉시 None reject.
# 핫 패스 최적화 (각 line 에 ~10 regex check → 1 set lookup + 0-1 regex check).
_HEADING_PREFIX_CHARS = frozenset(
    # Roman
    "IVXivx"
    # Numeric
    "0123456789"
    # Paren / Bracket (paren_num / paren_kor / short_paren / bracket)
    "([【"
    # Bullet
    "▣▶◈"
    # Circled (단일 char ① ~ ⑳ + ⓪)
    "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳⓪"
)


# 측정: hit=81.3% / unique=48230 (3 종목) — 종목당 ~16K 본문 line. 옛 65536 은
# 종목 4 개 즈음 cap 도달 + 이후 churn. 16384 = 1 종목 + 일부 헤드룸.
# 다종목 batch 에서는 evict 빈번하나 hit rate 75%+ 유지 (heading prefix 패턴이
# 종목 간 매우 중복: "I. 회사의 개요", "1. 주요사항" 등).
@lru_cache(maxsize=16384)
def _detectHeading(line: str) -> tuple[int, str, bool] | None:
    stripped = line.strip()
    if not stripped or stripped[0] == "|":
        return None
    if len(stripped) > 120:
        return None
    # `## ` markdown bold prefix — zipDocsXml._walk 가 SPAN-bold + TABLE-GROUP 안 nested
    # TITLE 을 parent 본문에 흡수할 때 부여하는 marker. 같은 cache 로 재귀 위임 후 level
    # +1 격하 (parent Roman chapter L=1 의 sub-section L=2 row 안에서 sub-sub heading
    # L=3 자리). 005930 consolidatedNotes_12_borrowings 본문 손실 회귀 root fix.
    if stripped.startswith("## "):
        sub = stripped[3:].strip()
        if not sub:
            return None
        inner = _detectHeading(sub)
        if inner is None:
            return _gateHeadingLabel(2, sub)
        lvl, label, structural = inner
        return (min(lvl + 1, 6), label, structural)
    # first-char dispatch: 한글 _RE_KOREAN 이 "가-힣" 매칭이므로 dict 검사 후
    # 한글 음절 추가 검사 — 대부분 본문 line 빠른 short-circuit.
    first = stripped[0]
    if first not in _HEADING_PREFIX_CHARS and not ("가" <= first <= "힣"):
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
        label = m.group(1).strip()
        # 한 글자 한글 label (예: "1. 일") 은 본문 단어 끊김 fragment.
        # 회귀 사례 (005930 옛 quarterly `1. 일반적 사항` 본문이 줄바꿈 깨져 `1. 일\n반적 사항`
        # 로 흘러들어와 첫 줄 `1. 일` 이 L2 heading 으로 잡힘 → textPath segment `일` 만 잘림 →
        # 365 row 가 `일 > ...` root 로 박혀 consolidatedNotes_22_sga / _01_general /
        # _29_fairValue 등 잘못된 sub-topic 으로 오분류). 한글 heading 매처의 동일 가드와 짝.
        if len(label) == 1 and "가" <= label <= "힣":
            return None
        return _gateHeadingLabel(2, label)

    m = _RE_KOREAN.match(stripped)
    if m:
        label = m.group(1).strip()
        # 한 글자 한글 label (예: "다. 메") 은 본문 단어 끊김 fragment 일 확률 압도.
        # 회귀 사례 (005930 II. 사업의 내용 본문 line-break 결함):
        # "...있습니" / "다. 메" / "모리 반도체 시장..." 3 라인 분할 → "다. 메" 가
        # L3 heading 으로 잡혀 textPath segment "메" 잘림.
        if len(label) == 1 and "가" <= label <= "힣":
            return None
        return _gateHeadingLabel(3, label)

    m = _RE_PAREN_NUM.match(stripped)
    if m:
        label = m.group(2).strip()
        # malformed paren — "(11) 참조)" 처럼 group2 가 trailing `)` 끝나면 본문
        # fragment (citation/reference) 의 잘림. heading 아님 (회귀 차단).
        if label.endswith(")") and label.count("(") < label.count(")"):
            pass
        # trailing circle marker — "(2) 연결①" 처럼 circle 가 본문 마지막에 박힌
        # 경우 본문 fragment + 다음 sub-section marker 가 line break 없이 붙은
        # case. label 안에 circle marker 들어있으면 heading 아님.
        elif any(c in label for c in "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳⓪"):
            pass
        # B-5 가드: body sentence fragment. paren_num label 안에 본문 문장
        # 시그니처 (`X : Y` 콜론 + 다중 콤마 + 임베디드 paren close) 가 있으면
        # heading 아닌 본문. 100 sample audit (2026-05-22) 발견 패턴:
        #   "(2) 판매조건 : 수출 - L/C BASE        " → 본문 row
        #   "(3) 생산설비의 현황 등주) 종속회사인 JW Theriac,C신약연구소" → 본문 row
        elif " : " in label or " 등주)" in label or label.count(",") >= 2:
            pass
        # B-5 가드: `_RE_PAREN_KOR` 의 `(가)내지` 패턴 처럼 본 매처에서도 inner
        # connector `내지` (= "or") 직후 단어 시작 시 본문 fragment.
        elif "내지" in label[:8]:
            pass
        else:
            return _gateHeadingLabel(4, label)

    m = _RE_PAREN_KOR.match(stripped)
    if m:
        inner = m.group(1).strip()
        rest = m.group(2).strip()
        # (주)/(사)/(유)/(재)/(합)/(조)/(학)/(의) — 한국 법인격 약자. heading prefix 가 아니라
        # 본문 명사 (회사명 약자) 일 확률 압도적. 회귀 사례 (현대모비스 005380 companyOverview
        # blockOrder 20~26): "(주)에서 푸본현대생명보험(주)로 사명이 변경됨" 본문 문장이
        # (주) level 5 heading 으로 박혀 textPath "계열회사 현황 > 에서 푸본현대생명보험"
        # 같은 fragment heading 행 생성 → 후속 wide-format row 의 textPath pollution.
        if inner in _PAREN_CORPORATE_ABBREV:
            pass
        # B-5 가드: temporal/period marker — `(당) 기초`, `(전) 기말` 등은
        # 재무제표 표 안의 *기간 컬럼* heading 위장. sections heading 아님.
        # 100 sample audit (2026-05-22) `(당) 기초` 2회 발견.
        elif inner in {"당", "전", "전전", "당기", "전기", "전전기", "당분기", "전분기"}:
            pass
        # B-5 가드: connector `내지` (= "or", 법조문/계약서 연결사) 시작.
        #   "(가)내지", "(나)내지(다)" 등 — 본문 인용 fragment.
        elif rest.startswith("내지"):
            pass
        else:
            return _gateHeadingLabel(5, rest)

    m = _RE_CIRCLED.match(stripped)
    if m:
        label = m.group(2).strip()
        # B-5 가드: 본문 list item — 한 라인에 다중 circle marker (① X ② Y) 가
        # 있으면 sub-section 분리가 아니라 본문 sentence (heading 아님).
        # 100 sample audit (2026-05-22):
        #   "① R실 산하 육가공개발1팀, 육가공개발2팀   ② 마케팅실 산하 신선마"
        if any(c in label for c in "②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"):
            return None
        return _gateHeadingLabel(5, label)

    m = _RE_SHORT_PAREN.match(stripped)
    if m:
        inner = m.group(1).strip()
        if inner and len(inner) <= 48 and not _RE_HEADING_NOISE.match(inner):
            # 본문 annotation marker 추가 가드 — heading 아닌 parenthetical 차단.
            # 회귀 사례 (Phase A 후 sectionsRawCompare spurious=11):
            # - "(舊 SK C㈜)" 5× — 옛 사명 marker (000660 SK하이닉스)
            # - "(Frost, 2021.7월 기준)" — citation
            # - "(*)" — placeholder
            # - "(11) 참조)" — 잘못된 trailing `)` 의 line
            if inner.startswith("舊 ") or "," in inner or set(inner) <= set("*") or inner.endswith(") 참조"):
                pass
            else:
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


# ── 재내보내기 (분리: textStructureParse.py) ────────────────────
from dartlab.providers.dart.docs.sections.textStructureParse import (  # noqa: E402  re-export
    parseTextStructure,
    parseTextStructureWithState,
)

__all__ = ["TextNodeType", "parseTextStructure", "parseTextStructureWithState"]
