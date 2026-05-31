"""panel read 엔진 (L1 read) — parquet long → 항목 × period wide 수평화 (lxml 0).

``Panel`` 이 wrap 하는 read backend 단일 모듈 (reader+anchor+pivot 통합). ``read_parquet`` +
columnar projection 만 — BUILD(build/) 와 물리 분리, lxml/zipfile import 0 (R2, 콜드 <1s).
period 파일 prune(``periods`` 인자)으로 대형 종목 메모리 핸들.

수평화 3 단계:
    1. ``readLong`` — period 파일 read + disclosureKey 보장(build 가 채움, 옛 artifact 만 fallback).
    2. ``anchorLatest`` — (disclosureKey, scope) 앵커로 era drift(BS→BS_C) 흡수 → 한 행 정렬.
    3. ``readWide`` — blockOrder 순 contentRaw join collapse → period 축 pivot. ``tag=False`` 면
       collapse 단계에서 태그 1회 strip(plain, raw wide 미생성) — 2 중 materialize 회피.

LLM Specifications:
    AntiPatterns:
        - lxml/zipfile/network import 금지 — read 표면(R2, 콜드 <1s).
        - 매 read resolveBatch 금지 — build 가 채운 disclosureKey 우선, 전부 null 일 때만 fallback.
        - strip 을 pivot 후 wide 셀에 적용 금지 — collapse 단계 1회(raw wide 2 중 materialize 회피).
        - pivot index 에 xbrlClass 유지 금지 — era drift, scope(파생)로 대체.
    OutputSchema:
        - ``readLong(code, *, marketNs, periods) -> pl.DataFrame | None`` (14-col + disclosureKey).
        - ``readWide(code, *, marketNs, periods, tag) -> pl.DataFrame | None`` (index + period 열).
        - ``scopeExpr(col) -> pl.Expr`` / ``anchorLatest(df) -> pl.DataFrame``.
    Prerequisites:
        - polars. data/{dart|edgar}/panel/{code}/*.parquet (build 결과).
    Freshness:
        - 매 호출 read (artifact 변경 즉시 반영, 캐시 0 — 누적 0).
    Dataflow:
        - parquet → readLong → anchorLatest → collapse(+tag strip) → pivot.
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

# pivot row identity (회사내 다기간 정렬 키). scope = read 파생(scopeExpr).
_INDEX_COLS = ["chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"]

# 태그 strip — 순수 polars regex (lxml 0, R2). join 후 적용(태그 element 경계 보존).
_TAG_RE = r"<[^>]+>"
_WS_RE = r"\s+"


def _panelDir(code: str, marketNs: str = "kr") -> Path:
    """panel artifact read 디렉터리 (시장별 단일 경로).

    Args:
        code: 종목코드(KR 6자리) 또는 CIK/ticker(US).
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        KR: ``data/dart/panel/{code}/`` · US: ``data/edgar/panel/{code}/`` Path.

    Raises:
        없음.

    Example:
        >>> _panelDir("005930").as_posix().endswith("dart/panel/005930")  # doctest: +SKIP
        True

    SeeAlso:
        - ``readLong`` / ``readWide`` — 본 디렉터리 read.

    Requires:
        - dartlab.config.

    Capabilities:
        - 시장별 panel artifact 단일 경로 — read 엔진이 본 함수만 경유(경로 분산 0).

    Guide:
        - 내부 helper — readLong/readWide 경유.

    AIContext:
        - 경로 계산만 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지 — 본 함수 단일.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - (code, marketNs) → data/{dart|edgar}/panel/{code}.
        TargetMarkets:
            - KR + US.
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "panel" / code


