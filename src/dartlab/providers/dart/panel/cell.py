"""panel 셀 read 표면 — 재무 5표 native 셀 artifact → acode×period wide (freq 토큰 선택, lxml 0).

``build/cell.buildPanelCells`` 가 구운 ``data/dart/panelCell/{code}/{period}.parquet`` (14-col) 를
읽어, freq(연간/분기/누적)에 맞는 ACONTEXT 토큰을 **선택만** 해서 acode×period wide 로 pivot. 산수 0
(정부가 단독/누적/연간 다 계산해 토큰으로 박음). R2: parquet only, lxml/zipfile import 0.

freq→토큰 규칙 (행별 ctxFlow 분기):
    - ``year``  : ctxMode=="Y" (dFY 흐름 / eFY 잔액). 열 = ctxYear. 사업보고서가 당기/전기/전전기 3년 운반.
    - ``quarter``: 흐름 d→ctxMode=="Q"(단독 3M), 시점 e→당기말 잔액(mode A/Y). 열 = YYYYQn.
    - ``ytd``   : ctxMode in (A,Y) (누적 흐름 FQA/HYA/TQA/dFY + 잔액). 열 = YYYYQn.

LLM Specifications:
    AntiPatterns:
        - lxml/zipfile import 금지 (R2 read 표면) — 분해 완료 컬럼만 filter.
        - freq 별 빼기 산수 금지 — ctxMode 토큰 선택만 (정부 native).
        - 5표 외 호출 금지 — statement ∈ {BS,IS2,IS3,CF,EF}.
    OutputSchema:
        - ``readCellWide(code,*,statement,freq,scope,...) -> pl.DataFrame | None`` (acode×period wide).
    Prerequisites:
        - data/dart/panelCell/{code}/*.parquet (build/cell.buildPanelCells 산출).
    Freshness:
        - 매 read (artifact 변경 즉시).
    Dataflow:
        - parquet glob → statement/scope/freq filter → 최신filing dedup → acode×period pivot.
    TargetMarkets:
        - KR (DART). ACONTEXT 2025-03+ (그 이전 셀 없음 → 열 부재).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

# 재무비율 = native 5표 항목의 산수. 공식·매핑·파서·라벨 전부 core(L0) SSOT 호출 (panel 자급, 농장 0).
from dartlab.core.ratioCategories import RATIO_CATEGORIES, RATIO_FIELD_LABELS
from dartlab.core.ratios import calcRatioSeries, toSeriesDict
from dartlab.core.utils.helpers import parseNumStr
from dartlab.core.utils.labels import _loadAccountMappings

from .cellSchema import CELL_PIVOT_INDEX

# 재무 5표 statement (build/cell.CELL_STATEMENTS 와 동일 — read 표면 SSOT, build import 안 함).
_CELL_STATEMENTS: frozenset[str] = frozenset({"BS", "IS2", "IS3", "CF", "EF"})

_MARKET_DIR = {"kr": "panelCell", "us": "edgarPanelCell"}


def cellStatements() -> frozenset[str]:
    """셀 세분화 대상 재무 5표 statement 집합 (BS/IS2/IS3/CF/EF).

    Args:
        없음.

    Returns:
        ``frozenset[str]`` — canonicalKey 형식 statement 코드 (불변).

    Raises:
        없음.

    Example:
        >>> "IS2" in cellStatements()
        True
        >>> len(cellStatements())
        5
    """
    return _CELL_STATEMENTS


def _cellDir(code: str, marketNs: str) -> Path:
    """셀 artifact 디렉터리 — ``data/dart/{panelCell}/{code}``."""
    sub = _MARKET_DIR.get(marketNs, "panelCell")
    return Path(_cfg.dataDir) / "dart" / sub / code


def _freqMask(freq: str) -> pl.Expr:
    """freq → ctxFlow/ctxMode filter mask (토큰 선택, 산수 0).

    Args:
        freq: "year" / "quarter" / "ytd".

    Returns:
        polars 불리언 Expr. 미지원 freq 는 항상 False.
    """
    if freq == "year":
        return pl.col("ctxMode") == "Y"
    if freq == "quarter":
        # 흐름=단독(Q), 시점=당기말 잔액(A 또는 연말 Y).
        return ((pl.col("ctxFlow") == "d") & (pl.col("ctxMode") == "Q")) | (
            (pl.col("ctxFlow") == "e") & pl.col("ctxMode").is_in(["A", "Y"])
        )
    if freq == "ytd":
        # 누적 흐름(A) + 연간(Y, =Q4 누적) + 잔액(A/Y).
        return pl.col("ctxMode").is_in(["A", "Y"])
    return pl.lit(False)


def _periodLabelExpr(freq: str) -> pl.Expr:
    """freq → period 열 라벨 Expr. year=YYYY, 그 외=YYYYQn."""
    if freq == "year":
        return pl.col("ctxYear").cast(pl.Utf8)
    return pl.col("ctxYear").cast(pl.Utf8) + "Q" + pl.col("ctxQuarter").cast(pl.Utf8)


def readCellWide(
    code: str,
    *,
    statement: str,
    freq: str = "quarter",
    scope: str = "consolidated",
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """재무 5표 셀 artifact → acode×period wide (freq 토큰 선택, 평탄화 acode@axisPath).

    Args:
        code: 종목코드.
        statement: 5표 canonicalKey ("BS"/"IS2"/"IS3"/"CF"/"EF").
        freq: "year"(연간) / "quarter"(분기 단독) / "ytd"(분기 누적). 기본 quarter.
        scope: "consolidated"(연결) / "standalone"(별도). 기본 consolidated.
        marketNs: 시장 namespace.
        periods: 특정 filing period(YYYYQn) parquet 만 (파일 prune). None = 전체.

    Returns:
        wide DataFrame — 행 = (statement, acode, label, axisPath, scope), 열 = period(최신 좌측),
        cell = valueRaw. 또는 None (artifact 없음 / statement 미존재 / freq 매칭 0).

    Raises:
        없음 — artifact 부재/빈 시 None.

    Example:
        >>> readCellWide("005930", statement="IS2", freq="year")  # doctest: +SKIP — 손익 연간 acode×연도
        >>> readCellWide("005930", statement="BS", freq="quarter")  # doctest: +SKIP — 재무상태 분기말

    SeeAlso:
        - ``build.cell.buildPanelCells`` — 본 artifact 생산.
        - ``readStatement`` — 항목명 statement view(`c.panel("is")`). 본 함수는 acode 정밀 차원 view(직접 호출).

    Requires:
        - polars. data/dart/panelCell/{code}/*.parquet.

    Capabilities:
        - 정부 native XBRL 셀을 freq 토큰 선택만으로 acode×period 격자 — 추측·산수 0, 깊이는 axisPath 행.

    Guide:
        - 직접 호출 (acode/축 정밀 view). 사람용 statement 는 ``readStatement``/``c.panel("is")``.

    AIContext:
        - 상태 없는 read. valueRaw(콤마/괄호) 그대로 — 숫자화는 소비자.

    When:
        - 재무 5표를 연간/분기/누적 native 셀 격자로 볼 때.

    How:
        - parquet glob → statement/scope/freq filter → 최신filing dedup → acode×period pivot → 정렬.

    LLM Specifications:
        AntiPatterns:
            - lxml import 금지(R2). freq 빼기 산수 금지(토큰 선택).
            - 5표 외 statement 금지.
        OutputSchema:
            - ``pl.DataFrame | None`` (acode×period wide).
        Prerequisites:
            - 셀 artifact.
        Freshness:
            - 매 read.
        Dataflow:
            - glob → filter → dedup → pivot.
        TargetMarkets:
            - KR + US.
    """
    if statement not in _CELL_STATEMENTS:
        return None
    base = _cellDir(code, marketNs)
    if not base.exists():
        return None
    files = sorted(base.glob("*.parquet"))
    if periods is not None:
        keep = set(periods)
        files = [f for f in files if f.stem in keep]
    if not files:
        return None

    df = pl.concat([pl.read_parquet(str(f)) for f in files], how="vertical")
    # readCellWide = XBRL acode 정밀 view (옛 acode=None 셀은 readStatement 전용).
    df = df.filter(
        (pl.col("statement") == statement)
        & (pl.col("scope") == scope)
        & pl.col("acode").is_not_null()
        & _freqMask(freq)
    )
    if df.is_empty():
        return None

    df = df.with_columns(_periodLabelExpr(freq).alias("_period"))
    # 최신 접수(rceptNo desc) 우선 — dedup·대표 label·대표 cellOrder 모두 최신 filing 기준.
    df = df.sort("rceptNo", descending=True)
    # 같은 (행 정체성, period) 가 여러 filing 에 — 최신 우선 dedup.
    deduped = df.unique(subset=[*CELL_PIVOT_INDEX, "_period"], keep="first", maintain_order=True)
    # 행 정체성별 대표 label(최신 filing) + 정렬용 cellOrder(최소).
    meta = df.group_by(CELL_PIVOT_INDEX, maintain_order=True).agg(
        pl.col("label").first().alias("label"),  # rceptNo desc 정렬 후라 최신 filing label
        pl.col("cellOrder").min().alias("_ord"),
    )

    wide = deduped.pivot(values="valueRaw", index=CELL_PIVOT_INDEX, on="_period", aggregate_function="first")
    wide = wide.join(meta, on=CELL_PIVOT_INDEX, how="left").sort("_ord").drop("_ord")

    periodCols = sorted((c for c in wide.columns if c not in CELL_PIVOT_INDEX and c != "label"), reverse=True)
    return wide.select([*CELL_PIVOT_INDEX, "label", *periodCols])


# 정규화 매칭 키: (주N) 주석참조 제거 + 공백 제거 (XBRL label ↔ 옛 항목명 통합).
_NOTE_PAT = r"\(주[\s\d,]+\)"


def _normalizeLabel(col: pl.Expr) -> pl.Expr:
    """label → 매칭 키: ``(주N)`` strip + 전 공백 제거. ("매출액 (주30)"→"매출액")."""
    return col.str.replace_all(_NOTE_PAT, "").str.replace_all(r"\s+", "")


def _find(parent: dict, x: str) -> str:
    """union-find root (경로 압축)."""
    parent.setdefault(x, x)
    r = x
    while parent[r] != r:
        r = parent[r]
    while parent[x] != r:
        parent[x], x = r, parent[x]
    return r


def _stitchRecentName(df: pl.DataFrame) -> pl.DataFrame:
    """개명 항목 통합 — 금액 겹침으로 같은 라인 묶어 **최신 filing 이름**(최근 기준) 부여.

    연속 보고서가 당기/전기/전전기로 연도 겹침 → 개명 전후 같은 라인은 **겹친 해의 금액이 같다**.
    그 금액 동치((ctxYear, valueRaw) 공유)로 `_name` 동치류를 만들고, 각 류 canonical = 최신
    rceptNo 의 `_name`. 식별력 있는 큰 금액(콤마 보유)만 링크 근거 — 0/소액 우연일치 over-merge 회피.

    Args:
        df: ``_name``/``ctxYear``/``valueRaw``/``rceptNo`` 보유 cell DataFrame.

    Returns:
        ``_name`` 을 canonical(최근 이름)로 치환한 DataFrame.
    """
    sig = df.filter(pl.col("valueRaw").str.contains(",", literal=True)).select("_name", "ctxYear", "valueRaw")
    parent: dict[str, str] = {}
    groups: dict[tuple, list[str]] = {}
    for name, yr, val in sig.iter_rows():
        groups.setdefault((yr, val), []).append(name)
    for names in groups.values():
        for n in names[1:]:
            parent[_find(parent, n)] = _find(parent, names[0])
    recency: dict[str, str] = dict(df.group_by("_name").agg(pl.col("rceptNo").max().alias("r")).iter_rows())
    comp: dict[str, list[str]] = {}
    for name in recency:
        comp.setdefault(_find(parent, name), []).append(name)
    nameToCanon: dict[str, str] = {}
    for members in comp.values():
        best = max(members, key=lambda n: recency.get(n) or "")  # 최신 filing 이름
        for m in members:
            nameToCanon[m] = best
    return df.with_columns(pl.col("_name").replace(nameToCanon).alias("_name"))


def readStatement(
    code: str,
    *,
    statement: str,
    freq: str = "year",
    scope: str = "consolidated",
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """native 재무제표 — 항목명 × 전 기간 (XBRL 최근 + 옛 표 과거 통합, 2011~).

    셀 artifact(XBRL 정밀 + 옛 위치파싱)를 **정규화 항목명**으로 통합 pivot. top-level axis
    (ConsolidatedMember, 깊이 1) 만 = 재무제표 라인아이템. 겹치는 해는 최신 filing(=XBRL) 우선.
    `readCellWide`(acode 정밀 차원 view) 와 별개 — 본 함수가 `c.panel("is")` statement view.

    Args:
        code: 종목코드.
        statement: 5표 ("BS"/"IS2"/"IS3"/"CF"/"EF").
        freq: "year"(연간) / "quarter"(분기) / "ytd"(누적). 기본 year.
        scope: "consolidated" / "standalone". 기본 consolidated.
        marketNs: 시장 namespace.
        periods: 특정 filing period parquet 만 (prune). None=전체.

    Returns:
        wide DataFrame — 행=(account 정규화명, label 표시명), 열=period(최신 좌측), cell=valueRaw.
        또는 None (artifact 없음 / statement 미존재 / 매칭 0).

    Raises:
        없음.

    Example:
        >>> readStatement("005930", statement="IS2", freq="year")  # doctest: +SKIP — 손익 2011~ 연속

    SeeAlso:
        - ``build.cell.buildPanelCells`` — XBRL+옛 셀 생산.
        - ``readCellWide`` — acode 정밀 차원 view (본 함수는 항목명 statement view).
        - ``panel.Panel.__call__`` — ``c.panel("is", freq=)`` 진입점.

    Requires:
        - polars. data/dart/panelCell/{code}/*.parquet.

    Capabilities:
        - native 재무제표를 XBRL 경계(2022) 넘어 항목명 매칭으로 과거 연장 — docs.parquet 0.

    Guide:
        - ``c.panel("is")`` 소문자 호출 → 본 함수. 대문자 IS 는 finance(파사드).

    AIContext:
        - 상태 없는 read. valueRaw 그대로. 개명 항목은 금액 겹침으로 최근 이름 통합(_stitchRecentName).

    When:
        - native 재무제표를 전 기간 연속으로 볼 때.

    How:
        - parquet glob → statement/scope/depth-1/freq filter → 정규화명 pivot → 최신 filing dedup.

    LLM Specifications:
        AntiPatterns:
            - lxml import 금지(R2). over-merge 회피 — 식별력 있는 큰 금액(콤마)만 stitch 링크.
        OutputSchema:
            - ``pl.DataFrame | None`` (항목명×period).
        Prerequisites:
            - 셀 artifact.
        Freshness:
            - 매 read.
        Dataflow:
            - glob → filter → 정규화명 pivot → dedup.
        TargetMarkets:
            - KR + US.
    """
    if statement not in _CELL_STATEMENTS:
        return None
    base = _cellDir(code, marketNs)
    if not base.exists():
        return None
    files = sorted(base.glob("*.parquet"))
    if periods is not None:
        keep = set(periods)
        files = [f for f in files if f.stem in keep]
    if not files:
        return None

    df = pl.concat([pl.read_parquet(str(f)) for f in files], how="vertical")
    df = df.filter(
        (pl.col("statement") == statement)
        & (pl.col("scope") == scope)
        & ~pl.col("axisPath").str.contains("|", literal=True)  # depth-1 top-level 라인아이템
        & _freqMask(freq)
    )
    if df.is_empty():
        return None

    df = df.with_columns(
        _normalizeLabel(pl.col("label")).alias("_name"),
        _periodLabelExpr(freq).alias("_period"),
    ).sort("rceptNo", descending=True)  # 최신 filing(=XBRL) 우선
    df = _stitchRecentName(df)  # 개명 항목 → 금액 겹침으로 최근 이름 통합
    deduped = df.unique(subset=["_name", "_period"], keep="first", maintain_order=True)
    meta = df.group_by("_name", maintain_order=True).agg(
        pl.col("label").first().alias("label"),  # 최신 filing 표시명
        pl.col("cellOrder").min().alias("_ord"),
    )

    wide = deduped.pivot(values="valueRaw", index="_name", on="_period", aggregate_function="first")
    wide = wide.join(meta, on="_name", how="left").sort("_ord").drop("_ord").rename({"_name": "account"})
    periodCols = sorted((c for c in wide.columns if c not in ("account", "label")), reverse=True)
    return wide.select(["account", "label", *periodCols])


# ── native 재무비율 (소문자 ratios — BS/IS/CF native 항목으로 core 공식 산출, panel 자급) ──

# 비율 재료를 읽을 native statement. 버킷 = 읽은 표(BS/IS/CF) — standardAccounts.sj COMMON 모호 회피.
_RATIO_SOURCE_STMTS: dict[str, str] = {"BS": "BS", "IS": "IS2", "CF": "CF"}

_NOTE_RE = re.compile(_NOTE_PAT)
_WS_RE = re.compile(r"\s+")


def _normKey(s: str) -> str:
    """항목명 → 매칭 키 — ``_normalizeLabel`` 의 스칼라 짝 ((주N) strip + 전 공백 제거)."""
    return _WS_RE.sub("", _NOTE_RE.sub("", s or ""))


@lru_cache(maxsize=1)
def _labelToSnakeId() -> dict[str, str]:
    """정규화 한국어 항목명 → snakeId — core ``mappings`` SSOT 재색인 (readStatement account 와 동일 정규화).

    Returns:
        ``{정규화항목명: snakeId}`` — 충돌 시 첫 등록 우선.

    SeeAlso:
        - ``core.utils.labels._loadAccountMappings`` — 원천 mappings(34,000+) 로더.
    """
    mappings = _loadAccountMappings().get("mappings", {})
    out: dict[str, str] = {}
    for korName, snakeId in mappings.items():
        key = _normKey(korName)
        if key and key not in out:
            out[key] = snakeId
    return out


def _assembleRatioSeries(
    statements: dict[str, pl.DataFrame | None],
) -> tuple[dict[str, dict[str, list[float | None]]], list[str]] | None:
    """native statement wide(항목명×period) → ``calcRatioSeries`` series + years.

    버킷 = 읽은 statement(BS/IS/CF). snakeId = core mappings(정규화 항목명). 값 = ``parseNumStr``(valueRaw,
    △/콤마). period = 표 간 union(오름차순 — YoY 정합, 각 series list 가 years 와 같은 길이로 정렬·None-fill).

    Args:
        statements: ``{"BS"|"IS"|"CF": readStatement 결과 | None}``.

    Returns:
        ``(series, years)`` 또는 None (재료 0). ``series={"BS":{snakeId:[...]}, ...}``.
    """
    labelMap = _labelToSnakeId()
    periodSet: set[str] = set()
    for df in statements.values():
        if df is not None:
            periodSet.update(c for c in df.columns if c not in ("account", "label"))
    if not periodSet:
        return None
    years = sorted(periodSet)  # 오름차순 (calcRatioSeries yoyLag 정합)
    series: dict[str, dict[str, list[float | None]]] = {}
    for sjKey, df in statements.items():
        if df is None or df.is_empty():
            continue
        bucket: dict[str, list[float | None]] = {}
        for row in df.iter_rows(named=True):
            snakeId = labelMap.get(row["account"])
            if snakeId is None or snakeId in bucket:  # 첫 행 우선(최신 filing 정렬됨)
                continue
            bucket[snakeId] = [parseNumStr(row.get(y)) for y in years]
        if bucket:
            series[sjKey] = bucket
    if not series:
        return None
    return series, years


def _ratiosToWide(rs, years: list[str]) -> pl.DataFrame | None:
    """RatioSeriesResult → ``[ratio, label, *period]`` wide (period 최신 좌측, RATIO_CATEGORIES 순서)."""
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


def readRatios(
    code: str,
    *,
    freq: str = "year",
    scope: str = "consolidated",
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """native 재무비율 — BS/IS/CF native statement 항목으로 core 공식 산출 (panel 자급, docs 0).

    ``readStatement``(bs/is/cf, XBRL+옛 통합 전기간) 의 항목을 core mappings 로 snakeId series 로 조립 →
    ``core.ratios.calcRatioSeries`` (공식 SSOT) → 비율 wide. 공식·매핑·파서·라벨 전부 core(L0) 호출,
    panel 재구현 0. native 5표 과거연장 덕에 finance(``c.panel("RATIOS")``)보다 깊은 history.

    Args:
        code: 종목코드.
        freq: "year"(연, yoyLag=1) / "quarter"(분기, yoyLag=4) / "ytd"(누적). 기본 year.
        scope: "consolidated" / "standalone". 기본 consolidated.
        marketNs: 시장 namespace.
        periods: 특정 filing period parquet 만 (prune). None=전체.

    Returns:
        wide DataFrame — 행=(ratio snakeId, label 한글), 열=period(최신 좌측), cell=비율값. 재료 없으면 None.

    Raises:
        없음 — artifact/재료 부재 시 None.

    Example:
        >>> readRatios("005930", freq="year")  # doctest: +SKIP  — ROE/부채비율 × 연도

    SeeAlso:
        - ``readStatement`` — 재료 native 재무제표(bs/is/cf).
        - ``core.ratios.calcRatioSeries`` / ``toSeriesDict`` — 비율 공식·시계열 dict SSOT.
        - ``core.ratioCategories.RATIO_FIELD_LABELS`` — 비율 한글 라벨 SSOT.

    Requires:
        - polars. data/dart/panelCell/{code}/*.parquet. core(L0) 공식·매핑.

    Capabilities:
        - native 재무제표 항목만으로 재무비율 — 외부 price 0 → 밸류에이션 제외 statement-only.

    Guide:
        - ``c.panel("ratios")`` 소문자 → 본 함수(native). 대문자 RATIOS 는 finance(파사드).

    AIContext:
        - 상태 없는 read. 공식·매핑·파서 core SSOT 호출(농장 0). 매핑 갭은 core accountMappings.json 보강.

    When:
        - native 재무비율을 깊은 기간으로 볼 때.

    How:
        - bs/is/cf readStatement → _assembleRatioSeries(snakeId series) → calcRatioSeries → _ratiosToWide.

    LLM Specifications:
        AntiPatterns:
            - 비율 공식·snakeId 매핑 재구현 금지(농장) — core SSOT 호출만.
            - lxml import 금지(R2). finance/company/docs import 금지(R1). docs.parquet read 금지(R3).
        OutputSchema:
            - ``pl.DataFrame | None`` ([ratio, label, *period]).
        Prerequisites:
            - 셀 artifact + core 번들 리소스.
        Freshness:
            - 매 read.
        Dataflow:
            - readStatement×3 → snakeId series → calcRatioSeries → wide.
        TargetMarkets:
            - KR (DART).
    """
    statements = {
        sjKey: readStatement(code, statement=stmt, freq=freq, scope=scope, marketNs=marketNs, periods=periods)
        for sjKey, stmt in _RATIO_SOURCE_STMTS.items()
    }
    assembled = _assembleRatioSeries(statements)
    if assembled is None:
        return None
    series, years = assembled
    rs = calcRatioSeries(series, years, yoyLag=(4 if freq == "quarter" else 1))
    return _ratiosToWide(rs, years)
