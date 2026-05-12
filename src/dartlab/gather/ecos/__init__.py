"""ECOS 경제지표 엔진 — 한국은행 경제통계시스템.

Usage::

    from dartlab.gather.ecos import Ecos

    e = Ecos()                                   # ECOS_API_KEY 환경변수
    cpi = e.series("CPI")                        # CPI 시계열
    compare = e.compare(["CPI", "BASE_RATE"])    # 복수 비교
    cat = e.catalog()                            # 카탈로그
"""

from __future__ import annotations

from .facade import Ecos
from .types import CatalogEntry, EcosError

__all__ = ["CatalogEntry", "Ecos", "EcosError"]
