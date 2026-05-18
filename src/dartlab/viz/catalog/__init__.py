"""viz/catalog — 카드 카탈로그 통합 진입점.

각 도메인 (finance / ratios / valuation / peer ...) 의 dict 를 `CATALOG`
하나로 합쳐서 builder 가 단일 lookup. 새 도메인 추가 시 `register(cards)`
한 줄.
"""

from __future__ import annotations

from dartlab.viz.catalog.finance import FINANCE_CARDS, FINANCE_DASHBOARD_KEYS
from dartlab.viz.catalog.governance import GOVERNANCE_CARDS, GOVERNANCE_KEYS
from dartlab.viz.catalog.lifecycle import LIFECYCLE_CARDS, LIFECYCLE_KEYS
from dartlab.viz.catalog.macro import MACRO_CARDS, MACRO_KEYS
from dartlab.viz.catalog.peer import PEER_CARDS, PEER_KEYS
from dartlab.viz.catalog.portfolio import PORTFOLIO_CARDS, PORTFOLIO_KEYS
from dartlab.viz.catalog.valuation import VALUATION_CARDS, VALUATION_KEYS
from dartlab.viz.schema import CatalogEntry

CATALOG: dict[str, CatalogEntry] = {}
"""모든 카드의 통합 dict. cardKey → CatalogEntry."""


def register(cards: dict[str, CatalogEntry]) -> None:
    """도메인 카드 모음을 전역 CATALOG 에 등록.

    충돌 키는 ValueError — 도메인 간 cardKey 네임스페이스 중복 방지.
    """
    for k, v in cards.items():
        if k in CATALOG:
            raise ValueError(f"viz.catalog cardKey conflict: '{k}' already registered")
        CATALOG[k] = v


register(FINANCE_CARDS)
register(VALUATION_CARDS)
register(PORTFOLIO_CARDS)
register(GOVERNANCE_CARDS)
register(PEER_CARDS)
register(LIFECYCLE_CARDS)
register(MACRO_CARDS)


TAB_KEYS: dict[str, list[str]] = {
    "financial": (
        list(FINANCE_DASHBOARD_KEYS)
        + list(PORTFOLIO_KEYS)
        + list(VALUATION_KEYS)
        + list(GOVERNANCE_KEYS)
        + list(PEER_KEYS)
        + list(LIFECYCLE_KEYS)
        + list(MACRO_KEYS)
    ),
    "viewer": [],
}
"""2 탭 (financial + viewer) → 카드 합집합. 옛 6 탭 (portfolio/valuation/
governance/peer/lifecycle/macro) 은 financial 안의 7 방법론 view (subCategory)
로 흡수됨. 탭별 일괄 빌드 endpoint 는 view 별 query 로 분기."""


# 7 분석 방법론별 카드 키 — viz.__init__ 이 export. subCategory 기준 동적 추출.
def _bySubCategory(sub: str) -> list[str]:
    """CATALOG 안의 subCategory == sub 인 카드키 (등록 순서 보존)."""
    return [k for k, e in CATALOG.items() if e.get("subCategory") == sub]


STORY_KEYS = _bySubCategory("story")
DUPONT_KEYS = _bySubCategory("dupont")
VALUE_KEYS = _bySubCategory("value")
GROWTH_KEYS = _bySubCategory("growth")
CREDIT_KEYS = _bySubCategory("credit")
QUALITY_KEYS = _bySubCategory("quality")
SNOWFLAKE_KEYS = _bySubCategory("snowflake")


def listCards(prefix: str | None = None) -> list[str]:
    """등록된 cardKey 리스트. prefix 로 도메인 필터."""
    keys = list(CATALOG.keys())
    if prefix:
        keys = [k for k in keys if k.startswith(prefix)]
    return keys


__all__ = [
    "CATALOG",
    "FINANCE_CARDS",
    "FINANCE_DASHBOARD_KEYS",
    "GOVERNANCE_CARDS",
    "GOVERNANCE_KEYS",
    "LIFECYCLE_CARDS",
    "LIFECYCLE_KEYS",
    "MACRO_CARDS",
    "MACRO_KEYS",
    "PEER_CARDS",
    "PEER_KEYS",
    "PORTFOLIO_CARDS",
    "PORTFOLIO_KEYS",
    "TAB_KEYS",
    "VALUATION_CARDS",
    "VALUATION_KEYS",
    # 7 분석 방법론별 카드 키 (subCategory 기준 동적 추출)
    "STORY_KEYS",
    "DUPONT_KEYS",
    "VALUE_KEYS",
    "GROWTH_KEYS",
    "CREDIT_KEYS",
    "QUALITY_KEYS",
    "SNOWFLAKE_KEYS",
    "listCards",
    "register",
]
