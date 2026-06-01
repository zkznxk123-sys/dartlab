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

from pathlib import Path

import polars as pl

import dartlab.config as _cfg

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
        - 상태 없는 read. valueRaw 그대로. 항목명 다르면 별 행(숨김 0).

    When:
        - native 재무제표를 전 기간 연속으로 볼 때.

    How:
        - parquet glob → statement/scope/depth-1/freq filter → 정규화명 pivot → 최신 filing dedup.

    LLM Specifications:
        AntiPatterns:
            - lxml import 금지(R2). 항목명 매칭 실패를 숨기지 말 것(별 행).
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
    deduped = df.unique(subset=["_name", "_period"], keep="first", maintain_order=True)
    meta = df.group_by("_name", maintain_order=True).agg(
        pl.col("label").first().alias("label"),  # 최신 filing 표시명
        pl.col("cellOrder").min().alias("_ord"),
    )

    wide = deduped.pivot(values="valueRaw", index="_name", on="_period", aggregate_function="first")
    wide = wide.join(meta, on="_name", how="left").sort("_ord").drop("_ord").rename({"_name": "account"})
    periodCols = sorted((c for c in wide.columns if c not in ("account", "label")), reverse=True)
    return wide.select(["account", "label", *periodCols])
