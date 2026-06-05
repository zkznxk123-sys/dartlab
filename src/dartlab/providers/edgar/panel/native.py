"""EDGAR panel native 재무 read — panel row payload → 계정×기간 wide.

소문자 ``c.panel("is"/"bs"/"cf"/"ratios")`` 는 DART 처럼 native 경로다. EDGAR 는 별도
셀 parquet 를 만들지 않고, build 시 fact/context 결합 결과를 같은 ``edgar/panel`` row
``contentRaw`` 안에 payload 로 보존한다. 본 모듈은 그 payload 를 read-time 으로 분해한다.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

_PAYLOAD_TAG = "DARTLAB_EDGAR_NATIVE_CELLS"
_PAYLOAD_RE = re.compile(r"<!--DARTLAB_EDGAR_NATIVE_CELLS:([A-Za-z0-9+/=]+)-->", re.DOTALL)

NATIVE_CELL_SCHEMA: dict[str, pl.DataType] = {
    "corp": pl.Utf8,
    "rceptNo": pl.Utf8,
    "filingPeriod": pl.Utf8,
    "statement": pl.Utf8,
    "scope": pl.Utf8,
    "concept": pl.Utf8,
    "label": pl.Utf8,
    "ctxYear": pl.Int32,
    "ctxFlow": pl.Utf8,
    "ctxQuarter": pl.Int32,
    "ctxMode": pl.Utf8,
    "axisPath": pl.Utf8,
    "valueRaw": pl.Utf8,
    "cellOrder": pl.UInt32,
}

_LOGICAL_TO_STMT: dict[str, str] = {"is": "IS", "bs": "BS", "cf": "CF", "cis": "CIS", "sce": "EF"}
_RATIO_SOURCE: dict[str, str] = {"BS": "bs", "IS": "is", "CF": "cf"}


def encodeNativeCellsPayload(cells: list[dict]) -> str:
    """native cell rows → ``contentRaw`` 에 붙일 HTML comment payload.

    Args:
        cells: native cell row dict 목록.

    Returns:
        base64 JSON HTML comment payload. 입력이 비면 빈 문자열.

    Raises:
        없음 — JSON 직렬화 가능한 cell dict 를 builder 입력 계약으로 받는다.

    Example:
        >>> encodeNativeCellsPayload([])
        ''
    """
    if not cells:
        return ""
    raw = json.dumps(cells, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = base64.b64encode(raw).decode("ascii")
    return f"<!--{_PAYLOAD_TAG}:{payload}-->"


def decodeNativeCellsPayload(contentRaw: str | None) -> list[dict]:
    """``contentRaw`` HTML comment payload → native cell rows.

    Args:
        contentRaw: panel row 의 raw HTML/text payload.

    Returns:
        native cell row dict 목록. payload 부재/손상 시 빈 list.

    Raises:
        없음 — 손상 payload 는 warning 후 skip.

    Example:
        >>> decodeNativeCellsPayload(None)
        []
    """
    if not contentRaw or _PAYLOAD_TAG not in contentRaw:
        return []
    out: list[dict] = []
    for match in _PAYLOAD_RE.finditer(contentRaw):
        try:
            raw = base64.b64decode(match.group(1).encode("ascii"))
            rows = json.loads(raw.decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            _log.warning("EDGAR native payload decode 실패: %s", exc)
            continue
        if isinstance(rows, list):
            out.extend(r for r in rows if isinstance(r, dict))
    return out


def _panelPath(ticker: str) -> Path:
    return Path(_cfg.dataDir) / "edgar" / "panel" / f"{ticker.upper()}.parquet"


def _cellsFromPanel(ticker: str, periods: list[str] | None = None) -> pl.DataFrame | None:
    """``edgar/panel/{ticker}.parquet`` contentRaw payload → native cell DataFrame."""
    from dartlab.providers.dart.panel.read import ensurePanelFromHf

    ticker = ticker.upper()
    ensurePanelFromHf(ticker, "us")
    p = _panelPath(ticker)
    if not p.exists():
        return None
    try:
        df = pl.read_parquet(str(p), columns=["period", "contentRaw"])
    except (OSError, pl.exceptions.PolarsError) as exc:
        _log.warning("edgar panel native read 실패 %s: %s", ticker, exc)
        return None
    if periods:
        df = df.filter(pl.col("period").is_in(list(periods)))
    rows: list[dict] = []
    for row in df.iter_rows(named=True):
        rows.extend(decodeNativeCellsPayload(row.get("contentRaw")))
    if not rows:
        return None
    return pl.DataFrame(rows, schema=NATIVE_CELL_SCHEMA)


def _accountColumn(df: pl.DataFrame, statement: str) -> pl.DataFrame:
    """concept(us-gaap local-name) → snakeId account 컬럼."""
    try:
        from dartlab.providers.edgar.finance.mapper import EdgarMapper

        mapper = EdgarMapper()
        concepts = df["concept"].unique().to_list()
        mp = {c: (mapper.mapToDart(c, statement) or c) for c in concepts if c}
    except Exception:  # noqa: BLE001 — 매퍼 실패 시 concept 그대로 반환
        return df.with_columns(pl.col("concept").alias("account"))
    return df.with_columns(pl.col("concept").replace(mp).alias("account"))


def _statementWide(df: pl.DataFrame, *, statement: str, freq: str, scope: str) -> pl.DataFrame | None:
    """native cell DataFrame → ``[account, label, *period]`` wide."""
    from dartlab.providers.dart.panel.cell import _freqMask, _periodLabelExpr

    df = df.filter(
        (pl.col("statement") == statement) & (pl.col("scope") == scope) & (pl.col("axisPath") == "") & _freqMask(freq)
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
    """EDGAR native 재무제표/비율 — panel 단일 artifact 에서 read-time 분해.

    Args:
        ticker: US ticker.
        statement: ``is``/``bs``/``cf``/``cis``/``sce``/``ratios``.
        freq: ``"quarter"`` 또는 ``"annual"``.
        scope: ``"consolidated"`` 등 scope 필터.
        periods: 선택 기간 필터.

    Returns:
        native wide DataFrame 또는 payload/statement 부재 시 None.

    Raises:
        없음 — panel 부재와 미지원 statement 는 None 으로 표현한다.

    Example:
        >>> readNative("AAPL", statement="is")  # doctest: +SKIP
    """
    key = statement.lower()
    if key == "ratios":
        return _readRatios(ticker, freq=freq, scope=scope, periods=periods)
    phys = _LOGICAL_TO_STMT.get(key)
    if phys is None:
        return None
    cells = _cellsFromPanel(ticker, periods)
    if cells is None:
        return None
    return _statementWide(cells, statement=phys, freq=freq, scope=scope)


def _readRatios(ticker: str, *, freq: str, scope: str, periods: list[str] | None) -> pl.DataFrame | None:
    """native 재무비율 — panel native bs/is/cf 셀 → core ratios."""
    from dartlab.core.ratioCategories import RATIO_CATEGORIES, RATIO_FIELD_LABELS
    from dartlab.core.ratios import calcRatioSeries, toSeriesDict
    from dartlab.core.utils.helpers import parseNumStr

    cells = _cellsFromPanel(ticker, periods)
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
    ordered = [field for _, fields in RATIO_CATEGORIES for field in fields if field in ratioDict]
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