def scopeExpr(col: str = "xbrlClass") -> pl.Expr:
    """xbrlClass → scope ('consolidated' / 'standalone') 파생 Expr (연결/별도 분리 보존).

    DART ACLASS 규약: 별도(개별)는 ``_S`` 표식(BS_S/IS_S2/NT_S_D######), 연결은 ``_C`` 또는
    옛 무접미사(BS/IS2/CF). ``_S`` 없으면 연결. 같은 disclosureKey 라도 scope 로 분리해 BS_C↔BS_S
    병합 차단.

    Args:
        col: xbrlClass 컬럼명 (기본 "xbrlClass").

    Returns:
        ``scope`` 별칭 Utf8 Expr ("consolidated"/"standalone").

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
        >>> df.select(scopeExpr())["scope"].to_list()
        ['consolidated', 'standalone', 'consolidated', 'standalone', 'consolidated']

    SeeAlso:
        - ``anchorLatest`` — scope 로 연결/별도 병합 방지.
        - ``readWide`` — scope 가 pivot index 의 일부.

    Requires:
        - polars.

    Capabilities:
        - 연결/별도 분리 보존 — 회사내 수평화에서 BS_C↔BS_S 병합 착시 차단.

    Guide:
        - anchorLatest / readWide 내부에서 사용 — 직접 호출 가능(순수 Expr).

    AIContext:
        - 순수 Expr — literal 매칭(특수문자 0).

    LLM Specifications:
        AntiPatterns:
            - ``_S`` regex 부분매칭 금지 — literal 매칭.
            - narrative(null) 에 None scope 금지 — consolidated 기본(pivot index 안정).
        OutputSchema:
            - ``pl.Expr`` (alias "scope", Utf8).
        Prerequisites:
            - polars. xbrlClass 컬럼.
        Freshness:
            - read 파생.
        Dataflow:
            - xbrlClass → null/_S/else → scope.
        TargetMarkets:
            - KR (DART _C/_S 규약). EDGAR 는 별도 scope 규칙.
    """
    c = pl.col(col)
    return (
        pl.when(c.is_null())
        .then(pl.lit("consolidated"))
        .when(c.str.contains("_S", literal=True))
        .then(pl.lit("standalone"))
        .otherwise(pl.lit("consolidated"))
        .alias("scope")
    )


