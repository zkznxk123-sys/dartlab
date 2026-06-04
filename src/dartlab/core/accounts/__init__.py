"""account 정규화 SSOT 단일 소유 엔진 (L0).

흩어진 5 in-code dict + 34k JSON + EDGAR 데이터를 단일 SSOT
(``reference/data/accountMappings.json``) + 단일 owner 로 통합. DART/EDGAR provider
(L1) 가 합법적으로 import 가능한 유일 계층(L0)에 위치.

공개 표면:

- ``AccountNormalizer`` — DART account → snakeId (12 단계 fallback)
- ``EdgarTagMapper`` — EDGAR tag → snakeId (+ DART alias)
- ``SNAKEID_ALIASES`` / ``mergeAliasRows`` — snakeId alias 통합
- ``koreanLabels`` / ``englishLabels`` / ``reverseKoreanLabels`` / ``accountLabels`` /
  ``resolveLabel`` — 라벨 cascade
- ``loadAccounts`` / ``loadSupplements`` — SSOT 로더
- ``release`` — 전 캐시 무효화 (SSOT 편집 후)
"""

from __future__ import annotations

from dartlab.core.accounts.aliases import SNAKEID_ALIASES, mergeAliasRows
from dartlab.core.accounts.data import loadAccounts, loadSupplements, release
from dartlab.core.accounts.edgar import EDGAR_TO_DART_ALIASES, EdgarTagMapper
from dartlab.core.accounts.labels import (
    accountLabels,
    englishLabels,
    koreanLabels,
    resolveLabel,
    reverseKoreanLabels,
)
from dartlab.core.accounts.normalize import AccountNormalizer, stripPrefix

__all__ = [
    "AccountNormalizer",
    "EdgarTagMapper",
    "EDGAR_TO_DART_ALIASES",
    "SNAKEID_ALIASES",
    "mergeAliasRows",
    "koreanLabels",
    "englishLabels",
    "reverseKoreanLabels",
    "accountLabels",
    "resolveLabel",
    "loadAccounts",
    "loadSupplements",
    "release",
    "stripPrefix",
]
