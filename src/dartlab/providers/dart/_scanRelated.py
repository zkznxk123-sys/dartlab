"""DART Company 의 scan-related 메서드 backend.

Company.network / governance / workforce / capital / debt 5 진입점은 모두
``dartlab.scan`` 의 프리빌드 결과를 조회한다. Company facade 가 본 모듈의 build*
함수에 thin delegate.

Module-level helper:
    _ensureNetwork / _ensureGovernance / _ensureWorkforce / _ensureCapital /
    _ensureDebt 는 ``Company._cache`` 에 prebuild 결과 lazy 저장.

Module-level builders:
    buildScanNetwork / buildScanGovernance / buildScanWorkforce /
    buildScanCapital / buildScanDebt — 각 진입점의 본체 구현.

분리 이유: company.py 5040 LOC 의 facade 책임 분산. scan-related 영역 ~450 LOC
가 외부 의존 (dartlab.scan.* prebuild) 이 강해 별도 모듈 분리가 자연스럽다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.memory import _CACHE_MISSING
from dartlab.core.polarsUtil import isEmptyDf

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


# ── ensure helpers (Company._cache lazy 저장) ──────────────────────
# atomic lazy build — cache.get + 로컬 var. set 직후 BoundedCache 의 FATAL 분기
# (just_set_key 보존 없음) 가 unpinned 전부 evict 해도 로컬 var 영향 없음.
# 5 질문 batch audit 의 ``tool debt failed: '_debt'`` race window fix.


def _ensureNetwork(company: Company) -> tuple[dict, dict] | None:
    """network 파이프라인 캐싱 → (data, full)."""
    data = company._cache.get("_network_data", _CACHE_MISSING)
    full = company._cache.get("_network_full", _CACHE_MISSING)
    if data is _CACHE_MISSING or full is _CACHE_MISSING:
        import importlib

        _network = importlib.import_module("dartlab.scan.network")
        buildGraph = _network.buildGraph
        exportFull = _network.exportFull
        data = buildGraph(verbose=False)
        full = exportFull(data)
        company._cache["_network_data"] = data
        company._cache["_network_full"] = full
    return data, full


def _ensureGovernance(company: Company) -> pl.DataFrame | None:
    val = company._cache.get("_governance", _CACHE_MISSING)
    if val is _CACHE_MISSING:
        import importlib

        scanGovernance = importlib.import_module("dartlab.scan.governance").scanGovernance
        val = scanGovernance(verbose=False)
        company._cache["_governance"] = val
    return val


def _ensureWorkforce(company: Company) -> pl.DataFrame | None:
    val = company._cache.get("_workforce", _CACHE_MISSING)
    if val is _CACHE_MISSING:
        import importlib

        scanWorkforce = importlib.import_module("dartlab.scan.workforce").scanWorkforce
        val = scanWorkforce(verbose=False)
        company._cache["_workforce"] = val
    return val


def _ensureCapital(company: Company) -> pl.DataFrame | None:
    val = company._cache.get("_capital", _CACHE_MISSING)
    if val is _CACHE_MISSING:
        import importlib

        scanCapital = importlib.import_module("dartlab.scan.capital").scanCapital
        val = scanCapital(verbose=False)
        company._cache["_capital"] = val
    return val


def _ensureDebt(company: Company) -> pl.DataFrame | None:
    val = company._cache.get("_debt", _CACHE_MISSING)
    if val is _CACHE_MISSING:
        import importlib

        scanDebt = importlib.import_module("dartlab.scan.debt").scanDebt
        val = scanDebt(verbose=False)
        company._cache["_debt"] = val
    return val


# ── view 공통 헬퍼 ─────────────────────────────────────────────────


def companyScanView(company: Company, df: pl.DataFrame | None, view: str | None) -> pl.DataFrame | None:
    """scan DataFrame 에서 view 별 필터.

    None 이면 이 회사 행만, "all" 이면 전체, "market" 이면 시장별 요약.
    """
    if isEmptyDf(df):
        return None
    assert df is not None  # narrowing
    if view == "all":
        return df
    if view == "market":
        return _scanMarketSummary(df)
    # 기본: 이 회사 행
    code = company.stockCode
    codeCol = "종목코드" if "종목코드" in df.columns else "stockCode"
    row = df.filter(pl.col(codeCol) == code)
    return row if not row.is_empty() else None


def _scanMarketSummary(df: pl.DataFrame) -> pl.DataFrame:
    """시장별 요약 통계."""
    import importlib

    loadListing = importlib.import_module("dartlab.scan._helpers").loadListing
    _, _, _, listing_meta = loadListing()
    code_to_market = {code: meta.get("market", "") for code, meta in listing_meta.items()}
    codeCol = "종목코드" if "종목코드" in df.columns else "stockCode"
    df_with_market = df.with_columns(
        pl.col(codeCol)
        .replace_strict(code_to_market, default="미분류")
        .replace("", "미분류")
        .fill_null("미분류")
        .alias("시장")
    )
    numeric_cols = [c for c in df.columns if c != "종목코드" and df[c].dtype in (pl.Float64, pl.Int64)]
    if not numeric_cols:
        return df_with_market.group_by("시장").len()
    aggs = [pl.len().alias("종목수")]
    for c in numeric_cols:
        aggs.append(pl.col(c).mean().alias(f"{c}_평균"))
        aggs.append(pl.col(c).median().alias(f"{c}_중간값"))
    return df_with_market.group_by("시장").agg(aggs).sort("시장")


# ── network ───────────────────────────────────────────────────────


def buildScanNetwork(company: Company, view: str | None = None, *, hops: int = 1):
    """network() 구현."""
    result = _ensureNetwork(company)
    if result is None:
        return None
    data, full = result
    code = company.stockCode
    group = data["code_to_group"].get(code, company.corpName or code)

    if view is None:
        import importlib

        exportEgo = importlib.import_module("dartlab.scan.network").exportEgo
        from dartlab.core.htmlRenderer import getHtmlRenderer

        ego = exportEgo(data, full, code, hops=hops)
        center_name = data["code_to_name"].get(code, code)
        renderer = getHtmlRenderer()
        if renderer is None:
            return None
        return renderer.renderNetwork(
            ego["nodes"],
            ego["edges"],
            f"{center_name} 관계 네트워크",
            centerId=code,
        )
    if view == "members":
        return _networkMembers(data, code, group)
    if view == "edges":
        return _networkEdges(full, code)
    if view == "cycles":
        return _networkCycles(data, code)
    if view == "peers":
        return _networkPeers(data, full, code, hops=hops)
    return None


def _networkMembers(data: dict, code: str, group: str) -> pl.DataFrame:
    """같은 그룹 계열사 목록."""
    members = [n for n in data["all_node_ids"] if data["code_to_group"].get(n) == group]
    rows = []
    for m in sorted(members):
        meta = data["listing_meta"].get(m, {})
        rows.append(
            {
                "종목코드": m,
                "회사명": meta.get("name", m),
                "시장": meta.get("market", ""),
                "업종": meta.get("industry", ""),
                "자기": m == code,
            }
        )
    return pl.DataFrame(rows)


def _networkEdges(full: dict, code: str) -> pl.DataFrame:
    """이 회사의 출자/지분 연결."""
    node_map = {n["id"]: n for n in full["nodes"]}
    rows = []
    for e in full["edges"]:
        if e["type"] == "person_shareholder":
            continue
        if e["source"] == code:
            target = e["target"]
            node = node_map.get(target)
            rows.append(
                {
                    "종목코드": target,
                    "회사명": node["label"] if node else target,
                    "유형": e["type"],
                    "방향": "출자 →",
                    "목적": e.get("purpose", ""),
                    "지분율": e.get("ownershipPct"),
                    "그룹": node["group"] if node else "",
                }
            )
        elif e["target"] == code:
            source = e["source"]
            node = node_map.get(source)
            rows.append(
                {
                    "종목코드": source,
                    "회사명": node["label"] if node else source,
                    "유형": e["type"],
                    "방향": "← 피출자",
                    "목적": e.get("purpose", ""),
                    "지분율": e.get("ownershipPct"),
                    "그룹": node["group"] if node else "",
                }
            )
    if not rows:
        return pl.DataFrame(
            schema={
                "종목코드": pl.Utf8,
                "회사명": pl.Utf8,
                "유형": pl.Utf8,
                "방향": pl.Utf8,
                "목적": pl.Utf8,
                "지분율": pl.Float64,
                "그룹": pl.Utf8,
            }
        )
    return pl.DataFrame(rows).sort("지분율", descending=True, nulls_last=True)


def _networkCycles(data: dict, code: str) -> pl.DataFrame:
    """이 회사가 포함된 순환출자 경로."""
    rows = []
    for i, cy in enumerate(data["cycles"]):
        if code not in cy:
            continue
        path = " → ".join(data["code_to_name"].get(c, c) for c in cy)
        rows.append({"번호": i + 1, "경로": path, "길이": len(cy) - 1})
    if not rows:
        return pl.DataFrame(schema={"번호": pl.Int64, "경로": pl.Utf8, "길이": pl.Int64})
    return pl.DataFrame(rows)


def _networkPeers(data: dict, full: dict, code: str, *, hops: int = 1) -> pl.DataFrame:
    """이 회사 중심 서브그래프 (ego 뷰) → DataFrame."""
    import importlib

    exportEgo = importlib.import_module("dartlab.scan.network").exportEgo
    ego = exportEgo(data, full, code, hops=hops)
    rows = []
    for n in ego["nodes"]:
        if n["type"] != "company":
            continue
        rows.append(
            {
                "종목코드": n["id"],
                "회사명": n["label"],
                "그룹": n["group"],
                "업종": n.get("industry", ""),
                "연결수": n["degree"],
                "자기": n["id"] == code,
            }
        )
    if not rows:
        return pl.DataFrame(
            schema={
                "종목코드": pl.Utf8,
                "회사명": pl.Utf8,
                "그룹": pl.Utf8,
                "업종": pl.Utf8,
                "연결수": pl.Int64,
                "자기": pl.Boolean,
            }
        )
    df = pl.DataFrame(rows)
    return df.sort("연결수", descending=True)


# ── 4 simple builders (governance/workforce/capital/debt) ─────────


def buildScanGovernance(company: Company, view: str | None = None) -> pl.DataFrame | None:
    """governance() 구현."""
    return companyScanView(company, _ensureGovernance(company), view)


def buildScanWorkforce(company: Company, view: str | None = None) -> pl.DataFrame | None:
    """workforce() 구현."""
    return companyScanView(company, _ensureWorkforce(company), view)


def buildScanCapital(company: Company, view: str | None = None) -> pl.DataFrame | None:
    """capital() 구현."""
    return companyScanView(company, _ensureCapital(company), view)


def buildScanDebt(company: Company, view: str | None = None) -> pl.DataFrame | None:
    """debt() 구현."""
    return companyScanView(company, _ensureDebt(company), view)