def anchorLatest(df: pl.DataFrame) -> pl.DataFrame:
    """과거 기간을 최신기준으로 수평화 — (disclosureKey, scope) 앵커 정렬 (era drift 흡수).

    같은 disclosure 가 era 마다 xbrlClass(BS→BS_C)·제목이 흔들려 pivot 이 era 별로 행을 쪼갬 →
    ``coalesce(disclosureKey, xbrlClass)`` 앵커(disclosureKey 가 canonical 키면 그 자체가 era-안정,
    build 가 scope-strip 채움)의 ``(_, scope)`` 그룹 **최신 period 라벨**(chapter/sectionLeaf/
    blockLeaf)을 전 기간에 덮어써 한 행으로 정렬. 앵커 null(narrative) 행은 손대지 않음(텍스트 정렬 유지).

    Args:
        df: panel long DataFrame (disclosureKey/xbrlClass/period/chapter/sectionLeaf/blockLeaf 포함).

    Returns:
        ``scope`` 컬럼 추가 + keyed 행의 chapter/sectionLeaf/blockLeaf 최신기준 통일 DataFrame.
        빈/필수컬럼 부재 시 원본 그대로.

    Raises:
        없음.

    Example:
        >>> out = anchorLatest(longDf)  # doctest: +SKIP
        >>> "scope" in out.columns  # doctest: +SKIP
        True

    SeeAlso:
        - ``scopeExpr`` — scope 파생.
        - ``readWide`` — anchorLatest 후 period 축 pivot.

    Requires:
        - polars.

    Capabilities:
        - 회사내 수평화의 era drift 흡수 — 과거 기간이 최신기준 한 행에 정렬(행 쪼개짐 0).

    Guide:
        - readWide 가 wide 변환 전 호출 — 직접 호출 가능.

    AIContext:
        - keyed 행만 라벨 통일, narrative 는 보존 — 무손실.

    When:
        - pivot 이 회사내 wide 변환 전 era drift 를 흡수할 때.

    How:
        - scope 부착 → (anchorKey, scope) 최신 period 라벨 → join 덮어쓰기.

    LLM Specifications:
        AntiPatterns:
            - 앵커 단독 group 금지 — (anchorKey, scope) 페어(연결/별도 병합 방지).
            - raw xbrlClass 를 pivot index 유지 금지 — era drift 로 행 쪼개짐(canonicalKey/scope 대체).
            - 최신 = period 최대 문자열(YYYYQn 정렬, 12월결산화라 안전).
        OutputSchema:
            - 입력 + ``scope``, keyed 행 라벨 최신 통일.
        Prerequisites:
            - disclosureKey/period/xbrlClass 컬럼.
        Freshness:
            - read 파생.
        Dataflow:
            - scope 부착 → keyed (anchorKey,scope) 최신 period 라벨 → join 덮어쓰기.
        TargetMarkets:
            - KR + US 공통.
    """
    if df.is_empty() or "disclosureKey" not in df.columns or "period" not in df.columns:
        return df
    df = df.with_columns(scopeExpr())
    anchorExpr = (
        pl.coalesce([pl.col("disclosureKey"), pl.col("xbrlClass")])
        if "xbrlClass" in df.columns
        else pl.col("disclosureKey")
    )
    df = df.with_columns(anchorExpr.alias("_anchorKey"))
    keyed = df.filter(pl.col("_anchorKey").is_not_null())
    if keyed.is_empty():
        return df.drop("_anchorKey")
    latest = (
        keyed.sort("period")
        .group_by(["_anchorKey", "scope"], maintain_order=True)
        .agg(
            pl.col("chapter").last().alias("_chapterL"),
            pl.col("sectionLeaf").last().alias("_sectionLeafL"),
            pl.col("blockLeaf").last().alias("_blockLeafL"),
        )
    )
    df = df.join(latest, on=["_anchorKey", "scope"], how="left")
    return df.with_columns(
        pl.when(pl.col("_chapterL").is_not_null())
        .then(pl.col("_chapterL"))
        .otherwise(pl.col("chapter"))
        .alias("chapter"),
        pl.when(pl.col("_sectionLeafL").is_not_null())
        .then(pl.col("_sectionLeafL"))
        .otherwise(pl.col("sectionLeaf"))
        .alias("sectionLeaf"),
        pl.when(pl.col("_blockLeafL").is_not_null())
        .then(pl.col("_blockLeafL"))
        .otherwise(pl.col("blockLeaf"))
        .alias("blockLeaf"),
    ).drop(["_chapterL", "_sectionLeafL", "_blockLeafL", "_anchorKey"])


