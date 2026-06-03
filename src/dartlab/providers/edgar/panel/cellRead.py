"""EDGAR native 셀 read — panelCell artifact → 계정×기간 wide (DART ``cell.readStatement`` 계약 동형).

DART 의 ``c.panel("is")`` 가 ``[account, label, *period]`` wide 를 내듯, EDGAR 도 **동일 공개 계약**으로
``data/edgar/panelCell/{ticker}.parquet`` 셀을 계정×기간 wide 로 낸다. freq 토큰 선택·period 라벨은 DART
``cell._freqMask``/``_periodLabelExpr`` (소스중립 순수)를 **재사용**해 계약 의미 동일 보장. account 는
us-gaap concept → snakeId(``EdgarMapper``) 통합(taxonomy 진화 SalesRevenueNet↔RevenueFromContract 흡수).

native(소문자 ``c.panel("is")``) = 이 필링 inline/INS XBRL 셀(deep history) / finance(대문자 ``c.panel("IS")``)
= companyfacts — DART native/finance 대칭.

LLM Specifications:
    AntiPatterns:
        - 출력 컬럼 DART 계약과 다르게 금지 — ``[account, label, *period]`` (period 최신 좌측).
        - freq 의미 재정의 금지 — DART ``_freqMask`` 재사용(동일 토큰 선택).
        - axis 차원 행 혼입 금지 — top-level(axisPath="") 만 statement view.
    OutputSchema:
        - ``readNative(ticker, *, statement, freq, scope, periods) -> pl.DataFrame | None``.
    Prerequisites:
        - polars. panelCell artifact. dart.panel.cell(_freqMask/_periodLabelExpr). EdgarMapper. core.ratios.
    Freshness:
        - 매 read (artifact 변경 즉시).
    Dataflow:
        - panelCell parquet → freq/scope/top-level filter → snakeId account → period pivot.
    TargetMarkets:
        - US (EDGAR).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# 논리 키(사용자) → EDGAR 물리 statement. DART STATEMENT_VARIANTS 의 EDGAR 짝(변형 없음 — 1:1).
_LOGICAL_TO_STMT: dict[str, str] = {"is": "IS", "bs": "BS", "cf": "CF", "cis": "CIS", "sce": "EF"}
# 비율 재료 버킷 → 논리 키 (DART _RATIO_SOURCE 동형).
_RATIO_SOURCE: dict[str, str] = {"BS": "bs", "IS": "is", "CF": "cf"}


def _cellPath(ticker: str) -> Path:
    return Path(_cfg.dataDir) / "edgar" / "panelCell" / f"{ticker.upper()}.parquet"


def _loadCells(ticker: str, periods: list[str] | None) -> pl.DataFrame | None:
    """panelCell artifact read (HF lazy 다운로드 포함, period filter). 부재 시 None."""
    from dartlab.providers.dart.panel.read import ensurePanelFromHf

    ensurePanelFromHf(ticker, "us")  # 보드+셀 동반 다운로드 (read.ensurePanelFromHf us 분기)
    p = _cellPath(ticker)
    if not p.exists():
        return None
    try:
        df = pl.read_parquet(str(p))
    except (OSError, pl.exceptions.PolarsError) as exc:
        _log.warning("edgar panelCell read 실패 %s: %s", ticker, exc)
        return None
    if periods:
        df = df.filter(pl.col("filingPeriod").is_in(list(periods)))
    return df if not df.is_empty() else None


def _accountColumn(df: pl.DataFrame, statement: str) -> pl.DataFrame:
    """concept(us-gaap local-name) → snakeId account 컬럼 (EdgarMapper, taxonomy 진화 통합).

    SalesRevenueNet·RevenueFromContractWithCustomer… 처럼 era 마다 다른 concept 를 같은 snakeId 로 통합
    (DART _stitchRecentName 의 EDGAR 짝 — concept→snakeId 매핑 기반). 미매핑은 concept 유지.
    """
    try:
        from dartlab.providers.edgar.finance.mapper import EdgarMapper

        mapper = EdgarMapper()
        concepts = df["concept"].unique().to_list()
        mp = {c: (mapper.mapToDart(c, statement) or c) for c in concepts if c}
    except Exception:  # noqa: BLE001 — 매퍼 부재/실패 시 concept 그대로(graceful)
        return df.with_columns(pl.col("concept").alias("account"))
    return df.with_columns(pl.col("concept").replace(mp).alias("account"))


def _statementWide(df: pl.DataFrame, *, statement: str, freq: str, scope: str) -> pl.DataFrame | None:
    """셀 DataFrame → 계정×기간 wide ([account, label, *period]). DART _statementFromCells 계약 동형."""
    from dartlab.providers.dart.panel.cell import _freqMask, _periodLabelExpr

    df = df.filter(
        (pl.col("statement") == statement)
        & (pl.col("scope") == scope)
        & (pl.col("axisPath") == "")  # top-level 라인아이템(차원 분해 제외 — statement view)
        & _freqMask(freq)
    )
    if df.is_empty():
        return None
    df = _accountColumn(df, statement)
    df = df.with_columns(_periodLabelExpr(freq).alias("_period")).sort("rceptNo", descending=True)
    deduped = df.unique(subset=["account", "_period"], keep="first", maintain_order=True)
    meta = df.group_by("account", maintain_order=True).agg(
        pl.col("label").first().alias("label"), pl.col("cellOrder").min().alias("_ord")
    )
    wide = deduped.pivot(values="valueRaw", index="account", on="_period", aggregate_function="first")
    wide = wide.join(meta, on="account", how="left").sort("_ord").drop("_ord")
    periodCols = sorted((c for c in wide.columns if c not in ("account", "label")), reverse=True)
    return wide.select(["account", "label", *periodCols])


def readNative(
    ticker: str,
    *,
    statement: str,
    freq: str = "quarter",
    scope: str = "consolidated",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """native 재무제표/비율 — panelCell → 계정×기간 wide (DART ``cell.readStatement`` 공개 계약 동형).

    논리 키 ``is/bs/cf/cis/sce`` → 물리 statement 해소 후 wide. ``ratios`` 는 bs/is/cf 조립 → core 공식
    (DART native ratios 동형). 출력 ``[account, label, *period]`` (period 최신 좌측) — DART 와 byte 계약 동일.

    Args:
        ticker: US ticker.
        statement: 논리 키 ("is"/"bs"/"cf"/"cis"/"sce"/"ratios").
        freq: "year"/"quarter"/"ytd" (DART 동일 토큰 의미).
        scope: "consolidated" (EDGAR 연결-only).
        periods: 특정 filingPeriod 만 (prune). None=전체.

    Returns:
        wide ``pl.DataFrame`` ([account, label, *period]) 또는 None (artifact/매칭 0).

    Raises:
        없음.

    Example:
        >>> readNative("AIR", statement="is", freq="year")  # doctest: +SKIP — 손익 연간 계정×연도

    SeeAlso:
        - ``providers.dart.panel.cell.readStatement`` — DART 계약 원본.
        - ``providers.dart.panel.cell._freqMask`` / ``_periodLabelExpr`` — 재사용(계약 의미 동일).

    Requires:
        - polars. panelCell artifact. EdgarMapper. core.ratios.

    Capabilities:
        - 필링 XBRL 셀을 DART 와 동일 계약 wide 로 — c.panel("is") 시장 무관 동형.

    Guide:
        - ``c.panel("is")`` (us) → 본 함수(facade _nativeFn 주입). 직접 호출 가능.

    AIContext:
        - native(소문자)=필링 셀(deep) / finance(대문자)=companyfacts. account=snakeId 통합.

    When:
        - EDGAR native 재무제표/비율을 계정×기간으로 볼 때.

    How:
        - load → (statement 해소|ratios 조립) → freq/top-level filter → snakeId pivot.

    LLM Specifications:
        AntiPatterns:
            - 출력 계약 변형 금지(DART [account,label,*period] 동일).
        OutputSchema:
            - ``pl.DataFrame | None``.
        Prerequisites:
            - panelCell artifact.
        Freshness:
            - 매 read.
        Dataflow:
            - panelCell → filter → pivot.
        TargetMarkets:
            - US.
    """
    if statement == "ratios":
        return _readRatios(ticker, freq=freq, scope=scope, periods=periods)
    phys = _LOGICAL_TO_STMT.get(statement)
    if phys is None:
        return None
    cells = _loadCells(ticker, periods)
    if cells is None:
        return None
    return _statementWide(cells, statement=phys, freq=freq, scope=scope)


def _readRatios(ticker: str, *, freq: str, scope: str, periods: list[str] | None) -> pl.DataFrame | None:
    """native 재무비율 — bs/is/cf 셀 → snakeId series → core.ratios (DART readRatios 동형).

    EDGAR 셀 account 가 이미 snakeId(EdgarMapper)라 DART 의 라벨→snakeId 재색인 불필요 — bs/is/cf wide
    의 account(snakeId) 그대로 series 조립 → ``core.ratios.calcRatioSeries``(공식 SSOT). 출력
    ``[ratio, label, *period]`` (DART ratios 계약 동형).
    """
    from dartlab.core.ratioCategories import RATIO_CATEGORIES, RATIO_FIELD_LABELS
    from dartlab.core.ratios import calcRatioSeries, toSeriesDict
    from dartlab.core.utils.helpers import parseNumStr

    cells = _loadCells(ticker, periods)
    if cells is None:
        return None
    statements = {
        sj: _statementWide(cells, statement=_LOGICAL_TO_STMT[key], freq=freq, scope=scope)
        for sj, key in _RATIO_SOURCE.items()
    }
    periodSet: set[str] = set()
    for df in statements.values():
        if df is not None:
            periodSet.update(c for c in df.columns if c not in ("account", "label"))
    if not periodSet:
        return None
    years = sorted(periodSet)
    series: dict[str, dict[str, list[float | None]]] = {}
    for sj, df in statements.items():
        if df is None or df.is_empty():
            continue
        bucket: dict[str, list[float | None]] = {}
        for row in df.iter_rows(named=True):
            acc = row["account"]
            if acc in bucket:
                continue
            bucket[acc] = [parseNumStr(row.get(y)) for y in years]
        if bucket:
            series[sj] = bucket
    if not series:
        return None
    rs = calcRatioSeries(series, years, yoyLag=(4 if freq == "quarter" else 1))
    ratioDict = toSeriesDict(rs)[0]["RATIO"]
    if not ratioDict:
        return None
    ordered = [f for _, fields in RATIO_CATEGORIES for f in fields if f in ratioDict]
    rows: list[dict] = []
    for field in ordered:
        vals = ratioDict[field]
        rec: dict = {"ratio": field, "label": RATIO_FIELD_LABELS.get(field, field)}
        for i, y in enumerate(years):
            rec[y] = vals[i] if i < len(vals) else None
        rows.append(rec)
    if not rows:
        return None
    wide = pl.DataFrame(rows)
    periodCols = sorted((c for c in wide.columns if c not in ("ratio", "label")), reverse=True)
    return wide.select(["ratio", "label", *periodCols])
