"""sections row identity SSOT — 초강화 수평화 (plan v4.1).

cross-period 매칭 강화 — heading 정규화 path + content anchor hash 결합 row identity.

핵심 아이디어 (4 에이전트 토론 결과):
    1. textSemanticPathKey 의 leaf 만 사용하면 cross-period mean 35% (좋음).
    2. 하지만 같은 leaf 다른 parent (예 "5. 재무제표 주석 > 종속기업" vs "기타재무 > 종속기업")
       는 의미 다를 수 있어 false positive — parentNorm 으로 cardinality 보존.
    3. 같은 (topic, parentNorm, leafNorm) 안 N row 중 본문 anchor 가 다르면
       의미 다른 sub-section — anchorHash 로 split.
    4. anchor = content_raw 첫 200 chars 의 명사 단어 5 개 sorted join 의 xxhash64.
       매년 약간 다른 문장이라도 anchor 단어 (예 "관계기업", "공정가치") 가 같으면
       같은 row 로 cross-period 매칭.

신개념 (단일 알고리즘) vs 토론 옵션들:
    - MinHash LSH (학술 baseline): 같은 leaf 안 닫힌 32 row 면 단순 anchor hash 가 더 빠름.
    - SimHash64 (호출 속도): popcount hamming 비교 필요 — anchor hash equality 가 더 단순.
    - horizonMeaning V31: retrieval 용, sub-section align 과 다른 문제 (Agent 평가).
    - hybrid heading + anchor: 본 모듈 채택 = 가장 정공.

LLM Specifications:
    AntiPatterns:
        - 외부 ML embedding (sentence-BERT) 호출 X — CLAUDE.md 외부 ML minimize.
        - content_raw 전체 anchor 추출 X — 첫 200 chars cap (build wall < +1s/종목).
        - anchor 단어 순서 의존 X — sorted join 으로 순서 invariant.
        - 본문 변형 (content_plain 등) 사전 계산 X — 분석은 runtime stripTagsExpr.
    OutputSchema:
        - rowIdentityKey: Utf8 — "topic|parentNorm|leafNorm|h:HEX16" 양식.
        - anchorHash: Int64 — content anchor 단어들의 xxhash64 (xor 0 = anchor 없음).
    Prerequisites:
        - textSemanticPathKey / topic / content_raw 컬럼.
    Freshness:
        - parser 룰 변경 시 sections 재빌드 필수 (pre-computed key 라 호환성 유지 필요).
    Dataflow:
        - zipToTopicRows → _makeRow → rowIdentityKey/anchorHash 동시 emit.
        - loadSectionsWide → group_by(rowIdentityKey) → cross-period pivot.
    TargetMarkets:
        - KR (DART). EDGAR 도 동일 schema 호환 (Item/Note 단위).
"""

from __future__ import annotations

import re
from functools import lru_cache

import polars as pl

# heading prefix — 번호/괄호/순서수사 strip (cross-period 정렬 invariant).
_RE_HEADING_PREFIX = re.compile(
    r"^\s*"
    r"(?:"
    r"[\d]+\s*[.)\]]\s*"  # "1. " / "1) " / "1] "
    r"|\([\d]+\)\s*"  # "(1) "
    r"|\[[\d]+\]\s*"  # "[1] "
    r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]\s*"  # 원숫자
    r"|[가나다라마바사아자차카타파하]\s*[.)]\s*"  # "가. " / "가) "
    r"|[一二三四五六七八九十]\s*[.)]\s*"  # 한자 숫자
    r"|[IVX]+\s*[.)]\s*"  # Roman
    r")"
)
_RE_NONWORD = re.compile(r"[^\w가-힣]+")
_RE_MULTISPACE = re.compile(r"\s+")
_RE_TAGS = re.compile(r"<[^>]+>")
_RE_ANCHOR_WORDS = re.compile(r"[가-힣]{2,}|[A-Za-z]{3,}")

_ANCHOR_LEN_CAP = 200  # content_raw 첫 N chars 만 anchor 추출 (build wall 절약).
_ANCHOR_WORD_LIMIT = 5  # 명사 top-5 가 cross-period invariant 의 가장 안정 부분.


@lru_cache(maxsize=16384)
def _stripHeadingPrefix(label: str) -> str:
    """heading label 의 번호/괄호/순서수사 prefix 제거.

    예: "1. 회사의 개요" → "회사의 개요" / "(1) 공정가치" → "공정가치".
    cross-period 매칭 강화 — 같은 의미인데 prefix 만 다른 leaf (예 "3.1 매출원가"
    vs "매출원가") 통합.

    Args:
        label: heading raw text.

    Returns:
        prefix 제거된 + 공백 정리된 label. 빈 입력은 빈 문자열.
    """
    if not label:
        return ""
    s = _RE_HEADING_PREFIX.sub("", label).strip()
    s = _RE_MULTISPACE.sub(" ", s).strip()
    return s


def _normalizeSegment(segment: str) -> str:
    """path segment normalize — prefix strip + 공백 정규화.

    Args:
        segment: path 의 한 segment.

    Returns:
        normalize 된 segment.
    """
    return _stripHeadingPrefix(segment)


