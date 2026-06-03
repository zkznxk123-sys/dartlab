"""EDGAR panel build — raw `.txt` → 16-col 보드 + EDGAR_CELL 셀 (DART panel.build 미러, 자급).

gather 원본 ``data/original/edgar/docs/{cik}/{accession}.txt`` 를 직접 파싱해 ① 16-col
``PANEL_SCHEMA`` 보드(재무제표 disclosureKey 앵커링, 서술 null) → ``data/edgar/panel/{ticker}.parquet``,
② ``EDGAR_CELL_SCHEMA`` 셀(계정×기간) → ``data/edgar/panelCell/{ticker}.parquet`` 생산. sections·gather·
meta 의존 0(자급, 전 history). DART ``buildPanel`` 의 EDGAR 미러 — zip 대신 SEC full-submission `.txt`.

LLM Specifications:
    AntiPatterns:
        - sections/gather/meta import 금지 — 원본 `.txt` 자급(폐기-무관).
        - 전 ticker 동시 로드 금지 — per-ticker 순차(거대 `.txt` 메모리 bound).
        - 비-재무 폼(8-K/DEF 14A) 포함 금지 — 10-K/10-Q/20-F/40-F 만.
    OutputSchema:
        - ``buildEdgarPanel(ticker, ...) -> dict`` ({"rows","cells","periods","filings"}).
        - ``filingToBoardAndCells(txtPath, *, ticker) -> tuple[list, list]``.
    Prerequisites:
        - polars. lxml(walker, build 전용). data/original/edgar/docs/. tickers.parquet.
    Freshness:
        - 원본 변경 시 재빌드 (offline — network 0).
    Dataflow:
        - {cik}/*.txt → submission/instance/linkbase/walker/cell → 보드+셀 2 parquet.
    TargetMarkets:
        - US.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.panel.schema import PANEL_SCHEMA

from .cell import buildCells
from .cellSchema import EDGAR_CELL_SCHEMA
from .instance import extractContexts, extractFacts, extractInstanceFacts
from .linkbase import parseLabels, parsePresentation
from .mapper import periodFromReport
from .submission import parseSubmission
from .walker import buildStatementConcepts, walkBody

_log = logging.getLogger(__name__)

_PANEL_REL = "edgar/panel"
_CELL_REL = "edgar/panelCell"
_REGULAR_FORMS = frozenset({"10-K", "10-Q", "20-F", "40-F"})
# content_raw in-memory 가드 (거대 filing HTML 누적 폭증 차단 — sectionsBuilder 가드 미러).
_CONTENT_RAW_MEM_CAP = 1_500_000_000


def panelPath(ticker: str) -> Path:
    """보드 artifact 경로 — ``data/edgar/panel/{TICKER}.parquet`` (read 표면 marketNs="us" 경로)."""
    return Path(_cfg.dataDir) / _PANEL_REL / f"{ticker.upper()}.parquet"


def panelCellPath(ticker: str) -> Path:
    """셀 artifact 경로 — ``data/edgar/panelCell/{TICKER}.parquet`` (cellRead 경로)."""
    return Path(_cfg.dataDir) / _CELL_REL / f"{ticker.upper()}.parquet"


def resolveCikForTicker(ticker: str) -> str | None:
    """ticker → 10자리 CIK (``data/edgar/tickers.parquet`` 직접 read, gather import 0).

    Args:
        ticker: US ticker (대소문자 무관).

    Returns:
        10자리 zero-pad CIK 또는 None (미등재/파일 부재).

    Raises:
        없음.

    Example:
        >>> resolveCikForTicker("AAR")  # doctest: +SKIP
        '0000001750'
    """
    p = Path(_cfg.dataDir) / "edgar" / "tickers.parquet"
    if not p.exists():
        return None
    try:
        df = pl.read_parquet(str(p), columns=["cik", "ticker"])
    except (OSError, pl.exceptions.PolarsError):
        return None
    hit = df.filter(pl.col("ticker").cast(pl.Utf8).str.to_uppercase() == ticker.upper())
    if hit.is_empty():
        return None
    return str(hit["cik"][0]).strip().zfill(10)


def filingToBoardAndCells(txtPath: Path, *, ticker: str) -> tuple[list[dict], list[dict]]:
    """1 filing `.txt` → (보드 16-col rows, 셀 EDGAR_CELL rows). 비-재무 폼/파싱불가는 ([], []).

    submission → (header, primary HTML, EX-101.PRE/LAB) → instance(facts+contexts) +
    linkbase(roles+labels) → walker(보드, 재무표 앵커링) + cell(셀). pre-XBRL(링크베이스/fact 부재)
    필링은 서술 보드만(앵커 0, 셀 0) — DART era 미러.

    Args:
        txtPath: ``data/original/edgar/docs/{cik}/{accession}.txt``.
        ticker: US ticker (corp 컬럼).

    Returns:
        ``(boardRows, cellRows)``. 보드 행은 16-col PANEL_SCHEMA 키, 셀 행은 EDGAR_CELL_SCHEMA 키.

    Raises:
        없음 — read/parse 실패는 ([], []).

    Example:
        >>> board, cells = filingToBoardAndCells(Path(".../0001410578-25-001475.txt"), ticker="AAR")  # doctest: +SKIP

    SeeAlso:
        - ``submission.parseSubmission`` / ``walker.walkBody`` / ``cell.buildCells``.
    """
    try:
        txt = txtPath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], []
    sub = parseSubmission(txt)
    form = (sub.get("form") or "").upper()
    if form not in _REGULAR_FORMS or not sub.get("primaryHtml"):
        return [], []
    filingPeriod = periodFromReport(form, sub.get("periodOfReport"))
    if not filingPeriod:
        return [], []
    accession = sub.get("accession") or txtPath.stem

    roles = parsePresentation(sub.get("ex101Pre") or "")
    labels = parseLabels(sub.get("ex101Lab") or "")
    statementConcepts = buildStatementConcepts(roles)
    primaryHtml = sub["primaryHtml"]

    # 보드 (walker) — 재무표 disclosureKey 앵커링.
    leafRows = walkBody(primaryHtml, formType=form, statementConcepts=statementConcepts)
    board: list[dict] = []
    for r in leafRows:
        board.append(
            {
                "chapter": r["chapter"],
                "sectionLeaf": r["sectionLeaf"],
                "sectionPath": r["sectionPath"],
                "leafType": r["leafType"],
                "blockLeaf": r["blockLeaf"],
                "xbrlClass": r["xbrlClass"],
                "xbrlMatched": r["disclosureKey"] is not None,
                "xbrlMatchScore": 1.0 if r["disclosureKey"] else 0.0,
                "atocId": None,
                "aassocnote": None,
                "blockOrder": r["blockOrder"],
                "contentRaw": r["contentRaw"],
                "period": filingPeriod,
                "corp": ticker.upper(),
                "rceptNo": accession,
                "disclosureKey": r["disclosureKey"],
            }
        )

    # 셀 (cell) — fact × context × role 분해. facts 는 inline(ix:, ≈2021+) + native EX-101.INS
    # (separate-instance, ≈2012~2020) 합집합 → deep history. context 도 inline+INS 병합.
    cells: list[dict] = []
    if roles:
        insXml = sub.get("ex101Ins") or ""
        facts = extractFacts(primaryHtml) + extractInstanceFacts(insXml)
        contexts = extractContexts(primaryHtml)
        if insXml:
            for cid, cval in extractContexts(insXml).items():
                contexts.setdefault(cid, cval)
        fyEnd = sub.get("fiscalYearEnd")  # "MMDD"
        fyEndMonth = int(fyEnd[:2]) if fyEnd and len(fyEnd) == 4 and fyEnd[:2].isdigit() else None
        cells = buildCells(
            facts,
            contexts,
            roles,
            labels,
            meta={
                "ticker": ticker.upper(),
                "accession": accession,
                "filingPeriod": filingPeriod,
                "fyEndMonth": fyEndMonth,
            },
        )
    return board, cells


def _applyContentRawCap(board: list[dict], ticker: str) -> None:
    """누적 content_raw bytes 가 cap 초과 시 content_raw 비움 (in-place, OOM 가드)."""
    total = 0
    for r in board:
        cr = r.get("contentRaw")
        total += len(cr) if cr else 0
        if total > _CONTENT_RAW_MEM_CAP:
            break
    if total > _CONTENT_RAW_MEM_CAP:
        _log.warning("%s board content_raw ~%.1fGB > cap — content_raw 비움", ticker, total / 1e9)
        for r in board:
            r["contentRaw"] = ""


def _writeParquet(rows: list[dict], schema: dict, target: Path) -> int:
    """rows(dict-of-list 구성) → schema parquet atomic write. 행 수 반환."""
    if not rows:
        return 0
    cols = {k: [r.get(k) for r in rows] for k in schema}
    df = pl.DataFrame(cols, schema=schema)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".parquet.tmp")
    df.write_parquet(str(tmp), compression="zstd")
    tmp.replace(target)
    return int(df.height)


def buildEdgarPanel(ticker: str, *, overwrite: bool = True, verbose: bool = False) -> dict[str, int]:
    """1 ticker: 원본 `.txt` 전수 → 보드 + 셀 2 artifact (자급, offline).

    ticker→cik 해소 후 ``data/original/edgar/docs/{cik}/*.txt`` 전 필링을 파싱(재무 폼만) → 보드/셀
    누적 → 2 parquet write. content_raw mem-cap 가드.

    Args:
        ticker: US ticker.
        overwrite: False 면 보드 artifact 존재 시 skip(증분).
        verbose: 진행 로그.

    Returns:
        ``{"rows", "cells", "periods", "filings"}``. cik/원본 부재 시 0.

    Raises:
        없음 — 필링별 실패는 흡수(resumable).

    Example:
        >>> buildEdgarPanel("AAR")  # doctest: +SKIP
        {'rows': 4100, 'cells': 12500, 'periods': 17, 'filings': 17}

    SeeAlso:
        - ``filingToBoardAndCells`` — 1 필링.
        - ``providers.dart.panel.Panel`` — 보드 read(marketNs="us").
        - ``providers.edgar.panel.cellRead`` — 셀 read.

    Requires:
        - polars. lxml. data/original/edgar/docs/. tickers.parquet.

    Capabilities:
        - 한 회사 전 필링을 XBRL 앵커 보드 + 셀로 — DART buildPanel 의 EDGAR 미러.

    Guide:
        - CLI ``python -X utf8 -m dartlab.providers.edgar.panel.build --tickers AAR``.

    AIContext:
        - offline 자급(network 0). 거대 `.txt` per-filing 처리 + mem-cap.

    When:
        - 원본 수집 후 panel artifact 생산.

    How:
        - cik 해소 → *.txt glob → filingToBoardAndCells 누적 → 2 parquet.

    LLM Specifications:
        AntiPatterns:
            - 비-재무 폼 포함 금지. 전 ticker 병렬 금지(순차).
        OutputSchema:
            - ``dict[str, int]``.
        Prerequisites:
            - 원본 `.txt` + tickers.parquet.
        Freshness:
            - 재빌드 시.
        Dataflow:
            - *.txt → 보드/셀 → write.
        TargetMarkets:
            - US.
    """
    target = panelPath(ticker)
    if not overwrite and target.exists():
        try:
            ex = pl.read_parquet(str(target), columns=["period"])
            return {"rows": int(ex.height), "cells": 0, "periods": int(ex["period"].n_unique()), "filings": 0}
        except (OSError, pl.exceptions.PolarsError):
            pass
    cik = resolveCikForTicker(ticker)
    if not cik:
        if verbose:
            _log.info("edgar panel %s: cik 미해소 — skip", ticker.upper())
        return {"rows": 0, "cells": 0, "periods": 0, "filings": 0}
    cikDir = Path(_cfg.dataDir) / "original" / "edgar" / "docs" / cik
    if not cikDir.exists():
        if verbose:
            _log.info("edgar panel %s: 원본 %s 부재 — skip", ticker.upper(), cikDir)
        return {"rows": 0, "cells": 0, "periods": 0, "filings": 0}

    board: list[dict] = []
    cells: list[dict] = []
    filings = 0
    for txtPath in sorted(cikDir.glob("*.txt")):
        b, c = filingToBoardAndCells(txtPath, ticker=ticker)
        if b:
            board.extend(b)
            cells.extend(c)
            filings += 1
    if not board:
        return {"rows": 0, "cells": 0, "periods": 0, "filings": 0}

    _applyContentRawCap(board, ticker.upper())
    nRows = _writeParquet(board, PANEL_SCHEMA, target)
    nCells = _writeParquet(cells, EDGAR_CELL_SCHEMA, panelCellPath(ticker)) if cells else 0
    periods = len({r["period"] for r in board})
    if verbose:
        _log.info(
            "edgar panel %s: %d board rows, %d cells, %d periods, %d filings",
            ticker.upper(),
            nRows,
            nCells,
            periods,
            filings,
        )
    return {"rows": nRows, "cells": nCells, "periods": periods, "filings": filings}


def buildEdgarPanelAll(
    tickers: list[str] | None = None, *, overwrite: bool = True, verbose: bool = False
) -> dict[str, dict]:
    """여러 ticker 순차 build (resumable, OOM 가드 — per-ticker). tickers=None 이면 원본 디렉터리 전수.

    Args:
        tickers: ticker list. None 이면 ``data/original/edgar/docs/`` 의 cik → ticker 역해소 전수.
        overwrite: False 면 기존 보드 skip(증분).
        verbose: 진행 로그.

    Returns:
        ``{ticker: {"rows","cells","periods","filings"}}``.

    Raises:
        없음.

    Example:
        >>> buildEdgarPanelAll(["AAR"])  # doctest: +SKIP

    SeeAlso:
        - ``buildEdgarPanel`` — 단일.
    """
    if tickers is None:
        # 원본 cik → ticker 역해소 (tickers.parquet).
        root = Path(_cfg.dataDir) / "original" / "edgar" / "docs"
        ciks = sorted(p.name for p in root.glob("*") if p.is_dir()) if root.exists() else []
        tickers = _ciksToTickers(ciks)
    out: dict[str, dict] = {}
    for tk in tickers:
        out[tk.upper()] = buildEdgarPanel(tk, overwrite=overwrite, verbose=verbose)
    return out


def _ciksToTickers(ciks: list[str]) -> list[str]:
    """cik list → ticker list (tickers.parquet 역해소, 미등재 skip)."""
    p = Path(_cfg.dataDir) / "edgar" / "tickers.parquet"
    if not p.exists():
        return []
    try:
        df = pl.read_parquet(str(p), columns=["cik", "ticker"])
    except (OSError, pl.exceptions.PolarsError):
        return []
    cikSet = {c.zfill(10) for c in ciks}
    hit = df.filter(pl.col("cik").cast(pl.Utf8).str.zfill(10).is_in(list(cikSet)))
    return sorted(hit["ticker"].cast(pl.Utf8).to_list())
