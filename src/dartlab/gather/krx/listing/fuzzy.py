"""한글 fuzzy 회사명 검색 — 초성 매칭 + Levenshtein 거리.

`registry.py` 의 `getKindList()` 결과를 입력으로 받아 회사명 검색에
다음 4 단계 점수를 적용한다:

    1) 정확 일치 (score=0)
    2) substring 매칭 (prefix > contains)
    3) 초성 매칭 (순수 초성 입력 + 혼합 입력 subsequence)
    4) Levenshtein 거리 (편집거리 1~3)

`_searchCache` 모듈 글로벌은 첫 호출 시 사전 계산 (회사명 lowercase + 초성).
`registry.getKindList()` 가 갱신될 때 `registry._invalidateSearchCache()` 가
이 글로벌을 None 으로 리셋.
"""

from __future__ import annotations

import polars as pl

from .registry import getKindList

_CHOSUNG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_CHO_BASE = 0xAC00
_CHO_PERIOD = 588  # 21 * 28

# fuzzySearch 캐시 — getKindList() 갱신 시 registry 가 None 으로 리셋
_searchCache: dict[str, object] | None = None


def _decomposeChar(ch: str) -> str:
    """한글 음절 → 초성 추출. 이미 자모이거나 비한글이면 그대로.

    Parameters
    ----------
    ch : str
        단일 문자.

    Returns
    -------
    str
        초성 자모 1글자. 비한글이면 원문 그대로.
    """
    cp = ord(ch)
    if 0xAC00 <= cp <= 0xD7A3:
        return _CHOSUNG[(cp - _CHO_BASE) // _CHO_PERIOD]
    if ch in _CHOSUNG:
        return ch
    return ch


def _extractChosung(text: str) -> str:
    """문자열의 초성만 추출. 비한글은 원문 그대로.

    Parameters
    ----------
    text : str
        입력 문자열 (예: "삼성전자").

    Returns
    -------
    str
        초성 문자열 (예: "ㅅㅅㅈㅈ").
    """
    return "".join(_decomposeChar(c) for c in text)


def _isAllChosung(text: str) -> bool:
    """입력이 모두 자음(초성)으로만 이루어졌는지 확인.

    Parameters
    ----------
    text : str
        판별할 문자열.

    Returns
    -------
    bool
        전부 초성이면 True.
    """
    return all(c in _CHOSUNG for c in text)


def _levenshtein(s: str, t: str) -> int:
    """최소 편집 거리 (Levenshtein distance).

    삽입·삭제·치환 각 비용 1. Wagner-Fischer 알고리즘.

    Parameters
    ----------
    s : str
        비교 문자열 A.
    t : str
        비교 문자열 B.

    Returns
    -------
    int
        편집 거리 (회).
    """
    if len(s) < len(t):
        s, t = t, s
    if not t:
        return len(s)
    prev = list(range(len(t) + 1))
    for i, sc in enumerate(s):
        curr = [i + 1]
        for j, tc in enumerate(t):
            cost = 0 if sc == tc else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _getSearchCache() -> dict[str, object]:
    """fuzzySearch용 사전 계산 캐시 — 회사명·소문자·초성 목록을 한 번만 계산.

    getKindList() 갱신 시 `registry._invalidateSearchCache()` 가 ``_searchCache`` 를
    None 으로 리셋해 다음 호출에 재계산.

    Returns
    -------
    dict[str, object]
        names : list[str] — 원본 회사명 목록
        names_lower : list[str] — 소문자 변환 회사명 목록
        names_chosung : list[str] — 초성 추출 회사명 목록
    """
    global _searchCache
    if _searchCache is not None:
        return _searchCache

    df = getKindList()
    names = df["회사명"].to_list()
    names_lower = [n.lower() for n in names]
    names_chosung = [_extractChosung(n) for n in names]
    _searchCache = {
        "names": names,
        "names_lower": names_lower,
        "names_chosung": names_chosung,
    }
    return _searchCache


def searchName(keyword: str, *, limit: int | None = None) -> pl.DataFrame:
    """회사명 부분 검색.

    Capabilities: substring 정확 매칭 (대소문자 구분 폴라스 literal).
    AIContext: fuzzy 검색 전 baseline — 사용자 키워드 정확 substring 회사 lookup.
    Guide: fuzzy 매칭 필요 시 fuzzySearch 사용. 본 함수는 literal substring 만.
    When: 키워드가 회사명 일부 (정확) 와 일치 가정 시.
    How: getKindList() → 회사명.str.contains(keyword) → limit slice.

    Args:
        keyword: 검색 키워드 (예: "삼성", "반도체").
        limit: 반환 행수 상한 (가장 위 N). None이면 매칭 전체.

    Returns:
        매칭된 종목 DataFrame (회사명, 종목코드, ...).

    Raises:
        FileNotFoundError: KIND listing cache 미생성 시 ``getKindList`` 가 raise.
        OSError: KIND 페이지 fetch 실패.

    Example:
        >>> df = searchName("삼성", limit=10)
    """
    kw = keyword.strip()
    if not kw:
        return getKindList().head(0)
    df = getKindList()
    result = df.filter(pl.col("회사명").str.contains(kw, literal=True))
    if limit is not None and limit > 0:
        return result.head(limit)
    return result


def fuzzySearch(keyword: str, *, maxResults: int = 10) -> pl.DataFrame:
    """한글 fuzzy 종목 검색 — 초성 매칭 + Levenshtein 거리.

    Capabilities: 초성/약칭/오타/영문 fuzzy 4 단계 점수 매칭 + 관련도 정렬.
    AIContext: 사용자 자연어 입력 ("삼전", "ㅅㅅ", "samsun") → 회사 추론 진입.
    Guide: maxResults 가 None 없음 — 기본 10. 큰 값은 성능 비용 ↑.
    When: AI 챗 / search bar / Skill OS 자연어 입력 처리 시.
    How: 정확 일치 → substring → 초성 subsequence → Levenshtein 거리 4 단계.

    지원:
    - 초성 검색: "ㅅㅅ" → 삼성전자, 삼성물산, ...
    - 약칭 부분매칭: "삼전" → 삼성전자 (초성 "ㅅㅈ" ⊂ "ㅅㅅㅈㅈ")
    - 오타 허용: "삼성전제" → 삼성전자 (편집거리 1)
    - 영문 오타: "samsun" → "samsung"에 가까운 종목
    - 기본 substring 매칭도 포함

    Args:
        keyword: 검색어 (한글, 영문, 초성, 혼합 모두 가능)
        maxResults: 최대 반환 수 (기본 10)

    Returns:
        매칭된 종목 DataFrame (회사명, 종목코드, ...), 관련도 순.

    Raises:
        FileNotFoundError: KIND listing cache 미생성 시 ``getKindList`` 가 raise.
        OSError: KIND 페이지 fetch 실패.

    Example:
        >>> df = fuzzySearch("삼전", maxResults=5)
    """
    kw = keyword.strip()
    if not kw:
        return getKindList().head(0)

    df = getKindList()
    cache = _getSearchCache()
    names: list[str] = cache["names"]
    names_lower: list[str] = cache["names_lower"]
    names_chosung: list[str] = cache["names_chosung"]

    kw_lower = kw.lower()
    kw_chosung = _extractChosung(kw)
    is_chosung_query = _isAllChosung(kw)

    scored: list[tuple[int, float, int]] = []  # (idx, score, order)

    for idx in range(len(names)):
        name_lower = names_lower[idx]

        # 1) 정확 일치
        if name_lower == kw_lower:
            scored.append((idx, 0.0, 0))
            continue

        # 2) substring 매칭
        if kw_lower in name_lower:
            # prefix > contains
            score = 1.0 if name_lower.startswith(kw_lower) else 2.0
            scored.append((idx, score, len(scored)))
            continue

        # 3) 초성 매칭
        name_chosung = names_chosung[idx]
        if is_chosung_query:
            # 순수 초성 입력: "ㅅㅅ" → 초성열에서 연속 매칭
            if kw_chosung in name_chosung:
                # 앞에서 매칭될수록 높은 점수
                pos = name_chosung.index(kw_chosung)
                scored.append((idx, 3.0 + pos * 0.1, len(scored)))
                continue
        else:
            # 혼합 입력: 초성 subsequence 매칭
            # "삼전"(ㅅㅈ) → "삼성전자"(ㅅㅅㅈㅈ) 순서 매칭
            if len(kw) >= 2:
                # 연속 substring 먼저 (더 정확)
                if kw_chosung in name_chosung:
                    pos = name_chosung.index(kw_chosung)
                    scored.append((idx, 4.0 + pos * 0.1, len(scored)))
                    continue
                # subsequence fallback: 글자별 초성이 순서대로 나타나는지
                ci = 0
                first_pos = -1
                for ni, nc in enumerate(name_chosung):
                    if ci < len(kw_chosung) and nc == kw_chosung[ci]:
                        if ci == 0:
                            first_pos = ni
                        ci += 1
                if ci == len(kw_chosung) and first_pos >= 0:
                    # gap penalty: 이름이 짧을수록 좋음
                    scored.append((idx, 4.5 + first_pos * 0.1 + len(names[idx]) * 0.01, len(scored)))
                    continue

        # 4) Levenshtein (짧은 키워드에서만 — 비용 절약)
        if 2 <= len(kw) <= 10:
            dist = _levenshtein(kw_lower, name_lower)
            max_dist = max(1, len(kw) // 3)  # 3자당 1 오타 허용
            if dist <= max_dist:
                scored.append((idx, 5.0 + dist, len(scored)))
                continue

    if not scored:
        return df.head(0)

    scored.sort(key=lambda x: (x[1], x[2]))
    indices = [s[0] for s in scored[:maxResults]]
    return df[indices]