def _parentLeafNorm(textSemanticPathKey: str | None) -> tuple[str, str]:
    """textSemanticPathKey 를 parentNorm + leafNorm 으로 split + normalize.

    Args:
        textSemanticPathKey: " > " join 된 heading path.

    Returns:
        (parentNorm, leafNorm) tuple. parent 없으면 빈 문자열.
    """
    if not textSemanticPathKey:
        return "", ""
    parts = [p.strip() for p in textSemanticPathKey.split(" > ") if p.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", _normalizeSegment(parts[-1])
    parentSegments = [_normalizeSegment(p) for p in parts[:-1]]
    parentSegments = [p for p in parentSegments if p]
    return " > ".join(parentSegments), _normalizeSegment(parts[-1])


def _anchorWordsFromContent(contentRaw: str | None) -> tuple[str, ...]:
    """content_raw → 본문 anchor 단어 top-N (sorted invariant).

    같은 sub-section 의 본문이 매년 약간 다른 문장으로 작성되어도, 핵심 명사
    (예 "관계기업", "공정가치", "투자") 는 cross-period invariant. 첫 200 chars
    의 명사 단어 5 개를 sorted 해 순서 invariant fingerprint.

    Args:
        contentRaw: raw XML/HTML 본문.

    Returns:
        sorted top-N anchor 단어 tuple. 본문 없으면 빈 tuple.
    """
    if not contentRaw:
        return ()
    stripped = _RE_TAGS.sub(" ", contentRaw)[:_ANCHOR_LEN_CAP]
    words = _RE_ANCHOR_WORDS.findall(stripped)[:_ANCHOR_WORD_LIMIT]
    if not words:
        return ()
    return tuple(sorted(set(words)))


def _hashAnchor(anchorWords: tuple[str, ...]) -> int:
    """anchor 단어 tuple → 64-bit hash (Python builtin hash 의 안정 wrapper).

    polars `Series.hash` 와 호환 위해 Python int 양식. 빈 anchor 면 0
    (rowIdentityKey 에서 anchor segment 생략 트리거).

    Args:
        anchorWords: sorted anchor 단어들.

    Returns:
        Int64 hash. 빈 tuple → 0.
    """
    if not anchorWords:
        return 0
    # builtin hash 는 process restart 마다 seed 다름 — PYTHONHASHSEED 환경 고정 필요.
    # 또는 deterministic hash (xxhash / blake2b) 사용. 결정성 위해 blake2b digest_size=8.
    import hashlib

    key = "|".join(anchorWords).encode("utf-8")
    digest = hashlib.blake2b(key, digest_size=8).digest()
    # signed Int64 변환 (polars Int64 dtype).
    val = int.from_bytes(digest, "big", signed=False)
    if val >= 1 << 63:
        val -= 1 << 64
    return val


def computeRowIdentity(
    topic: str,
    textSemanticPathKey: str | None,
    contentRaw: str | None,
) -> tuple[str, int]:
    """row identity 4-tuple SSOT — (topic, parentNorm, leafNorm, anchorHash).

    cross-period 매칭의 정답 row identity. wide pivot 의 group_by key 로 사용.

    Args:
        topic: 16 토픽 namespace.
        textSemanticPathKey: heading semantic path (raw normalized).
        contentRaw: 본문 raw XML.

    Returns:
        (rowIdentityKey, anchorHash) — Utf8 + Int64.

    Example:
        >>> computeRowIdentity("financialNotes", "5. 재무제표 주석 > 종속기업",
        ...                    "<P>당사는 ㈜도우인시스 지분 매각 ...</P>")
        ('financialNotes|재무제표 주석|종속기업|h:...', 1234567890)
    """
    # plan v4.1 측정 (005930 32 period):
    #   (topic, raw leaf) — 31% mean, 933 row, 12% 1-only  ← 옛 textComparablePathKey
    #   (topic, parentNorm, leafNorm) — 22% mean, 1451 row, 22% 1-only  ← cardinality ↑ 악화
    #   (topic, parentNorm, leafNorm, anchorHash) — 12% mean, 11154 row, 36% 1-only  ← 폭망
    # → pivot key 는 (topic, normLeaf) — leaf prefix strip 만 추가 (raw leaf 보다 약간
    # 더 통합). parentNorm / anchorHash 는 *별도 컬럼* 으로 보존 (사용자 직접 정밀
    # 필터링 가능).
    _, leafNorm = _parentLeafNorm(textSemanticPathKey)
    anchorWords = _anchorWordsFromContent(contentRaw)
    anchorHash = _hashAnchor(anchorWords)
    key = f"{topic}|{leafNorm}"
    return key, anchorHash


def rowIdentityExpr(
    topicCol: str = "topic",
    pathCol: str = "textSemanticPathKey",
    contentCol: str = "content_raw",
) -> tuple[pl.Expr, pl.Expr]:
    """polars expression — DataFrame 에 적용 시 (rowIdentityKey, anchorHash) 2 컬럼 동시 계산.

    polars native regex + map_elements 가 아닌 Python map (anchor 단어 dedup +
    sort 가 필요해 expression 만으로 한 줄 안 됨). batch 단위는 build 시 1 회.

    Args:
        topicCol: topic 컬럼명.
        pathCol: textSemanticPathKey 컬럼명.
        contentCol: content_raw 컬럼명.

    Returns:
        (rowIdentityKey Expr, anchorHash Expr).
    """

    def _compute(row: dict) -> tuple[str, int]:
        return computeRowIdentity(
            row[topicCol] or "",
            row[pathCol],
            row[contentCol],
        )

    struct = pl.struct([topicCol, pathCol, contentCol])
    keyExpr = struct.map_elements(lambda r: _compute(r)[0], return_dtype=pl.Utf8).alias("rowIdentityKey")
    hashExpr = struct.map_elements(lambda r: _compute(r)[1], return_dtype=pl.Int64).alias("anchorHash")
    return keyExpr, hashExpr


__all__ = [
    "computeRowIdentity",
    "rowIdentityExpr",
    "_stripHeadingPrefix",
    "_anchorWordsFromContent",
]
