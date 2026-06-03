"""EDGAR panel build — gather sections artifact → cross-market 16-col PANEL_SCHEMA 미러 artifact.

DART ``panel.build`` 의 EDGAR analog. 단 **XML 파싱 파이프라인이 아니다** — gather 엔진
(``gather.edgar.docs``)이 이미 SEC 10-K/10-Q/20-F 를 item 단위로 itemize 해 ``data/edgar/sections/
{ticker}/{period}.parquet`` 로 적재했으므로(walker/refScan/dechunkNotes 불요), build 는 그 long
sections 를 **컬럼 remap** 만 한다 → ``providers.dart.panel.schema.PANEL_SCHEMA`` 16-col flat
artifact (``data/edgar/panel/{ticker}.parquet``). 이 16-col 을 cross-market read 표면
(``providers.dart.panel`` Panel/read, ``marketNs="us"``)이 무변경으로 read (schema 계약 SSOT).

매핑(sections → 16-col): chapter=form_type · sectionLeaf=topic itemId(``topicMap``) · sectionPath=
topic 전체 · leafType=blockType(heading→text) · blockLeaf=source_title · contentRaw=content_raw
(빈 셀=OOM 가드 → content_plain fallback) · period · corp=ticker · rceptNo=accession_no ·
disclosureKey=null·xbrlClass=null(section 블록은 narrative — rowIdentity=NARR::form␟itemId 기간 안정).

native 재무제표(BS/IS/CF)는 본 artifact 가 아니라 companyfacts(``c.show``) — ``c.panel("IS")`` 가
facade 위임. 본 build 는 **공시 본문 보드**(item 섹션·표·서술) 수평화만 (DART 미러의 본체).

LLM Specifications:
    AntiPatterns:
        - sections 원본 HTML 재파싱 금지 — gather 가 이미 itemize(content_raw/plain 보유), build 는 remap.
        - 시장별 컬럼 추가/이름 변경 금지 — PANEL_SCHEMA 16-col 동결(schema 계약 SSOT).
        - disclosureKey 에 임의 키 부여 금지 — section 블록은 narrative(null), rowIdentity=NARR.
        - 전 ticker 동시 메모리 로드 금지 — per-ticker 순차(빌드된 parquet read+remap, 메모리 bound).
    OutputSchema:
        - ``sectionsToPanel(long) -> pl.DataFrame`` (16-col PANEL_SCHEMA, 순수).
        - ``buildEdgarPanel(ticker, ...) -> dict[str, int]`` ({"rows", "periods"}).
        - ``buildEdgarPanelAll(tickers, ...) -> dict[str, dict]``.
    Prerequisites:
        - polars. data/edgar/sections/{ticker}/ (gather 산출). PANEL_SCHEMA.
    Freshness:
        - sections artifact 변경 시 재빌드 (offline — network 0).
    Dataflow:
        - loadSectionsLong → sectionsToPanel(remap) → atomic write data/edgar/panel/{ticker}.parquet.
    TargetMarkets:
        - US (EDGAR).
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
from dartlab.providers.edgar.docs.sections.sectionsStorage import (
    listAvailablePeriods,
    loadSectionsLong,
)

from .topicMap import itemIdExpr

_log = logging.getLogger(__name__)

_PANEL_REL = "edgar/panel"

# build 가 sections 에서 read 할 최소 컬럼 (columnar projection — content_raw 외 페이지 fault 절감).
_SOURCE_COLS = [
    "topic",
    "blockType",
    "blockOrder",
    "source_title",
    "content_raw",
    "content_plain",
    "period",
    "ticker",
    "accession_no",
    "form_type",
]


def panelPath(ticker: str) -> Path:
    """EDGAR panel flat artifact 경로 — ``data/edgar/panel/{TICKER}.parquet``.

    ``providers.dart.panel.read._panelDir(code, "us").parent / f"{code}.parquet"`` 와 동일 경로
    (read 표면이 ``marketNs="us"`` 로 read 하는 flat 파일). build write·read 단일 경로 SSOT.

    Args:
        ticker: US ticker (대소문자 무관, ``upper()`` 정규화).

    Returns:
        ``data/edgar/panel/{TICKER}.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> panelPath("aapl").name
        'AAPL.parquet'
    """
    return Path(_cfg.dataDir) / _PANEL_REL / f"{ticker.upper()}.parquet"


def sectionsToPanel(long: pl.DataFrame) -> pl.DataFrame:
    """EDGAR sections long → cross-market 16-col PANEL_SCHEMA (순수 remap, I/O 0).

    gather sections 의 itemize 결과를 DART panel reader 가 무변경으로 read 하는 16-col 으로 변환.
    section 블록은 ACLASS 없는 narrative 라 ``disclosureKey``/``xbrlClass`` null — read 표면의
    ``rowIdentity``(NARR::chapter␟sectionLeaf)·``scopeExpr``(null→consolidated)·``canonicalChapterExpr``
    (미매칭 passthrough)·``orderBySpine``(_skel 문서순서)가 그대로 graceful 동작. content_raw 가
    빈 문자열(상류 OOM 가드)이면 content_plain 으로 fallback(보드 본문 항상 보유).

    Args:
        long: sections long DataFrame (``loadSectionsLong`` 결과 — topic/blockType/blockOrder/
            source_title/content_raw/content_plain/period/ticker/accession_no/form_type 보유).

    Returns:
        16-col PANEL_SCHEMA DataFrame (키 순서·dtype 강제). 빈/None 입력은 빈 16-col DataFrame.

    Raises:
        없음 — 빈 입력은 빈 16-col.

    Example:
        >>> import polars as pl
        >>> long = pl.DataFrame({
        ...     "topic": ["10-K::item1Business"], "blockType": ["text"], "blockOrder": [0],
        ...     "source_title": ["Item 1. Business"], "content_raw": ["<p>x</p>"],
        ...     "content_plain": ["x"], "period": ["2024Q4"], "ticker": ["AAPL"],
        ...     "accession_no": ["0000320193-24-000123"], "form_type": ["10-K"]})
        >>> out = sectionsToPanel(long)
        >>> out["chapter"][0], out["sectionLeaf"][0], out["disclosureKey"][0]
        ('10-K', 'item1Business', None)

    SeeAlso:
        - ``topicMap.itemIdExpr`` — topic → sectionLeaf(itemId).
        - ``providers.dart.panel.schema.PANEL_SCHEMA`` — 16-col 계약 SSOT.
        - ``providers.dart.panel.read.readWide`` — 본 산출물을 wide 수평화.

    Requires:
        - polars. PANEL_SCHEMA.

    Capabilities:
        - sections itemize 를 cross-market 16-col 로 무손실 remap — reader/facade 무변경 동작.

    Guide:
        - ``buildEdgarPanel`` 이 호출. 순수라 테스트는 in-memory long 으로 직접 호출.

    AIContext:
        - 컬럼 일괄 Expr(map_elements 0). null/false/0.0 채움은 narrative 계약(graceful read).

    When:
        - sections long 을 panel 16-col artifact 로 변환할 때.

    How:
        - select(form_type/itemIdExpr/topic/leafType/source_title/null들/blockOrder/contentRaw
          fallback/period/ticker/accession_no/null) → PANEL_SCHEMA cast.

    LLM Specifications:
        AntiPatterns:
            - leafType 에 "heading" 유지 금지 — PANEL_SCHEMA 는 text/table 2값(heading→text).
            - content_raw 빈 셀 그대로 금지 — content_plain fallback(보드 본문 보유).
        OutputSchema:
            - ``pl.DataFrame`` (16-col PANEL_SCHEMA).
        Prerequisites:
            - polars. sections long.
        Freshness:
            - 순수 변환.
        Dataflow:
            - long → 컬럼 Expr remap → PANEL_SCHEMA cast.
        TargetMarkets:
            - US (EDGAR).
    """
    if long is None or long.is_empty():
        return pl.DataFrame(schema=PANEL_SCHEMA)

    cols = set(long.columns)
    topic = pl.col("topic").cast(pl.Utf8).fill_null("")
    blockType = (pl.col("blockType") if "blockType" in cols else pl.lit("text")).cast(pl.Utf8).fill_null("text")
    leafType = pl.when(blockType == "table").then(pl.lit("table")).otherwise(pl.lit("text"))
    raw = (pl.col("content_raw") if "content_raw" in cols else pl.lit(None)).cast(pl.Utf8)
    plain = (pl.col("content_plain") if "content_plain" in cols else pl.lit(None)).cast(pl.Utf8)
    # content_raw 빈/공백(상류 OOM 가드) → content_plain fallback (보드 본문 항상 보유).
    contentRaw = pl.when(raw.is_null() | (raw.str.strip_chars().str.len_chars() == 0)).then(plain).otherwise(raw)

    out = long.select(
        (pl.col("form_type") if "form_type" in cols else pl.lit(None)).cast(pl.Utf8).alias("chapter"),
        itemIdExpr("topic"),  # alias "sectionLeaf"
        topic.alias("sectionPath"),
        leafType.alias("leafType"),
        (pl.col("source_title") if "source_title" in cols else pl.lit(None)).cast(pl.Utf8).alias("blockLeaf"),
        pl.lit(None, dtype=pl.Utf8).alias("xbrlClass"),
        pl.lit(False).alias("xbrlMatched"),
        pl.lit(0.0, dtype=pl.Float32).alias("xbrlMatchScore"),
        pl.lit(None, dtype=pl.Utf8).alias("atocId"),
        pl.lit(None, dtype=pl.Utf8).alias("aassocnote"),
        (pl.col("blockOrder") if "blockOrder" in cols else pl.lit(0)).cast(pl.UInt32).alias("blockOrder"),
        contentRaw.alias("contentRaw"),
        pl.col("period").cast(pl.Utf8).alias("period"),
        (pl.col("ticker") if "ticker" in cols else pl.lit(None)).cast(pl.Utf8).str.to_uppercase().alias("corp"),
        (pl.col("accession_no") if "accession_no" in cols else pl.lit(None)).cast(pl.Utf8).alias("rceptNo"),
        pl.lit(None, dtype=pl.Utf8).alias("disclosureKey"),
    )
    # 16-col schema 순서·dtype 강제 (cross-market 계약).
    return out.select([pl.col(c).cast(dt) for c, dt in PANEL_SCHEMA.items()])


def buildEdgarPanel(ticker: str, *, overwrite: bool = True, verbose: bool = False) -> dict[str, int]:
    """1 ticker: sections artifact → 16-col panel artifact (atomic write).

    ``loadSectionsLong`` (period-sharded long, columnar projection) → ``sectionsToPanel`` remap →
    ``data/edgar/panel/{TICKER}.parquet`` flat 1파일 (HF 폭발 회피 — DART flat 정책 미러). offline —
    network 0(HF lazy 다운로드는 read 표면 책임). per-ticker 순차로 메모리 bound.

    Args:
        ticker: US ticker.
        overwrite: False 면 기존 artifact 존재 시 skip(증분). True(기본) 면 재생성.
        verbose: 진행 로그.

    Returns:
        ``{"rows": N, "periods": M}``. sections 부재/빈 시 ``{"rows": 0, "periods": 0}``.

    Raises:
        없음 — read/write 실패는 warning + {"rows":0,...}.

    Example:
        >>> buildEdgarPanel("AAPL")  # doctest: +SKIP
        {'rows': 919, 'periods': 31}

    SeeAlso:
        - ``sectionsToPanel`` — 순수 remap.
        - ``sectionsStorage.loadSectionsLong`` — sections long read.
        - ``providers.dart.panel.Panel`` — 본 artifact 의 read 표면(marketNs="us").

    Requires:
        - polars. data/edgar/sections/{ticker}/ (gather 산출).

    Capabilities:
        - 한 회사 sections 를 panel 16-col artifact 로 — read 표면이 wide 수평화.

    Guide:
        - CLI ``python -X utf8 -m dartlab.providers.edgar.panel.build --tickers AAPL`` 또는 직접.

    AIContext:
        - offline remap(파싱 0). artifact stale 시 재빌드(파생 체인 — sections 가 truth).

    When:
        - sections 수집 후 panel 보드 artifact 를 생산할 때.

    How:
        - (overwrite=False·존재 시 skip) → loadSectionsLong → sectionsToPanel → .tmp write → replace.

    LLM Specifications:
        AntiPatterns:
            - 전 ticker DataFrame 동시 보관 금지 — per-ticker write 후 해제.
            - sections 부재에 예외 금지 — {"rows":0} graceful.
        OutputSchema:
            - ``dict[str, int]`` ({"rows", "periods"}).
        Prerequisites:
            - sections artifact.
        Freshness:
            - 재빌드 시.
        Dataflow:
            - loadSectionsLong → sectionsToPanel → atomic write.
        TargetMarkets:
            - US (EDGAR).
    """
    target = panelPath(ticker)
    if not overwrite and target.exists():
        if verbose:
            _log.info("edgar panel %s 이미 존재 — skip", ticker.upper())
        try:
            existing = pl.read_parquet(str(target), columns=["period"])
            return {"rows": int(existing.height), "periods": int(existing["period"].n_unique())}
        except (OSError, pl.exceptions.PolarsError):
            pass  # 손상 시 재빌드로 진행
    long = loadSectionsLong(ticker, columns=_SOURCE_COLS)
    if long is None or long.is_empty():
        if verbose:
            _log.info("edgar sections %s 부재 — panel build skip", ticker.upper())
        return {"rows": 0, "periods": 0}
    panel = sectionsToPanel(long)
    if panel.is_empty():
        return {"rows": 0, "periods": 0}
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".parquet.tmp")
    try:
        panel.write_parquet(str(tmp), compression="zstd")
        tmp.replace(target)
    except (OSError, pl.exceptions.PolarsError) as exc:
        _log.warning("edgar panel %s write 실패: %s", ticker.upper(), exc)
        tmp.unlink(missing_ok=True)
        return {"rows": 0, "periods": 0}
    periods = int(panel["period"].n_unique())
    if verbose:
        _log.info("edgar panel %s: %d rows, %d periods", ticker.upper(), panel.height, periods)
    return {"rows": int(panel.height), "periods": periods}


def buildEdgarPanelAll(
    tickers: list[str] | None = None, *, overwrite: bool = True, verbose: bool = False
) -> dict[str, dict]:
    """여러 ticker 순차 build (resumable — per-ticker 독립).

    ticker 를 **순차**(병렬 0) 처리 — Polars Rust heap OOM 가드(per-ticker read+remap 후 해제).
    ``tickers=None`` 이면 ``data/edgar/sections/*/`` 디렉터리(=수집된 회사) 전수 스캔.

    Args:
        tickers: ticker list. None 이면 sections 디렉터리 전수.
        overwrite: False 면 기존 panel artifact skip(증분).
        verbose: 진행 로그.

    Returns:
        ``{ticker: {"rows": N, "periods": M}}``.

    Raises:
        없음 — ticker 별 실패는 {"rows":0} 로 흡수(전체 resumable).

    Example:
        >>> buildEdgarPanelAll(["AAPL", "MSFT"])  # doctest: +SKIP
        {'AAPL': {'rows': 919, 'periods': 31}, 'MSFT': {...}}

    SeeAlso:
        - ``buildEdgarPanel`` — 단일 ticker.

    Requires:
        - polars. data/edgar/sections/.

    Capabilities:
        - 전(또는 일부) 수집 회사를 순차 build — resumable, OOM 가드.

    Guide:
        - CLI ``--all`` 또는 ``--tickers``. 직접 호출 가능.

    AIContext:
        - 순차(병렬 0). 한 ticker 실패가 다음 ticker 막지 않음.

    When:
        - 다회사 panel artifact 를 일괄 생산할 때.

    How:
        - (tickers None 이면 sections dir 스캔) → 순차 buildEdgarPanel.

    LLM Specifications:
        AntiPatterns:
            - 병렬 fan-out 금지 — 순차(OOM 가드).
        OutputSchema:
            - ``dict[str, dict]``.
        Prerequisites:
            - sections artifact.
        Freshness:
            - 재빌드 시.
        Dataflow:
            - tickers → 순차 buildEdgarPanel.
        TargetMarkets:
            - US (EDGAR).
    """
    if tickers is None:
        sectionsRoot = Path(_cfg.dataDir) / "edgar" / "sections"
        tickers = sorted(p.name for p in sectionsRoot.glob("*") if p.is_dir()) if sectionsRoot.exists() else []
    out: dict[str, dict] = {}
    for tk in tickers:
        out[tk.upper()] = buildEdgarPanel(tk, overwrite=overwrite, verbose=verbose)
    return out
