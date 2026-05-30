"""TITLE 텍스트 NFKC + prefix strip + tokenize — ref table canonical key 생성.

5 baseline 실측 (005930 / 005380 / 035720 / 207940 / 000660 2025Q4):
    - "1. 회사의 개요" / "II. 사업의 내용" / "가. 회사의 법적·상업적 명칭"
    - "3.1 매출원가" / "3-1. 매출원가" / "1) ..." / "(1) ..."
    - 035720 만 "(제조서비스업)" prefix 추가 — 괄호 내용까지 strip 필요.

LLM Specifications:
    AntiPatterns:
        - mapper.py / 260 regex 자료 import 금지.
        - 한글 형태소 분석 라이브러리 (konlpy/soynlp) 사용 금지 — KISS.
        - 외부 의존성 추가 금지 — 표준 ``re`` + ``unicodedata`` 만.
    OutputSchema:
        - ``normalizeTitle(str) -> str`` — canonical form.
        - ``tokenize(str) -> set[str]`` — 한글 2자+ / 영문 2자+ token set
          (Jaccard similarity 용).
    Prerequisites:
        - 없음 (stdlib 만).
    Freshness:
        - regex pattern 변경 시 5 baseline parity 재측정 필수.
    Dataflow:
        - raw title (e.g. "1. (제조서비스업)사업의 개요")
          → NFKC → prefix strip (숫자/Roman/한글번호/괄호)
          → 어미 strip (의/에 관한/등)
          → 공백 정리.
    TargetMarkets:
        - KR. EDGAR 는 영어 전용 normalizer 별도.
"""

from __future__ import annotations

import re
import unicodedata

# 숫자/Roman/한글번호 prefix (선두 다중 매칭 가능)
_NUMERIC_PREFIX_RE = re.compile(
    r"""
    ^\s*
    (
        [IVXLCDMivxlcdm]+ [\.．] \s* |               # Roman: I. II. III.
        [가-힣] [\.．] \s* |                          # 한글번호: 가. 나. 다.
        \d+ ([\.．\-] \d+)* [\.．\-)] \s* |          # 1. / 3.1 / 1) / 1-1)
        \( \d+ ([\.．\-] \d+)* \) \s*                 # (1) / (1.1)
    )+
    """,
    re.VERBOSE,
)

# 괄호 내용 strip — 035720 의 "(제조서비스업)" 같은 회사 특유 prefix
_PAREN_STRIP_RE = re.compile(r"\s*[\(（\[【「『][^\)）\]】」』]*[\)）\]】」』]\s*")

# 한글 어미 strip — 의미 단위 통일
_SUFFIX_STRIP_RE = re.compile(r"(에\s*관한\s*사항|에\s*관한|에\s*대한|관련|에\s*있어서)$")
_TAIL_STRIP_RE = re.compile(r"(의\s*구성|의\s*내용|의\s*개요|현황)$")

# 다중 공백
_MULTISPACE_RE = re.compile(r"\s+")

# token 추출 — 한글 2자+ 또는 영문 2자+
_TOKEN_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}")


def normalizeTitle(raw: str) -> str:
    """TITLE 텍스트 → canonical form.

    Args:
        raw: TABLE-GROUP / TITLE element 의 itertext concat.

    Returns:
        NFKC + prefix strip + 어미 strip + 공백 정리 결과.
        빈 입력 또는 normalize 후 빈 결과는 ``""``.

    Raises:
        없음 — 빈/None 유사 입력은 ``""`` 반환.

    Example:
        >>> normalizeTitle("1. 회사의 개요")
        '회사의 개요'
        >>> normalizeTitle("1. (제조서비스업)사업의 개요")
        '사업의 개요'
        >>> normalizeTitle("3-1. 매출원가의 구성")
        '매출원가'
        >>> normalizeTitle("Ⅲ. 재무에 관한 사항")
        '재무'
        >>> normalizeTitle("")
        ''

    SeeAlso:
        - ``tokenize`` — canonical title → token set.
        - ``refMatcher.matchToRef`` — canonical 비교로 옛 양식 매칭.

    Requires:
        - 표준 라이브러리 (re, unicodedata).

    Capabilities:
        - 회사·era 별 제목 표기 변동을 canonical form 으로 흡수 → ref 집계·fuzzy 매칭 키.

    Guide:
        - aclassExtractor·refMatcher 내부에서 호출 — 직접 호출 X.

    AIContext:
        - 순수 변환 — 외부 의존 0, 형태소 분석 미사용(KISS).

    LLM Specifications:
        AntiPatterns:
            - prefix strip 순서 변경 금지 — NFKC 가 Roman 숫자 (Ⅰ→I) 변환을 먼저.
            - 어미 strip 두 번 적용(loop) 금지 — nested 사례는 수동 큐레이션.
        OutputSchema:
            - ``str`` (canonical title, lowercase 안 함 — 한글 case 없음).
        Prerequisites:
            - 입력 string. None 은 caller 책임.
        Freshness:
            - regex pattern 변경 시 baseline parity 재측정.
        Dataflow:
            - raw → NFKC → prefix strip → 괄호 strip → 어미 strip → 공백 정리.
        TargetMarkets:
            - KR. EDGAR 는 영어 전용 normalizer 별도.
    """
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", raw).strip()
    if not s:
        return ""
    # prefix strip — 다중 prefix 한 번에 (예: "1.1.1 ...")
    s = _NUMERIC_PREFIX_RE.sub("", s)
    # 괄호 prefix strip — 회사 특유 prefix ("(제조서비스업)...")
    s = _PAREN_STRIP_RE.sub("", s)
    # 어미 strip
    s = _SUFFIX_STRIP_RE.sub("", s).strip()
    s = _TAIL_STRIP_RE.sub("", s).strip()
    # 다중 공백 정리
    s = _MULTISPACE_RE.sub(" ", s).strip()
    return s


