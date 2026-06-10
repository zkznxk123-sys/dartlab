"""관세청 무역통계 gather — 한국 월별 수출입(산업 사이클 선행지표).

공공데이터포털 관세청_품목별 국가별 수출입실적(GW). 공공누리/KOGL — 출처표시 후
재배포·변형 가능. FRED/ECOS 와 동일 호출계약(.series → date,value).
인증키 `DATA_GO_KR_KEY` (gov·pension 과 단일 공유) — credentials 레지스트리 해석.
"""

from __future__ import annotations

from .catalog import CATALOG, getAllEntries, getEntry
from .facade import Customs
from .types import CatalogEntry, CustomsError, RateLimitError

__all__ = [
    "CATALOG",
    "CatalogEntry",
    "Customs",
    "CustomsError",
    "RateLimitError",
    "getAllEntries",
    "getEntry",
]
