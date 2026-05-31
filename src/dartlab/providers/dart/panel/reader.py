"""panel RUNTIME reader (L1 read) — panel parquet → lazy scan / long.

``Panel`` facade 가 wrap 하는 read backend. ``scan_parquet`` + columnar projection 만
사용 (lxml/zip import 0 — BUILD 와 물리 분리, R2). 콜드 <1s 핵심: 본문(contentRaw)은
show 시점 per-query materialize, meta board 는 contentRaw 제외로 <1MB.

LLM Specifications:
    AntiPatterns:
        - 옛 docs.parquet 호환 layer 신설 금지 — 신 panel artifact 만 backend.
        - in-memory 전체 누적 read 금지 — scan_parquet + columnar projection.
        - lxml / zipfile import 금지 — BUILD(gather) 전용(R2).
    OutputSchema:
        - ``scanPanel(code, ...) -> pl.LazyFrame | None``.
        - ``readLong(code, ...) -> pl.DataFrame | None`` (14-col long + disclosureKey).
    Prerequisites:
        - data/dart/panel/{code}/*.parquet (BUILD 결과).
        - data/bridge/panelBridge.parquet (disclosureKey fallback).
    Freshness:
        - panel parquet 변경 시 캐시 0 (매 호출 read).
    Dataflow:
        - panel *.parquet → polars scan → disclosureKey(이미 채워짐, 없으면 fallback).
    TargetMarkets:
        - KR (DART) + US (EDGAR) 공통.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)


def _panelDir(code: str, marketNs: str = "kr") -> Path:
    """panel artifact read 디렉터리.

    Args:
        code: 종목코드(KR) 또는 CIK/ticker(US).
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        KR: ``data/dart/panel/{code}/`` · US: ``data/edgar/panel/{code}/``.

    Raises:
        없음.

    Example:
        >>> _panelDir("005930").as_posix().endswith("dart/panel/005930")  # doctest: +SKIP
        True

    SeeAlso:
        - ``scanPanel`` — 본 디렉터리 scan.
        - ``core.dataConfig`` — panel 경로 SSOT(S5).

    Requires:
        - dartlab.config.

    Capabilities:
        - 시장별 panel artifact 단일 경로 — reader 가 본 함수만 경유.

    Guide:
        - 내부 helper — scanPanel/readLong 경유.

    AIContext:
        - 경로 계산만.

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


def _labelPath(marketNs: str = "kr") -> Path:
    """canonicalKey→labelKr 테이블 경로 (gather index.labelPath 의 providers-side mirror, R1).

    Args:
        marketNs: 시장 namespace ("kr"/"us").

    Returns:
        ``data/{dart|edgar}/panel/_label.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> _labelPath().name
        '_label.parquet'
    """
    base = "dart" if marketNs == "kr" else "edgar"
    return Path(_cfg.dataDir) / base / "panel" / "_label.parquet"


def resolveKeyArg(key: str, *, marketNs: str = "kr", byLabel: bool = True) -> list[str]:
    """사용자 key → canonicalKey list (exact canonicalKey + byLabel 시 한글 라벨 substring).

    show/cross 가 받는 key 를 정렬키(canonicalKey)로 정규화. exact canonicalKey("NT_D826380"/
    "BS")는 항상 자기 자신 포함, ``byLabel=True`` 면 ``_label.parquet`` labelKr substring 매칭
    canonicalKey 도 추가("재고"→재고자산 연결/별도 canonicalKey). _label 없으면 exact 만(라벨
    보강은 표시 전용 — 정렬은 canonicalKey 가 책임).

    Args:
        key: canonicalKey exact 또는 한글 라벨 substring.
        marketNs: 시장 namespace (기본 "kr").
        byLabel: True 면 labelKr substring 매칭도 포함 (기본 True).

    Returns:
        canonicalKey 후보 list (정렬). 매칭 없으면 ``[key]`` (exact 자기 자신).

    Raises:
        없음 — _label read 실패는 exact 만.

    Example:
        >>> resolveKeyArg("NT_D826380")  # doctest: +SKIP
        ['NT_D826380']
        >>> resolveKeyArg("재고")  # doctest: +SKIP
        ['NT_D826380', 'NT_D826385', '재고']

    SeeAlso:
        - ``gather.dart.panel.buildLabel`` — _label.parquet 생산.
        - ``Panel.show`` / ``cross.crossCompany`` — 본 helper 로 key 정규화.

    Requires:
        - polars. (byLabel 시) _label.parquet.

    Capabilities:
        - D-code canonicalKey 의 UX 저하를 한글 라벨 substring 검색으로 보완.

    Guide:
        - show/cross 가 disclosure 필터 전 호출. 결과를 ``is_in`` 필터.

    AIContext:
        - exact 우선 + 라벨 보강 — 라벨 없거나 미스 시에도 exact canonicalKey 동작.

    When:
        - show/cross 가 사용자 key 를 canonicalKey 정렬키로 정규화할 때.

    How:
        - {key} ∪ (byLabel ∧ _label 존재 시) labelKr.str.contains(key) canonicalKey.

    LLM Specifications:
        AntiPatterns:
            - 라벨을 정렬키로 저장 금지 — 검색 입력만, 출력은 canonicalKey.
            - _label 부재 시 raise 금지 — exact 만 반환.
        OutputSchema:
            - ``list[str]`` (canonicalKey 후보, 정렬).
        Prerequisites:
            - (byLabel) _label.parquet.
        Freshness:
            - 매 호출 read (_label 작음).
        Dataflow:
            - key → {key} ∪ labelKr substring 매칭 canonicalKey.
        TargetMarkets:
            - KR + US.
    """
    keys = {key}
    if byLabel:
        p = _labelPath(marketNs)
        if p.exists():
            try:
                label = pl.read_parquet(str(p))
                matched = label.filter(pl.col("labelKr").str.contains(key, literal=True))["canonicalKey"].to_list()
                keys.update(m for m in matched if m)
            except (pl.exceptions.PolarsError, OSError):
                pass
    return sorted(keys)