def tokenize(text: str) -> set[str]:
    """canonical title → token set (Jaccard 계산용).

    Args:
        text: ``normalizeTitle`` 결과 또는 원본 string.

    Returns:
        한글 2자+ 또는 영문 2자+ token 의 set. NFKC normalize 후 추출.

    Raises:
        없음 — 빈 입력은 ``set()``.

    Example:
        >>> sorted(tokenize("매출원가의 구성"))
        ['구성', '매출원가']
        >>> sorted(tokenize("Revenue Recognition Policy"))
        ['Policy', 'Recognition', 'Revenue']
        >>> tokenize("")
        set()

    SeeAlso:
        - ``normalizeTitle`` — token 추출 전 canonical form.
        - ``jaccardSimilarity`` — token set 유사도.

    Requires:
        - 표준 라이브러리 (re, unicodedata).

    Capabilities:
        - canonical title 의 의미 token 추출 → Jaccard 유사도 입력.

    Guide:
        - refMatcher 내부에서 호출 — 직접 호출 X.

    AIContext:
        - 순수 추출 — 한글 2자+ / 영문 2자+ token.

    LLM Specifications:
        AntiPatterns:
            - 1글자 token 포함 금지 — 한글 1자("가"·"의") 노이즈.
            - lowercase 적용 금지 — 영문 case 보존 (us-gaap PascalCase).
        OutputSchema:
            - ``set[str]``.
        Prerequisites:
            - 입력 string.
        Freshness:
            - token regex 변경 시 baseline 재측정.
        Dataflow:
            - text → NFKC → _TOKEN_RE findall → set.
        TargetMarkets:
            - KR + US (한글·영문 token 동시 지원).
    """
    if not text:
        return set()
    norm = unicodedata.normalize("NFKC", text)
    return set(_TOKEN_RE.findall(norm))


def jaccardSimilarity(a: set[str], b: set[str]) -> float:
    """두 token set 의 Jaccard similarity.

    Args:
        a: token set 1.
        b: token set 2.

    Returns:
        ``|a ∩ b| / |a ∪ b|``. 양쪽 빈 set 이면 ``0.0``.

    Raises:
        없음.

    Example:
        >>> jaccardSimilarity({"매출원가", "구성"}, {"매출원가", "정책"})
        0.3333333333333333
        >>> jaccardSimilarity(set(), set())
        0.0
        >>> jaccardSimilarity({"a"}, {"a"})
        1.0

    SeeAlso:
        - ``tokenize`` — 입력 token set 생산.
        - ``refMatcher.matchToRef`` — 본 유사도로 best match 선택.

    Requires:
        - 없음 (집합 연산).

    Capabilities:
        - 두 제목 token set 의 의미 근접도 측정 → 옛 양식 fuzzy 매칭 score.

    Guide:
        - refMatcher 내부에서 호출 — 직접 호출 X.

    AIContext:
        - 순수 집합 연산 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 한쪽 빈 set 에 1.0 반환 금지 — 0.0 (무의미 매칭 차단).
        OutputSchema:
            - ``float`` (0.0 ~ 1.0).
        Prerequisites:
            - token set 2개.
        Freshness:
            - 정적.
        Dataflow:
            - (a, b) → |교집합| / |합집합|.
        TargetMarkets:
            - KR + US 공통.
    """
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union)
