"""레지스트리 DataEntry 카탈로그 — 카테고리별 분할 (Cut 8).

단일 진실의 원천은 각 카테고리 모듈의 list. 본 ``__init__`` 은 합산만 한다.
로직은 ``core/registry.py``.
"""

from __future__ import annotations

from dartlab.core.registry import DataEntry
from dartlab.frame.types.analysis import _ANALYSIS_ENTRIES
from dartlab.frame.types.disclosure import _DISCLOSURE_ENTRIES
from dartlab.frame.types.finance import _FINANCE_ENTRIES
from dartlab.frame.types.notes import _NOTES_ENTRIES
from dartlab.frame.types.raw import _RAW_ENTRIES
from dartlab.frame.types.report import _REPORT_ENTRIES

_ENTRIES: list[DataEntry] = [
    *_FINANCE_ENTRIES,
    *_REPORT_ENTRIES,
    *_DISCLOSURE_ENTRIES,
    *_NOTES_ENTRIES,
    *_RAW_ENTRIES,
    *_ANALYSIS_ENTRIES,
]

# Q1.4 (2026-04-21): business alias 를 entry 별로 쪼개지 않고 단일 맵으로 관리.
# 이 맵은 registry 인덱스 빌드 시 해당 entry 의 `aliases` 튜플과 병합됨.
# 새 alias 추가 = 이 dict 한 줄 추가. DataEntry 선언 수정 불필요.
#
# 과거 company.py 의 하드코딩 dict `_TOPIC_ALIASES` 에서 이관 (26개 중 22개).
# 나머지 4개 (intangible/stock/treasury/invested → intangibleAsset/stockTotal/
# treasuryStock/investedCompany) 는 target entry 가 없어 제외.
_BUSINESS_ALIASES: dict[str, tuple[str, ...]] = {
    "boardOfDirectors": ("board", "directors"),
    "executivePay": ("pay",),
    "majorHolder": ("holder",),
    "holderOverview": ("holders",),
    "shareholderMeeting": ("meeting",),
    "contingentLiability": ("contingent",),
    "relatedPartyTx": ("relatedParty",),
    "riskDerivative": ("risk",),
    "internalControl": ("control",),
    "tangibleAsset": ("tangible",),
    "rawMaterial": ("material",),
    "costByNature": ("cost",),
    "salesOrder": ("sales",),
    "productService": ("product",),
    "investmentInOther": ("investment",),
    "companyOverview": ("overview",),
    "companyHistory": ("history",),
    "articlesOfIncorporation": ("articles",),
    "shareCapital": ("capital",),
    "fsSummary": ("summary",),
}
