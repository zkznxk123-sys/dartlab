"""finance 계정매퍼 격리 경계 (mapping unit — 나중 통째 swap).

account_id / account_nm → snakeId 해석은 본 패키지 단일 경계. 외부(pivot/scan/
formatter/facade)는 본 __init__ 표면(`AccountMapper` + synonym set)만 의존하고
내부 dict/JSON 에 직접 접근하지 않는다 → 매핑 내부를 통째 교체해도 무영향.

경계 인터페이스: ``AccountMapper.get()`` · ``.map(accountId, accountNm)`` ·
``.labelMap()`` · ``.sortOrder(sjDiv)`` · ``.levelMap(sjDiv)`` · ``.release()``.
"""

from __future__ import annotations

from .mapper import ACCOUNT_NAME_SYNONYMS, ID_SYNONYMS, AccountMapper

__all__ = ["ACCOUNT_NAME_SYNONYMS", "ID_SYNONYMS", "AccountMapper"]
