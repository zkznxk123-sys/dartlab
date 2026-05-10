"""자연어 종목 추출 — CLI, Python API, Server 공통 원소스.

사용법::

    from dartlab.core.resolve import resolve_from_text, resolve_alias

    # 자연어에서 종목+질문 분리
    company, question = resolve_from_text("삼성전자 재무건전성 분석해줘")
    # company = Company("삼성전자"), question = "재무건전성 분석해줘"

    # 약칭 → 정식명
    resolve_alias("삼전")  # "삼성전자"
"""

from __future__ import annotations

import re

_RESOLVE_ERRORS = (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError)

COMPANY_SUFFIXES = (
    "차",
    "전자",
    "그룹",
    "건설",
    "화학",
    "제약",
    "바이오",
    "증권",
    "보험",
    "은행",
    "금융",
    "지주",
    "산업",
    "통신",
    "에너지",
)

COMMON_ALIASES: dict[str, str] = {
    "삼전": "삼성전자",
    "현차": "현대자동차",
    "현대차": "현대자동차",
    "기차": "기아",
    "삼바": "삼성바이오로직스",
    "삼성바이오": "삼성바이오로직스",
    "셀트리온헬스케어": "셀트리온",
    "네이버": "NAVER",
    "포스코": "포스코홀딩스",
    "에코프로": "에코프로비엠",
    "LG엔솔": "LG에너지솔루션",
    "엔솔": "LG에너지솔루션",
    "카뱅": "카카오뱅크",
    "카페": "카카오",
    "하이닉스": "SK하이닉스",
}


_KR_PARTICLES = re.compile(
    r"(의|은|는|이|가|을|를|에|에서|와|과|로|으로|도|만|까지|부터|에게|한테|처럼|보다|라고|이라고)$"
)


def stripParticles(text: str) -> str:
    """한국어 조사를 제거한다. 예: '하이닉스의' → '하이닉스'."""
    return _KR_PARTICLES.sub("", text)


def resolveAlias(text: str) -> str | None:
    """COMMON_ALIASES에서 매칭되는 정식 종목명 반환. 조사 제거 후 재시도. 없으면 None."""
    result = COMMON_ALIASES.get(text)
    if result:
        return result
    stripped = stripParticles(text)
    if stripped != text:
        return COMMON_ALIASES.get(stripped)
    return None


def collectCandidates(query: str, *, strict: bool) -> list[dict[str, str]]:
    """검색 결과에서 매칭되는 후보를 수집한다.

    strict=True: 정확히 일치하거나 prefix 관계만 허용
    strict=False: 부분 포함도 허용 (fuzzy — 초성/Levenshtein 포함)
    """
    if len(query) < 2:
        return []
    # ListingResolver registry 사용 (정공법 B — DIP). gather 직접 import 0.
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        df = None
    else:
        df = resolver.search(query)
        if df is not None and len(df) == 0:
            df = None

    exact: list[dict[str, str]] = []
    prefix: list[dict[str, str]] = []
    contains: list[dict[str, str]] = []

    if df is not None:
        for row in df.to_dicts()[:10]:
            name = row.get("회사명", row.get("corpName", ""))
            code = row.get("종목코드", row.get("stockCode", ""))
            if not code:
                continue
            entry = {"corpName": name, "stockCode": code}
            if name == query:
                exact.append(entry)
            elif name.startswith(query) or query.startswith(name):
                prefix.append(entry)
            elif len(query) >= 3 and query in name:
                contains.append(entry)

    result = exact + prefix + contains

    # fuzzy fallback: substring 매칭이 없으면 ListingResolver fuzzy 시도 (정공법 B — DIP).
    if not result and not strict and resolver is not None:
        fuzzyDf = resolver.fuzzy(query, maxResults=5)
        if fuzzyDf is not None and len(fuzzyDf) > 0:
            seen = {e["stockCode"] for e in result}
            for row in fuzzyDf.to_dicts():
                name = row.get("회사명", row.get("corpName", ""))
                code = row.get("종목코드", row.get("stockCode", ""))
                if code and code not in seen:
                    seen.add(code)
                    result.append({"corpName": name, "stockCode": code})

    return result


def searchSuggestions(question: str) -> list[dict[str, str]]:
    """질문에서 단어를 추출하여 비슷한 종목 후보를 검색한다.

    ListingResolver registry (정공법 B — DIP) 사용. core 가 dartlab/gather 직접 import 0.
    """
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        return []

    words = re.split(r"\s+", question)
    seen_codes: set[str] = set()
    suggestions: list[dict[str, str]] = []

    for word in words:
        if len(word) < 2:
            continue
        queries = [word]
        for suffix in COMPANY_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix):
                queries.append(word[: -len(suffix)])
        for q in queries:
            try:
                df = resolver.search(q)
                if df is None:
                    continue
                for row in df.head(3).to_dicts():
                    code = row.get("종목코드", row.get("stockCode", ""))
                    name = row.get("회사명", row.get("corpName", ""))
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        suggestions.append({"corpName": name, "stockCode": code})
                        if len(suggestions) >= 5:
                            return suggestions
            except _RESOLVE_ERRORS:
                continue
    return suggestions


def resolveStockCodeFromText(text: str) -> tuple[str | None, str]:
    """자연어 텍스트에서 stockCode/ticker 와 남은 질문을 분리한다.

    core layer 책임 — Company 인스턴스 생성은 호출자 (dartlab.company.resolveFromText) 책임.

    Returns:
        (stockCode | ticker | None, remaining_question)
    """
    text = text.strip()
    if not text:
        return None, text

    # 1) 6자리 종목코드 먼저
    code_match = re.match(r"^(\d{6})\s+(.+)$", text)
    if code_match:
        return code_match.group(1), code_match.group(2).strip()

    # 2) US ticker 패턴 (대문자 1~5글자 + 공백 + 나머지)
    ticker_match = re.match(r"^([A-Z]{1,5})\s+(.+)$", text)
    if ticker_match:
        return ticker_match.group(1), ticker_match.group(2).strip()

    # 3) 약칭/회사명 (단어 조합, 긴 것 우선) — alias 우선, 매칭 1 개면 채택
    words = text.split()
    for length in range(min(4, len(words)), 0, -1):
        for i in range(len(words) - length + 1):
            candidate = " ".join(words[i : i + length])
            remaining_parts = words[:i] + words[i + length :]
            remaining = " ".join(remaining_parts).strip()

            stripped = stripParticles(candidate)
            for term in dict.fromkeys([stripped, candidate]):
                alias = COMMON_ALIASES.get(term)
                if alias:
                    return alias, remaining if remaining else candidate

            for term in dict.fromkeys([stripped, candidate]):
                candidates = collectCandidates(term, strict=True)
                if candidates:
                    break
            else:
                candidates = []
            if len(candidates) == 1:
                return candidates[0]["stockCode"], remaining if remaining else candidate

            exact = [c for c in candidates if c["corpName"] == candidate]
            if len(exact) == 1:
                return exact[0]["stockCode"], remaining if remaining else candidate

    return None, text