def readLong(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.DataFrame | None:
    """panel long format read + disclosureKey 보장 (period 파일 prune).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace ("kr" / "us").
        periods: 특정 period 만(파일 단위 prune — 대형 종목 메모리 핸들). None = 전체.

    Returns:
        long DataFrame (14-col + disclosureKey) 또는 None (artifact 없음/빈/read 실패).

    Raises:
        없음 — read 실패는 None.

    Example:
        >>> df = readLong("005930", periods=["2025Q4"])  # doctest: +SKIP

    SeeAlso:
        - ``readWide`` — 본 long 을 wide 수평화.
        - ``mapper.resolveBatch`` — disclosureKey fallback.

    Requires:
        - polars. panel artifact. (fallback 시) bridge parquet.

    Capabilities:
        - 한 회사 전(또는 일부) 기간 long 본문 read — disclosureKey 보장, period 파일 prune.

    Guide:
        - readWide / Panel.long() 이 호출. 직접 호출 가능.

    AIContext:
        - build 가 채운 disclosureKey 사용, 옛 artifact(전부 null)만 fallback resolve.

    When:
        - 한 회사 long 본문 + disclosureKey 가 필요할 때.

    How:
        - dir glob → (periods filter) → read_parquet → disclosureKey null 검사 → (fallback) resolveBatch.

    LLM Specifications:
        AntiPatterns:
            - 매 read resolveBatch 금지 — build 가 채운 값 우선, 전부 null 일 때만.
        OutputSchema:
            - ``pl.DataFrame | None`` (14-col + disclosureKey).
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 호출 read.
        Dataflow:
            - dir glob → (periods filter) → read_parquet → disclosureKey 보장.
        TargetMarkets:
            - KR + US.
    """
    d = _panelDir(code, marketNs)
    if not d.exists():
        return None
    files = sorted(d.glob("*.parquet"))
    if periods:
        files = [f for f in files if f.stem in set(periods)]
    if not files:
        return None
    try:
        df = pl.read_parquet([str(f) for f in files])
    except (pl.exceptions.PolarsError, OSError) as exc:
        _log.warning("panel read 실패 %s: %s", code, exc)
        return None
    if df.is_empty():
        return None
    if "disclosureKey" not in df.columns or df["disclosureKey"].null_count() == df.height:
        from .mapper import resolveBatch

        if "disclosureKey" in df.columns:
            df = df.drop("disclosureKey")
        # KR within = native canonicalKey (옛 artifact·미빌드 fallback). US = bridge overlay.
        df = resolveBatch(df, marketNs=marketNs, useCanonical=(marketNs == "kr"))
    return df


def readWide(
    code: str,
    *,
    marketNs: str = "kr",
    periods: list[str] | None = None,
    tag: bool = True,
) -> pl.DataFrame | None:
    """panel wide pivot — index=(canonical key), columns=period (회사내 수평화 + tag strip).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 만(파일 prune). None = 전체.
        tag: True(기본) 면 contentRaw 원본 XML 무손실(R4), False 면 collapse 단계에서 태그 strip(plain).

    Returns:
        wide DataFrame. row identity = (chapter, sectionLeaf, blockLeaf, disclosureKey, scope),
        열 = period (cell = 본문). 또는 None (artifact 없음/빈/pivot 실패).

    Raises:
        없음 — pivot 실패는 None.

    Example:
        >>> readWide("005930", tag=False, periods=["2025Q4", "2024Q4"])  # doctest: +SKIP

    SeeAlso:
        - ``readLong`` — long 입력.
        - ``anchorLatest`` — 최신기준 정렬.
        - ``Panel`` — 본 함수를 wide 본체로 wrap.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - 한 회사 다기간을 항목 행 × period 열로 정렬 — era drift 흡수.
        - tag=False 면 collapse 1회 strip → plain wide(raw 의 ~22%, 표시·메모리 경량, 2중 materialize 회피).

    Guide:
        - Panel.__init__ 이 본 함수로 wide 생성. 직접 호출 가능.

    AIContext:
        - contentRaw 는 blockOrder 순 join(무손실), anchorLatest 후 pivot.
        - tag=False strip 은 join 결과에 1회 — raw wide 미생성.

    When:
        - 한 회사 다기간을 항목 × period 로 수평화할 때.

    How:
        - readLong → anchorLatest → group collapse(join contentRaw, +tag strip) → period pivot.

    LLM Specifications:
        AntiPatterns:
            - contentRaw 다중블록 first 금지 — blockOrder 순 join(무손실).
            - xbrlClass pivot index 금지 — scope 대체.
            - strip 을 pivot 후 적용 금지 — collapse 단계(raw wide 2중 회피).
        OutputSchema:
            - ``pl.DataFrame | None`` (index cols + period 열).
        Prerequisites:
            - panel artifact + period 컬럼.
        Freshness:
            - 매 호출.
        Dataflow:
            - readLong → anchorLatest → group(index,period) collapse(+strip) → pivot.
        TargetMarkets:
            - KR + US.
    """
    long = readLong(code, marketNs=marketNs, periods=periods)
    if long is None or long.is_empty() or "contentRaw" not in long.columns:
        return None
    long = anchorLatest(long)
    indexCols = [c for c in _INDEX_COLS if c in long.columns]
    if not indexCols or "period" not in long.columns:
        return None
    joined = pl.col("contentRaw").str.join("")
    aggExpr = joined if tag else joined.str.replace_all(_TAG_RE, " ").str.replace_all(_WS_RE, " ").str.strip_chars()
    try:
        collapsed = (
            long.sort("blockOrder")
            .group_by([*indexCols, "period"], maintain_order=True)
            .agg(aggExpr.alias("contentRaw"))
        )
        return collapsed.pivot(values="contentRaw", index=indexCols, on="period", aggregate_function="first")
    except (pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("panel pivot 실패 %s: %s", code, exc)
        return None