def scanPanel(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.LazyFrame | None:
    """panel artifact LazyFrame (collect 0 — show/pivot 가 per-query 필터).

    런타임 경량화 핵심: scan_parquet 만 반환. 호출자가 canonical 키 filter + 필요 컬럼만
    select → collect 시점에 해당 섹션 contentRaw 만 materialize (전체 본문 로드 회피).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 period 파일만 scan. None = 전체.

    Returns:
        LazyFrame 또는 None (artifact 없음).

    Raises:
        없음.

    Example:
        >>> lf = scanPanel("005930")  # doctest: +SKIP

    SeeAlso:
        - ``readLong`` — eager read + disclosureKey.
        - ``pivot.readPanelWide`` — 회사내 수평화.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - lazy scan → per-query filter/projection 으로 콜드 <1s, 메모리 최소.

    Guide:
        - cross-entity scan 또는 lazy 파이프라인에 사용.

    AIContext:
        - scan_parquet only — materialize 0.

    When:
        - lazy 파이프라인·대량에서 본문 미read scan 이 필요할 때.

    How:
        - dir glob → (periods filter) → scan_parquet.

    LLM Specifications:
        AntiPatterns:
            - read_parquet eager 금지(전체 본문 로드) — scan_parquet.
        OutputSchema:
            - ``pl.LazyFrame | None``.
        Prerequisites:
            - data/{dart|edgar}/panel/{code}/*.parquet.
        Freshness:
            - 매 호출 scan.
        Dataflow:
            - dir glob → (periods filter) → scan_parquet.
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
    return pl.scan_parquet([str(f) for f in files])


def readLong(code: str, *, marketNs: str = "kr", periods: list[str] | None = None) -> pl.DataFrame | None:
    """panel long format read + disclosureKey 부착(fallback).

    Args:
        code: 종목코드.
        marketNs: 시장 namespace ("kr" / "us").
        periods: 특정 period 만. None = 전체.

    Returns:
        long DataFrame (14-col + disclosureKey) 또는 None (artifact 없음/빈).

    Raises:
        없음 — read 실패는 None.

    Example:
        >>> df = readLong("005930")  # doctest: +SKIP

    SeeAlso:
        - ``scanPanel`` — lazy 버전.
        - ``pivot.readPanelWide`` — wide 수평화.
        - ``core.panel.resolveBatch`` — disclosureKey fallback.

    Requires:
        - polars. panel artifact. (fallback 시) bridge parquet.

    Capabilities:
        - 한 회사 전(또는 일부) 기간 long 본문 read — disclosureKey 보장.

    Guide:
        - pivot/cross/facade 가 호출. 직접 호출 가능.

    AIContext:
        - build 가 채운 disclosureKey 사용, 옛 artifact(전부 null)만 fallback resolve.

    When:
        - 한 회사 long 본문 + disclosureKey 가 필요할 때.

    How:
        - parquet read → disclosureKey null 검사 → (fallback) resolveBatch.

    LLM Specifications:
        AntiPatterns:
            - 매 read 마다 resolveBatch 금지 — build 가 채운 값 우선, null 일 때만.
        OutputSchema:
            - ``pl.DataFrame | None`` (14-col + disclosureKey).
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 호출 read.
        Dataflow:
            - parquet read → disclosureKey null 검사 → (fallback) resolveBatch.
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
        from dartlab.core.panel import resolveBatch

        if "disclosureKey" in df.columns:
            df = df.drop("disclosureKey")
        # KR within = native canonicalKey (옛 artifact·미빌드 fallback). US = bridge overlay.
        df = resolveBatch(df, marketNs=marketNs, useCanonical=(marketNs == "kr"))
    return df
