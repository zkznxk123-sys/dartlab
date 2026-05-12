"""FRED 경제지표 엔진 — 미국 연방준비은행 경제 데이터.

Usage::

    from dartlab.gather.fred import Fred

    f = Fred()                                       # FRED_API_KEY 환경변수
    gdp = f.series("GDP")                            # GDP 시계열
    compare = f.compare(["GDP", "UNRATE"])            # 복수 비교
    corr = f.correlation(["GDP", "UNRATE", "FEDFUNDS"])  # 상관행렬
"""

from __future__ import annotations

from .facade import Fred
from .types import CatalogEntry, FredError, SeriesMeta

__all__ = ["CatalogEntry", "Fred", "FredError", "SeriesMeta"]
