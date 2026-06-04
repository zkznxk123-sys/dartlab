"""EDGAR 태그 → DART canonical snakeId 매핑 하위 호환 facade.

본체는 ``dartlab.core.accounts.edgar.EdgarTagMapper`` (SSOT 단일 소유). 본 모듈은
기존 import 경로(``EdgarMapper`` / ``STMT_OVERRIDES`` / ``EDGAR_TO_DART_ALIASES``)를
보존하는 *얇은 위임 facade*. 새 코드는 ``dartlab.core.accounts`` 를 직접 import 한다.

매핑 우선순위 (본체):
1. stmtOverrides — 같은 태그가 stmt 따라 다른 snakeId
2. stmtTagMap — stmt 충돌 해소 (commonTags)
3. tagMap — learnedTags + commonTags 병합본 (commonTags 우선)
"""

from __future__ import annotations

from dartlab.core.accounts.data import loadAccounts
from dartlab.core.accounts.edgar import EDGAR_TO_DART_ALIASES, EdgarTagMapper

# 하위 호환 alias — 본체 위임 (classmethod + 인스턴스화 양쪽 보존)
EdgarMapper = EdgarTagMapper


# 옛 STMT_OVERRIDES tuple 형태 재구성 (SSOT "tag|stmt" 디코딩)
def _decodeStmtOverrides() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for key, sid in loadAccounts()["edgar"]["stmtOverrides"].items():
        tag, _, stmt = key.partition("|")
        out[(tag, stmt)] = sid
    return out


STMT_OVERRIDES: dict[tuple[str, str], str] = _decodeStmtOverrides()

__all__ = ["EdgarMapper", "STMT_OVERRIDES", "EDGAR_TO_DART_ALIASES"]
