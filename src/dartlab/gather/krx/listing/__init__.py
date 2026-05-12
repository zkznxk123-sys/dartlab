"""KRX KIND + KRX data + OpenDART 상장법인 목록 — 종목코드 ↔ 회사명 매퍼.

thin facade. 실제 구현은 `registry.py` (등록부 + cache + lookup) 와
`fuzzy.py` (자모 분해 + Levenshtein 검색). 외부 호출자는 본 패키지의
공개 심볼 (`getKindList`, `getDartList`, `getKrxList`, `codeToName`,
`nameToCode`, `searchName`, `fuzzySearch`) 만 사용한다.
"""

from __future__ import annotations

from .fuzzy import fuzzySearch, searchName
from .registry import (
    GatherListingResolver,
    codeToName,
    getDartList,
    getKindList,
    getKrxList,
    nameToCode,
)

__all__ = [
    "GatherListingResolver",
    "codeToName",
    "fuzzySearch",
    "getDartList",
    "getKindList",
    "getKrxList",
    "nameToCode",
    "searchName",
]
