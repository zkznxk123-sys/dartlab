"""항목 라벨/alias 하위 호환 facade — 본체는 ``dartlab.core.accounts``.

흩어진 라벨 cascade·snakeId alias·SSOT 로더가 ``core/accounts/`` 단일 소유 엔진으로
통합됐다. 본 모듈은 기존 import 경로(``from dartlab.core.utils.labels import ...``)를
깨지 않기 위한 *얇은 re-export shim* 이다. 새 코드는 ``dartlab.core.accounts`` 를
직접 import 한다.
"""

from __future__ import annotations

from dartlab.core.accounts.aliases import SNAKEID_ALIASES, mergeAliasRows
from dartlab.core.accounts.data import loadAccounts as _loadAccountMappings
from dartlab.core.accounts.data import loadSupplements as _loadLabelSupplements
from dartlab.core.accounts.labels import (
    _edgarKorNames as _loadEdgarStandardAccounts,
)
from dartlab.core.accounts.labels import (
    _snakeToTitle,
    resolveLabel,
)
from dartlab.core.accounts.labels import accountLabels as getAccountLabels
from dartlab.core.accounts.labels import englishLabels as getEnglishLabels
from dartlab.core.accounts.labels import koreanLabels as getKoreanLabels
from dartlab.core.accounts.labels import reverseKoreanLabels as getReverseKoreanLabels

# SSOT layers 직접 노출 (옛 module 상수 — 동일 객체 identity 보존)
_EDGAR_LABELS = _loadAccountMappings()["layers"]["labelEn"]
_KR_SYNONYMS = _loadAccountMappings()["layers"]["korSynonym"]


def _loadStandardAccounts() -> dict[str, dict]:
    """{snakeId: {korName, code, level, sj}} — SSOT standardAccounts."""
    return _loadAccountMappings().get("standardAccounts", {})


__all__ = [
    "SNAKEID_ALIASES",
    "mergeAliasRows",
    "getKoreanLabels",
    "getEnglishLabels",
    "getAccountLabels",
    "getReverseKoreanLabels",
    "resolveLabel",
    "_loadAccountMappings",
    "_loadStandardAccounts",
    "_loadEdgarStandardAccounts",
    "_loadLabelSupplements",
    "_EDGAR_LABELS",
    "_KR_SYNONYMS",
    "_snakeToTitle",
]
