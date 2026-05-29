"""Company facade — 시장 무관 단일 진입점 (marketNs → backend dispatch).

sections SSOT 철학: ``c.sections`` 는 sections artifact 구조 board, show/select/
diff/trace 는 그 위 얇은 파생. 재무제표(BS/IS/CIS/CF/SCE)는 finance 정규화로,
report(배당/임원/…)는 report shaping 으로, 그 외(주석·narrative)는 docs sections
contentRaw 로 — `backend.classify(key)` 가 분기.

LLM Specifications:
    AntiPatterns:
        - 옛 docsProfileBuilder board 합성·mapper·source synthetic 행 부활 금지.
        - 시장별 구체 모듈 직접 import 금지 — MarketBackend Protocol 으로만 dispatch.
        - 전체 contentRaw eager materialize 금지 — show 는 per-query lazy filter.
    OutputSchema:
        - ``Company(code, marketNs).sections / sectionsRaw() / show / select / diff / trace``.
    Prerequisites:
        - data/{market}/sections/{code}/*.parquet (BUILD) + finance/report parquet.
    TargetMarkets:
        - KR(DART) 기본. US(EDGAR) 등은 marketNs + backend 추가로 확장.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from dartlab.filings.core.backend import MarketBackend
from dartlab.filings.core.memory import BoundedCache
from dartlab.filings.core.period import periodColumns, sortPeriods
from dartlab.filings.core.schema import PIVOT_INDEX
from dartlab.filings.core.sections import readSectionsMeta, readSectionsWide, scanSections
from dartlab.filings.core.tagstrip import stripExpr

# marketNs → backend (plugin DI — lazy 시장 로드, 미사용 시장 import 회피).
_BACKENDS: dict[str, MarketBackend] = {}


def resolveBackend(marketNs: str) -> MarketBackend:
    """marketNs → MarketBackend 인스턴스 (registry). 미지원 시 ValueError."""
    if marketNs in _BACKENDS:
        return _BACKENDS[marketNs]
    if marketNs == "kr":
        from dartlab.filings.dart import DART

        _BACKENDS["kr"] = DART
        return DART
    raise ValueError(f"미지원 marketNs: {marketNs!r} (현재 'kr' 만)")


class Company:
    """단일 회사 facade — sections SSOT + finance/report 합성.

    Args:
        code: 종목코드 (KR) 또는 ticker/CIK (US).
        marketNs: 시장 namespace ("kr" 기본).

    Example:
        >>> c = Company("005930")          # doctest: +SKIP
        >>> c.show("BS").shape             # doctest: +SKIP  finance 정규화
        >>> c.show("inventoryDisclosure")  # doctest: +SKIP  docs sections
    """

    def __init__(self, code: str, marketNs: str = "kr"):
        self.code = code
        self.marketNs = marketNs
        self._backend = resolveBackend(marketNs)
        self._cache = BoundedCache(maxsize=16)

    # ────────────────────────── sections SSOT ──────────────────────────

    @property
    def sections(self) -> pl.DataFrame | None:
        """sections 구조 board (canonical 키 × period presence) — cheap meta.

        contentRaw 제외 → 데이터 footprint <1MB. 본문은 show 시점 per-query pull.
        """
        if "_meta" in self._cache:
            return self._cache["_meta"]
        m = readSectionsMeta(self.code, marketNs=self.marketNs)
        self._cache["_meta"] = m
        return m

    def sectionsRaw(self, periods: list[str] | None = None) -> pl.DataFrame | None:
        """전체 contentRaw wide board (viewer용 — 큼). canonical 키 × period."""
        return readSectionsWide(self.code, marketNs=self.marketNs, periods=periods, valueColumn="contentRaw")

    # ────────────────────────── show (얇은 파생) ──────────────────────────

    def show(
        self, key: str, *, period: str | None = None, scope: str = "consolidated", raw: bool = False
    ) -> pl.DataFrame | None:
        """topic/key 조회 — backend.classify 로 finance/report/sections 분기.

        Args:
            key: 재무제표 alias(BS/IS/…) / report apiType(dividend/…) / disclosureKey
                / sectionLeaf.
            period: 특정 period (YYYYQn) 만.
            scope: finance 연결/별도 ("consolidated"/"separate").
            raw: True 면 sections contentRaw 태그 보존 (viewer), False 면 plain.

        Returns:
            DataFrame 또는 None.
        """
        kind, params = self._backend.classify(key)
        if kind == "finance":
            df = self._backend.statementWide(self.code, params["sjDiv"], scope=params.get("scope", scope))
            return _filterPeriod(df, period)
        if kind == "report":
            return self._backend.reportTopic(self.code, params["apiType"], period=period)
        return self._showSections(params["key"], period=period, raw=raw)

    def _showSections(self, key: str, *, period: str | None = None, raw: bool = False) -> pl.DataFrame | None:
        """sections per-query — canonical 키 매칭 → period wide (lazy, contentRaw)."""
        lf = scanSections(self.code, marketNs=self.marketNs)
        if lf is None:
            return None
        flt = (pl.col("disclosureKey") == key) | (pl.col("xbrlClass") == key) | (pl.col("sectionLeaf") == key)
        cols = [c for c in PIVOT_INDEX if c] + ["period", "contentRaw"]
        sub = lf.filter(flt).select(cols).collect()
        if sub.is_empty():
            return None
        if period:
            sub = sub.filter(pl.col("period") == period)
            if sub.is_empty():
                return None
        if not raw:
            sub = sub.with_columns(stripExpr("contentRaw"))
        idx = [c for c in PIVOT_INDEX if c in sub.columns]
        wide = sub.pivot(values="contentRaw", index=idx, on="period", aggregate_function="first")
        return wide.select(idx + periodColumns(wide))

    # ────────────────────────── select / diff / trace ──────────────────────────

    def select(self, key: str, indList=None, colList=None, *, scope: str = "consolidated") -> pl.DataFrame | None:
        """show 결과에서 행(indList: label 부분일치) + 열(colList: period 부분집합) 필터."""
        df = self.show(key, scope=scope)
        if df is None:
            return None
        pcols = periodColumns(df)
        labelCols = [c for c in df.columns if c not in pcols]
        out = df
        if indList:
            terms = [indList] if isinstance(indList, str) else list(indList)
            expr = None
            for lc in labelCols:
                for t in terms:
                    e = pl.col(lc).cast(pl.Utf8).str.contains(str(t), literal=True)
                    expr = e if expr is None else (expr | e)
            if expr is not None:
                out = out.filter(expr.fill_null(False))
        if colList:
            cols = {colList} if isinstance(colList, str) else set(colList)
            keepP = [c for c in pcols if c in cols]
            out = out.select(labelCols + keepP)
        return out

    def diff(self, key: str, fromPeriod: str, toPeriod: str, *, scope: str = "consolidated") -> pl.DataFrame | None:
        """show 결과의 두 period 비교 — 값이 변한 행만 (label + from/to)."""
        df = self.show(key, scope=scope)
        if df is None:
            return None
        pcols = periodColumns(df)
        if fromPeriod not in pcols or toPeriod not in pcols:
            return None
        labelCols = [c for c in df.columns if c not in pcols]
        d = df.select(labelCols + [fromPeriod, toPeriod])
        d = d.with_columns(pl.col(fromPeriod).ne_missing(pl.col(toPeriod)).alias("changed"))
        return d.filter(pl.col("changed")).drop("changed")

    def trace(self, key: str, period: str | None = None) -> dict[str, Any]:
        """canonical 키 출처 — kind + (sjDiv/apiType/disclosureKey/xbrlClass/periods)."""
        kind, params = self._backend.classify(key)
        info: dict[str, Any] = {"key": key, "marketNs": self.marketNs, "kind": kind, **params}
        if kind == "sections":
            lf = scanSections(self.code, marketNs=self.marketNs)
            if lf is not None:
                rows = (
                    lf.filter(
                        (pl.col("disclosureKey") == key) | (pl.col("xbrlClass") == key) | (pl.col("sectionLeaf") == key)
                    )
                    .select(["period", "chapter", "sectionLeaf", "xbrlClass", "disclosureKey"])
                    .collect()
                )
                if not rows.is_empty():
                    info["periods"] = sortPeriods(rows["period"].unique().to_list())
                    info["chapter"] = rows["chapter"][0]
                    info["xbrlClass"] = rows["xbrlClass"][0]
                    info["disclosureKey"] = rows["disclosureKey"][0]
                    info["sectionLeaf"] = rows["sectionLeaf"][0]
        return info

    # ────────────────────────── 메모리 가드 ──────────────────────────

    def __enter__(self) -> "Company":
        """context 진입 — multi-company 루프에서 with 블록 권장."""
        return self

    def __exit__(self, *exc: object) -> bool:
        """context 종료 — cache 비움 (Polars 힙 RSS 회수)."""
        self._cache.clear()
        return False

    def __repr__(self) -> str:
        return f"Company({self.code!r}, marketNs={self.marketNs!r})"


def _filterPeriod(df: pl.DataFrame | None, period: str | None) -> pl.DataFrame | None:
    """wide DataFrame 을 단일 period 컬럼으로 좁힘 (label + 해당 period)."""
    if df is None or not period:
        return df
    pcols = periodColumns(df)
    if period not in pcols:
        return df
    labelCols = [c for c in df.columns if c not in pcols]
    return df.select(labelCols + [period])
