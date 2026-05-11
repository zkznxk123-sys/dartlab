"""scan 필드 카탈로그와 조건형 스크리닝 실행기.

`scan("fields")` 는 AI와 사용자가 먼저 검색할 수 있는 필드 목록을 제공한다.
`scan("screen", spec=...)` 는 같은 카탈로그의 field 키를 조건으로 받아 후보
종목을 좁힌다. 공개 진입점은 계속 `dartlab.scan()` 하나다.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import polars as pl

_NUMERIC_OPS = ">,>=,<,<=,==,!=,between,exists,not_exists"
_TEXT_OPS = "contains,==,!=,exists,not_exists"
_CONTEXT_OPS = "context"

_KRX_FIELDS: dict[str, tuple[str, str, str]] = {
    "close": ("종가", "원", "latest"),
    "open": ("시가", "원", "latest"),
    "high": ("고가", "원", "latest"),
    "low": ("저가", "원", "latest"),
    "volume": ("거래량", "주", "latest"),
    "amount": ("거래대금", "원", "latest"),
    "marketCap": ("시가총액", "원", "latest"),
    "listShares": ("상장주식수", "주", "latest"),
    "fluctuationRate": ("등락률", "%", "latest"),
    "priceChange": ("전일대비", "원", "latest"),
}

_KRX_INDEX_FIELDS: dict[str, tuple[str, str]] = {
    "close": ("종가지수", "점"),
    "open": ("시가지수", "점"),
    "high": ("고가지수", "점"),
    "low": ("저가지수", "점"),
    "volume": ("거래량", "주"),
    "amount": ("거래대금", "원"),
    "marketCap": ("시가총액", "원"),
    "fluctuationRate": ("등락률", "%"),
}

_REPORT_META = {
    "stockCode",
    "year",
    "quarter",
    "apiType",
    "rcept_no",
    "corp_code",
    "corp_name",
    "corpCode",
    "collectStatus",
    "apiName",
    "corp_cls",
}


def scanFields(query: str | None = None, source: str | None = None) -> pl.DataFrame:
    """scan 스크리닝에 사용할 수 있는 필드 카탈로그를 반환한다.

    Summary
    -------
    `finance`, `report`, `docs`, `krx`, `krxIndex` 필드를 한 표에서 검색한다.

    Description
    -----------
    이 함수는 데이터를 전부 합치지 않는다. 각 원천의 필드 이름, 단위, 허용
    연산자, 커버리지, 실행 예시를 먼저 보여주고, 실제 후보 추출은
    `scan("screen", spec=...)` 가 필요한 필드만 로드한다.

    Parameters
    ----------
    query : str | None
        field, label, notes 에서 찾을 검색어. 예: ``"roe"``, ``"매출"``,
        ``"감사의견"``, ``"rsi"``.
    source : str | None
        원천 필터. ``"finance"``, ``"report"``, ``"docs"``, ``"krx"``,
        ``"krxIndex"``, ``"valuation"`` 중 하나.

    Returns
    -------
    pl.DataFrame
        field : str — `screen` spec 에 넣는 정규 필드 키 (단위 없음).
        label : str — 사람용 한글/영문 라벨 (단위 없음).
        source : str — 데이터 원천 이름 (단위 없음).
        kind : str — ``"number"``, ``"text"``, ``"boolean"``, ``"context"``.
        unit : str — 비교 단위. 원/%/배/건/일/점/주/텍스트/없음.
        operatorSet : str — 허용 연산자 목록.
        coverage : str — 로컬 prebuild 기준 관측 범위 또는 설명.
        example : str — `scan("screen", spec=...)` 에 넣을 조건 예시.
        notes : str — 해석·성능·제약 설명.

    Raises
    ------
    ValueError
        source 값이 카탈로그에 없는 경우.

    Examples
    --------
    >>> dartlab.scan("fields")
    >>> dartlab.scan("fields", "roe")
    >>> dartlab.scan("fields", source="krx")

    Notes
    -----
    report 카탈로그는 메모리 안전을 위해 schema 기준으로 생성한다. non-null
    전수 coverage 계산은 report parquet 전체를 materialize 할 수 있어 기본 경로에서
    수행하지 않는다.

    Guide
    -----
    When: 종목을 찾기 전 어떤 데이터 필드가 있는지 먼저 확인할 때.
    How: fields 로 후보 필드를 찾고, 최소 3개 이상의 서로 다른 관점 조건을
    screen spec 으로 조합한 뒤, 남은 종목만 Company/analysis 로 심층 확인한다.
    Verified: finance/report/docs/krx/krxIndex source 가 단일 표로 노출된다.

    See Also
    --------
    dartlab.scan : scan 단일 진입점.
    dartlab.scan("screen") : 조건형 스크리닝 실행.
    dartlab.search : docs 텍스트 조건의 검색 인덱스 기반 후보 생성.
    """
    df = _catalog()
    if source is not None:
        valid = set(df["source"].to_list())
        if source not in valid:
            raise ValueError(f"source는 {sorted(valid)} 중 하나. 받은 값: {source!r}")
        df = df.filter(pl.col("source") == source)
    if query is not None:
        q = str(query).strip().lower()
        if q:
            df = df.filter(
                pl.any_horizontal(
                    pl.col("field").str.to_lowercase().str.contains(q, literal=True),
                    pl.col("label").str.to_lowercase().str.contains(q, literal=True),
                    pl.col("notes").str.to_lowercase().str.contains(q, literal=True),
                )
            )
    return df


def executeScreenSpec(spec: dict[str, Any]) -> pl.DataFrame:
    """조건 spec 을 실행해 후보 종목 DataFrame 을 반환한다.

    Summary
    -------
    `where` 조건은 AND, `any` 조건은 OR 후보군으로 계산한다.

    Description
    -----------
    필드별 resolver 는 필요한 원천만 lazy 로 로드한다. finance/ratio/valuation/krx
    조건은 종목별 최신 값을 계산해 비교하고, report 조건은 구조화 공시 parquet 을
    필터하며, docs 조건은 검색 인덱스 hit 를 종목 단위로 요약한다.

    Parameters
    ----------
    spec : dict
        ``where``, ``any``, ``select``, ``sort``, ``limit`` 키를 가진 스크리닝
        명세. 최소 조건 형태는
        ``{"where": [{"field": "finance.ratio.roe", "op": ">", "value": 10}]}``.

    Returns
    -------
    pl.DataFrame
        stockCode : str — 후보 종목코드.
        <field> : object — where/select/sort 에서 요청한 필드 값 (필드별 단위).
        docsHitCount : int — docs 조건 hit 수 (건), docs 조건이 있을 때.
        docsBestScore : float — docs 검색 최고 점수 (점), docs 조건이 있을 때.
        docsSnippet : str — 대표 공시 snippet (텍스트), docs 조건이 있을 때.
        dartUrl : str — 대표 DART 링크 (텍스트), docs 조건이 있을 때.

    Raises
    ------
    ValueError
        spec 형식, field, op, unit 이 잘못된 경우.

    Examples
    --------
    >>> dartlab.scan("screen", spec={
    ...     "where": [
    ...         {"field": "finance.ratio.roe", "op": ">", "value": 10},
    ...         {"field": "valuation.pbr", "op": "<", "value": 1},
    ...     ],
    ...     "select": ["krx.marketCap"],
    ...     "sort": {"field": "finance.ratio.roe", "desc": True},
    ...     "limit": 30,
    ... })

    Notes
    -----
    docs 조건은 검색 인덱스 기반 후보 생성이다. 원문 전체에 대한 완전한
    boolean scan 으로 해석하지 않는다.

    Guide
    -----
    When: 넓은 시장에서 후보군을 줄일 때.
    How: 가치·성장·품질·가격·공시 중 최소 3축을 조합하고, 결과 종목은
    Company/analysis 로 원문과 재무제표를 재검증한다.
    Verified: 기존 preset 호출과 독립적으로 spec 경로만 실행된다.

    See Also
    --------
    scanFields : 사용 가능한 필드 검색.
    dartlab.search : docs 조건 후보 생성.
    """
    if not isinstance(spec, dict):
        raise ValueError("screen spec 은 dict 여야 합니다.")

    where = _ensureConditionList(spec.get("where", []), key="where")
    any_conditions = _ensureConditionList(spec.get("any", []), key="any")
    select = _ensureStrList(spec.get("select", []), key="select")
    sort = spec.get("sort")
    limit = int(spec.get("limit", 50))
    if limit <= 0:
        raise ValueError("limit 은 1 이상이어야 합니다.")

    frames: list[pl.DataFrame] = []
    for cond in where:
        frames.append(_conditionFrame(cond, spec))

    if any_conditions:
        any_frames = [_conditionFrame(cond, spec) for cond in any_conditions]
        any_frames = [f for f in any_frames if not f.is_empty()]
        if any_frames:
            frames.append(_unionOnStock(any_frames))
        else:
            return pl.DataFrame({"stockCode": []})

    result = _innerJoinOnStock(frames)

    requested = list(dict.fromkeys(select))
    if sort:
        if not isinstance(sort, dict) or "field" not in sort:
            raise ValueError('sort 는 {"field": "...", "desc": true} 형태여야 합니다.')
        requested.append(str(sort["field"]))

    if result.is_empty() and not frames and requested:
        first = requested[0]
        result = _loadFieldValues(first, spec)
        requested = requested[1:]

    for field in requested:
        if _isContextField(field):
            continue
        if field in result.columns:
            continue
        values = _loadFieldValues(field, spec)
        result = (
            values
            if result.is_empty() and "stockCode" not in result.columns
            else result.join(values, on="stockCode", how="left")
        )

    if result.is_empty() and not frames:
        result = pl.DataFrame({"stockCode": []})

    result = _attachContextFields(result, select + ([str(sort["field"])] if sort else []), spec)

    if sort:
        sort_field = str(sort["field"])
        if sort_field in result.columns:
            result = result.sort(sort_field, descending=bool(sort.get("desc", False)), nulls_last=True)

    return result.head(limit)


@lru_cache(maxsize=1)
def _catalog() -> pl.DataFrame:
    rows: list[dict[str, str]] = []
    rows.extend(_financeCatalogRows())
    rows.extend(_valuationCatalogRows())
    rows.extend(_reportCatalogRows())
    rows.extend(_docsCatalogRows())
    rows.extend(_krxCatalogRows())
    rows.extend(_krxIndexCatalogRows())
    return pl.DataFrame(rows).sort(["source", "field"])


def _row(
    field: str,
    label: str,
    source: str,
    kind: str,
    unit: str,
    operatorSet: str,
    coverage: str,
    notes: str,
) -> dict[str, str]:
    if kind == "number":
        example = f'{{"field": "{field}", "op": ">", "value": 0}}'
    elif kind == "boolean":
        example = f'{{"field": "{field}", "op": "exists"}}'
    elif kind == "context":
        example = f'{{"select": ["{field}"]}}'
    else:
        example = f'{{"field": "{field}", "op": "contains", "value": "키워드"}}'
    return {
        "field": field,
        "label": label,
        "source": source,
        "kind": kind,
        "unit": unit,
        "operatorSet": operatorSet,
        "coverage": coverage,
        "example": example,
        "notes": notes,
    }


def _financeCatalogRows() -> list[dict[str, str]]:
    from dartlab.providers.dart.finance.scanAccount import scanAccountList, scanRatioList

    rows: list[dict[str, str]] = []
    for rec in scanAccountList():
        name = rec["name"]
        label = rec.get("label", name)
        stmt = rec.get("statement", "")
        rows.append(
            _row(
                f"finance.account.{name}",
                label,
                "finance",
                "number",
                "원",
                _NUMERIC_OPS,
                stmt,
                "DART 재무제표 계정. 종목별 최신 기간 값을 비교한다.",
            )
        )
    for rec in scanRatioList():
        name = rec["name"]
        label = rec.get("label", name)
        unit = rec.get("unit", "%")
        rows.append(
            _row(
                f"finance.ratio.{name}",
                label,
                "finance",
                "number",
                unit,
                _NUMERIC_OPS,
                "ratio",
                "DART 재무제표 기반 비율. 종목별 최신 기간 값을 비교한다.",
            )
        )
    return rows


def _valuationCatalogRows() -> list[dict[str, str]]:
    fields = {
        "marketCap": ("시가총액", "원"),
        "per": ("PER", "배"),
        "pbr": ("PBR", "배"),
        "psr": ("PSR", "배"),
        "dividendYield": ("배당수익률", "%"),
        "current": ("현재가", "원"),
    }
    return [
        _row(
            f"valuation.{name}",
            label,
            "valuation",
            "number",
            unit,
            _NUMERIC_OPS,
            "daily snapshot",
            "일일 prebuild 밸류에이션 snapshot 기반 최신 값.",
        )
        for name, (label, unit) in fields.items()
    ]


def _reportCatalogRows() -> list[dict[str, str]]:
    from dartlab.core.dataLoader import _dataDir
    from dartlab.providers.dart.report.types import API_TYPE_LABELS, API_TYPES

    rows: list[dict[str, str]] = []
    scan_dir = Path(_dataDir("scan"))
    report_dir = scan_dir / "report"
    for apiType in API_TYPES:
        label = API_TYPE_LABELS.get(apiType, apiType)
        rows.append(
            _row(
                f"report.{apiType}.__exists__",
                f"{label} 존재",
                "report",
                "boolean",
                "없음",
                "exists,not_exists,==,!=",
                "apiType",
                "OpenDART 구조화 공시 API type 존재 여부.",
            )
        )
        path = report_dir / f"{apiType}.parquet"
        if not path.exists():
            continue
        try:
            cols = pl.scan_parquet(str(path)).collect_schema().names()
        except (OSError, pl.exceptions.PolarsError):
            continue
        for col in cols:
            if col in _REPORT_META:
                continue
            rows.append(
                _row(
                    f"report.{apiType}.{col}",
                    f"{label}.{col}",
                    "report",
                    "text",
                    "텍스트",
                    "contains,>,>=,<,<=,==,!=,between,exists,not_exists",
                    "prebuild",
                    "구조화 공시 원천 컬럼. schema 기준 노출이며 숫자 비교 시 문자열 숫자를 파싱한다.",
                )
            )
    return rows


def _docsCatalogRows() -> list[dict[str, str]]:
    return [
        _row(
            "docs.content",
            "공시 본문",
            "docs",
            "text",
            "텍스트",
            "contains,==",
            "search index",
            "본문 검색 인덱스 hit 기반 후보 생성.",
        ),
        _row(
            "docs.title",
            "공시 제목/섹션",
            "docs",
            "text",
            "텍스트",
            "contains,==",
            "search index",
            "보고서명·섹션명 검색 인덱스 기반 후보 생성.",
        ),
        _row(
            "docs.report",
            "보고서명",
            "docs",
            "text",
            "텍스트",
            "contains,==",
            "search index",
            "보고서명 검색 후보 생성.",
        ),
    ]


def _krxCatalogRows() -> list[dict[str, str]]:
    from dartlab.gather.transforms.indicatorDispatch import _DEFAULT_INDICATORS_ALL

    rows = [
        _row(
            f"krx.{name}",
            label,
            "krx",
            "number",
            unit,
            _NUMERIC_OPS,
            coverage,
            "KRX 가격/거래 raw 최신값. 기본 window 는 252 거래일이다.",
        )
        for name, (label, unit, coverage) in _KRX_FIELDS.items()
    ]
    for name in _DEFAULT_INDICATORS_ALL:
        rows.append(
            _row(
                f"krx.{name}",
                name,
                "krx",
                "number",
                "점",
                _NUMERIC_OPS,
                "window=252",
                "KRX OHLCV 기반 기술지표. start/end 미지정 시 최근 252 거래일 window 를 사용한다.",
            )
        )
    return rows


def _krxIndexCatalogRows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for market in ("KRX", "KOSPI", "KOSDAQ"):
        for name, (label, unit) in _KRX_INDEX_FIELDS.items():
            rows.append(
                _row(
                    f"krxIndex.{market}.{name}",
                    f"{market} {label}",
                    "krxIndex",
                    "context",
                    unit,
                    _CONTEXT_OPS,
                    "latest",
                    "시장 지수 컨텍스트. 종목별 필터가 아니라 결과 컬럼으로만 붙인다.",
                )
            )
    return rows


def _ensureConditionList(value: Any, *, key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key} 는 condition dict 리스트여야 합니다.")
    for cond in value:
        if not isinstance(cond, dict):
            raise ValueError(f"{key} 의 각 항목은 dict 여야 합니다.")
    return value


def _ensureStrList(value: Any, *, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key} 는 문자열 리스트여야 합니다.")
    return [str(v) for v in value]


def _conditionFrame(cond: dict[str, Any], spec: dict[str, Any]) -> pl.DataFrame:
    field = _normalizeField(str(cond.get("field", "")))
    meta = _fieldMeta(field)
    if meta["kind"] == "context":
        raise ValueError(
            f"{field!r} 는 시장 컨텍스트 필드라 종목 필터 조건으로 사용할 수 없습니다. select 에 넣으세요."
        )
    if "unit" in cond and str(cond["unit"]) != meta["unit"]:
        raise ValueError(f"{field!r} 단위는 {meta['unit']} 입니다. 받은 unit={cond['unit']!r}")
    if field.startswith("docs."):
        return _docsConditionValues(cond, spec)
    values = _loadFieldValues(field, spec)
    return _applyCondition(values, field, cond, meta)


def _normalizeField(field: str) -> str:
    f = field.strip()
    if not f:
        raise ValueError("condition field 가 비어 있습니다.")
    aliases = {
        "roe": "finance.ratio.roe",
        "roa": "finance.ratio.roa",
        "pbr": "valuation.pbr",
        "per": "valuation.per",
        "psr": "valuation.psr",
        "marketCap": "krx.marketCap",
        "시가총액": "krx.marketCap",
        "매출액": "finance.account.sales",
    }
    return aliases.get(f, f)


def _fieldMeta(field: str) -> dict[str, str]:
    catalog = _catalog()
    hit = catalog.filter(pl.col("field") == field)
    if hit.is_empty():
        examples = ", ".join(catalog["field"].head(8).to_list())
        raise ValueError(f"알 수 없는 scan field: {field!r}. dartlab.scan('fields') 로 확인하세요. 예: {examples}")
    return hit.row(0, named=True)


def _loadFieldValues(field: str, spec: dict[str, Any]) -> pl.DataFrame:
    field = _normalizeField(field)
    _fieldMeta(field)
    if field.startswith("finance.account."):
        return _loadFinanceAccount(field)
    if field.startswith("finance.ratio."):
        return _loadFinanceRatio(field)
    if field.startswith("valuation."):
        return _loadValuation(field)
    if field.startswith("report."):
        return _loadReport(field)
    if field.startswith("docs."):
        raise ValueError("docs 필드는 where 조건의 value 로 검색어를 지정해야 합니다.")
    if field.startswith("krx."):
        return _loadKrx(field, spec)
    if field.startswith("krxIndex."):
        raise ValueError("krxIndex 필드는 select 전용 시장 컨텍스트입니다.")
    raise ValueError(f"지원하지 않는 field source: {field!r}")


def _loadFinanceAccount(field: str) -> pl.DataFrame:
    from dartlab.providers.dart.finance.scanAccount import scanAccount

    name = field.split(".", 2)[2]
    df = scanAccount(name)
    return _latestWideValue(df, field)


def _loadFinanceRatio(field: str) -> pl.DataFrame:
    from dartlab.providers.dart.finance.scanAccount import scanRatio

    name = field.split(".", 2)[2]
    df = scanRatio(name)
    return _latestWideValue(df, field)


def _latestWideValue(df: pl.DataFrame, field: str) -> pl.DataFrame:
    if df is None or df.is_empty() or "stockCode" not in df.columns:
        return pl.DataFrame({"stockCode": [], field: []})
    period_cols = sorted([c for c in df.columns if c != "stockCode"], reverse=True)
    if not period_cols:
        return pl.DataFrame({"stockCode": [], field: []})
    return df.select("stockCode", pl.coalesce([pl.col(c) for c in period_cols]).alias(field))


def _loadValuation(field: str) -> pl.DataFrame:
    name = field.split(".", 1)[1]
    if name != "psr":
        from dartlab.scan.parquetLoad import loadValuationSnapshot

        raw, _snapshot_at = loadValuationSnapshot()
        if raw is not None and not raw.is_empty() and name in raw.columns:
            return raw.select("stockCode", pl.col(name).alias(field))

    from dartlab.scan.valuation import scanValuation

    df = scanValuation(verbose=False)
    if df is None or df.is_empty() or name not in df.columns:
        return pl.DataFrame({"stockCode": [], field: []})
    return df.select("stockCode", pl.col(name).alias(field))


def _loadReport(field: str) -> pl.DataFrame:
    from dartlab.scan.parquetLoad import scanParquets

    _, apiType, col = field.split(".", 2)
    if col == "__exists__":
        raw = _loadReportExists(apiType)
        if raw.is_empty():
            return pl.DataFrame({"stockCode": [], field: []})
        return raw.select("stockCode").unique().with_columns(pl.lit(True).alias(field))

    raw = scanParquets(apiType, ["stockCode", "year", "quarter", col])
    if raw.is_empty() or col not in raw.columns or "stockCode" not in raw.columns:
        return pl.DataFrame({"stockCode": [], field: []})
    raw = _latestByStock(raw)
    return raw.select("stockCode", pl.col(col).alias(field))


def _loadReportExists(apiType: str) -> pl.DataFrame:
    from dartlab.core.dataLoader import _dataDir
    from dartlab.scan.parquetLoad import _ensureScanData

    scan_path = _ensureScanData() / "report" / f"{apiType}.parquet"
    if scan_path.exists():
        try:
            return pl.scan_parquet(str(scan_path)).select("stockCode").collect()
        except (OSError, pl.exceptions.PolarsError):
            return pl.DataFrame()

    report_dir = Path(_dataDir("report"))
    frames = []
    for pf in sorted(report_dir.glob("*.parquet")):
        try:
            lf = pl.scan_parquet(str(pf))
            if "apiType" not in lf.collect_schema().names():
                continue
            frames.append(lf.filter(pl.col("apiType") == apiType).select("stockCode"))
        except (OSError, pl.exceptions.PolarsError):
            continue
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames).collect()


def _latestByStock(df: pl.DataFrame) -> pl.DataFrame:
    sort_cols = [c for c in ("stockCode", "year", "quarter") if c in df.columns]
    if "stockCode" not in sort_cols:
        return df
    return df.sort(sort_cols).group_by("stockCode").tail(1)


def _docsConditionValues(cond: dict[str, Any], spec: dict[str, Any]) -> pl.DataFrame:
    field = _normalizeField(str(cond.get("field", "")))
    op = str(cond.get("op", "contains"))
    if op not in {"contains", "=="}:
        raise ValueError("docs 조건은 contains 또는 == 만 지원합니다.")
    query = str(cond.get("value", "")).strip()
    if not query:
        raise ValueError("docs 조건 value 에 검색어가 필요합니다.")
    scope = "content" if field == "docs.content" else "title"
    top_k = int(cond.get("limit", spec.get("docsTopK", 500)))

    from dartlab.providers.dart.search import search

    hits = search(query, limit=top_k, scope=scope)
    if hits is None or hits.is_empty() or "info" in hits.columns:
        return pl.DataFrame({"stockCode": [], field: []})
    sc_col = "stock_code" if "stock_code" in hits.columns else "stockCode" if "stockCode" in hits.columns else None
    if sc_col is None:
        return pl.DataFrame({"stockCode": [], field: []})
    text_col = "text" if "text" in hits.columns else "section_title" if "section_title" in hits.columns else sc_col
    score_expr = (
        pl.col("score").max().alias("docsBestScore") if "score" in hits.columns else pl.lit(None).alias("docsBestScore")
    )
    url_expr = (
        pl.col("dartUrl").first().alias("dartUrl") if "dartUrl" in hits.columns else pl.lit(None).alias("dartUrl")
    )
    return (
        hits.rename({sc_col: "stockCode"})
        .group_by("stockCode")
        .agg(
            pl.len().alias("docsHitCount"),
            score_expr,
            pl.col(text_col).first().alias("docsSnippet"),
            url_expr,
        )
        .with_columns(pl.lit(True).alias(field))
    )


def _loadKrx(field: str, spec: dict[str, Any]) -> pl.DataFrame:
    name = field.split(".", 1)[1]
    start = spec.get("start")
    end = spec.get("end")
    if start is None and end is None and name in _KRX_FIELDS:
        raw = _loadKrxLatestYear()
    else:
        end_date = date.today()
        if start is None and end is None:
            start = (end_date - timedelta(days=int(spec.get("windowDays", 420)))).isoformat()
            end = end_date.isoformat()
        raw = _loadKrxWindow(start=start, end=end)
    if raw is None or raw.is_empty():
        return pl.DataFrame({"stockCode": [], field: []})
    return _finalizeKrxValues(raw, name, field)


def _loadKrxLatestYear() -> pl.DataFrame:
    from dartlab.gather.bulkData.hfBulk import loadFiltered

    this_year = date.today().year
    raw = loadFiltered(year=this_year, adjustment="raw")
    if raw is None or raw.is_empty():
        raw = loadFiltered(year=this_year - 1, adjustment="raw")
    return raw


def _loadKrxWindow(*, start: str | None, end: str | None) -> pl.DataFrame:
    from dartlab.gather.bulkData.hfBulk import loadFiltered

    return loadFiltered(start=start, end=end, adjustment="raw")


def _finalizeKrxValues(raw: pl.DataFrame, name: str, field: str) -> pl.DataFrame:
    from dartlab.gather.krx.krxApi import _KRX_TO_STD

    rename = {k: v for k, v in _KRX_TO_STD.items() if k in raw.columns}
    df = raw.rename(rename).sort(["stockCode", "date"])
    if name not in df.columns:
        from dartlab.gather.transforms.indicatorDispatch import computeIndicator

        df = df.with_columns(computeIndicator(df, name).alias(name))
    if name not in df.columns:
        raise ValueError(f"KRX field {field!r} 를 계산할 수 없습니다.")
    return df.group_by("stockCode").agg(pl.col(name).last().alias(field))


def _applyCondition(df: pl.DataFrame, field: str, cond: dict[str, Any], meta: dict[str, str]) -> pl.DataFrame:
    if df.is_empty():
        return df
    op = str(cond.get("op", "=="))
    allowed = set(meta["operatorSet"].split(","))
    if op not in allowed:
        raise ValueError(f"{field!r} 에서 op={op!r} 는 지원하지 않습니다. 가용: {meta['operatorSet']}")
    if op == "exists":
        return df.filter(pl.col(field).is_not_null())
    if op == "not_exists":
        return df.filter(pl.col(field).is_null())
    if "value" not in cond:
        raise ValueError(f"{field!r} 조건에는 value 가 필요합니다.")

    value = cond["value"]
    if meta["kind"] == "number" or _looksNumeric(value):
        expr = _numericExpr(field)
        if op == ">":
            return df.filter(expr > float(value))
        if op == ">=":
            return df.filter(expr >= float(value))
        if op == "<":
            return df.filter(expr < float(value))
        if op == "<=":
            return df.filter(expr <= float(value))
        if op == "==":
            return df.filter(expr == float(value))
        if op == "!=":
            return df.filter(expr != float(value))
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("between value 는 [min, max] 형태여야 합니다.")
            return df.filter(expr.is_between(float(value[0]), float(value[1])))

    text = pl.col(field).cast(pl.Utf8)
    if op == "contains":
        return df.filter(text.str.contains(str(value), literal=True))
    if op == "==":
        return df.filter(text == str(value))
    if op == "!=":
        return df.filter(text != str(value))
    raise ValueError(f"{field!r} 에서 op={op!r} 를 적용할 수 없습니다.")


def _numericExpr(field: str) -> pl.Expr:
    return (
        pl.col(field)
        .cast(pl.Utf8, strict=False)
        .str.replace_all(",", "")
        .str.replace_all("%", "")
        .str.replace_all("배", "")
        .cast(pl.Float64, strict=False)
    )


def _looksNumeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _innerJoinOnStock(frames: list[pl.DataFrame]) -> pl.DataFrame:
    frames = [f for f in frames if f is not None]
    if not frames:
        return pl.DataFrame()
    result = frames[0]
    for frame in frames[1:]:
        result = result.join(frame, on="stockCode", how="inner")
    return result


def _unionOnStock(frames: list[pl.DataFrame]) -> pl.DataFrame:
    all_cols = sorted({c for frame in frames for c in frame.columns})
    padded = []
    for frame in frames:
        missing = [c for c in all_cols if c not in frame.columns]
        if missing:
            frame = frame.with_columns([pl.lit(None).alias(c) for c in missing])
        padded.append(frame.select(all_cols))
    return pl.concat(padded, how="diagonal_relaxed").unique(subset=["stockCode"], keep="first")


def _isContextField(field: str) -> bool:
    return _normalizeField(field).startswith("krxIndex.")


def _attachContextFields(df: pl.DataFrame, fields: list[str], spec: dict[str, Any]) -> pl.DataFrame:
    for field in dict.fromkeys(_normalizeField(f) for f in fields if f):
        if not field.startswith("krxIndex."):
            continue
        value = _loadKrxIndexScalar(field, spec)
        df = df.with_columns(pl.lit(value).alias(field))
    return df


def _loadKrxIndexScalar(field: str, spec: dict[str, Any]) -> float | int | str | None:
    _, market, name = field.split(".", 2)
    start = spec.get("start")
    end = spec.get("end")
    if start is None and end is None:
        year = date.today().year
        raw = _loadKrxIndexYear(market=market, year=year)
        if raw is None or raw.is_empty():
            raw = _loadKrxIndexYear(market=market, year=year - 1)
    else:
        from dartlab.gather.bulkData.hfIndexBulk import loadFiltered

        raw = loadFiltered(market=market, start=start, end=end)
    if raw is None or raw.is_empty():
        return None

    return _finalizeKrxIndexScalar(raw, name, spec)


def _loadKrxIndexYear(*, market: str, year: int) -> pl.DataFrame:
    from dartlab.gather.bulkData.hfIndexBulk import loadFiltered

    return loadFiltered(market=market, year=year)


def _finalizeKrxIndexScalar(raw: pl.DataFrame, name: str, spec: dict[str, Any]) -> float | int | str | None:
    from dartlab.gather.krx.krxIndex import _KRX_TO_STD

    rename = {k: v for k, v in _KRX_TO_STD.items() if k in raw.columns}
    df = raw.rename(rename).sort("date")
    target_index = spec.get("indexName")
    if target_index and "indexName" in df.columns:
        df = df.filter(pl.col("indexName") == target_index)
    if df.is_empty() or name not in df.columns:
        return None
    return df[name][-1]


__all__ = ["executeScreenSpec", "scanFields"]
