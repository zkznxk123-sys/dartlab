"""KRX KIND + KRX data + OpenDART 상장법인 목록 — 종목코드 ↔ 회사명 매퍼.

thin facade. 실제 구현은 4 모듈로 분할:
    - ``registry.py`` — KIND (KOSPI/KOSDAQ) 등록부 + getKindList + codeToName + nameToCode
    - ``dartList.py`` — DART CORPCODE (HF 미러) + getDartList
    - ``krxList.py``  — KRX data.krx + getKrxList
    - ``resolver.py`` — DIP 등록 (import 시 GatherListingResolver 자동 register)

자모 분해·fuzzy 검색은 ``fuzzy.py`` 자매 모듈.

외부 호출자는 본 패키지의 공개 심볼만 사용한다.
"""

from __future__ import annotations

from .dartList import getDartList
from .fuzzy import fuzzySearch, searchName
from .krxList import getKrxList
from .registry import codeToName, getKindList, nameToCode
from .resolver import GatherListingResolver

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
