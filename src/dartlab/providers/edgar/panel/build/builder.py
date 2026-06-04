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
    """보드 artifact 경로 — ``data/edgar/panel/{TICKER}.parquet`` (read 표면 marketNs="us" 경로).

    Args:
        ticker: US ticker (대소문자 무관, ``upper()`` 정규화).

    Returns:
        ``data/edgar/panel/{TICKER}.parquet`` Path (``read._panelDir(code,"us").parent`` 와 동일).

    Raises:
        없음.

    Example:
        >>> panelPath("aapl").name
        'AAPL.parquet'
    """
    return Path(_cfg.dataDir) / _PANEL_REL / f"{ticker.upper()}.parquet"


def panelCellPath(ticker: str) -> Path:
    """셀 artifact 경로 — ``data/edgar/panelCell/{TICKER}.parquet`` (cellRead 경로).

    Args:
        ticker: US ticker (대소문자 무관, ``upper()`` 정규화).

    Returns:
        ``data/edgar/panelCell/{TICKER}.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> panelCellPath("aapl").name
        'AAPL.parquet'
    """
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


def existingAccessions(ticker: str) -> set[str]:
    """기존 panel artifact 의 ``rceptNo``(=accession) 집합 — 증분 append 중복 판정용.

    Args:
        ticker: US ticker.

    Returns:
        set[str] — 기존 보드 parquet 의 accession 집합. 파일 부재/오류 시 빈 집합.

    Raises:
        없음.

    Example:
        >>> existingAccessions("AAR")  # doctest: +SKIP
        {'0001410578-25-001475', ...}
    """
    p = panelPath(ticker)
    if not p.exists():
        return set()
    try:
        df = pl.read_parquet(str(p), columns=["rceptNo"])
    except (OSError, pl.exceptions.PolarsError):
        return set()
    return set(df["rceptNo"].cast(pl.Utf8).to_list())


def _rowsToDf(rows: list[dict], schema: dict) -> pl.DataFrame:
    """rows(dict list) → schema DataFrame (열 순서·타입 고정)."""
    return pl.DataFrame({k: [r.get(k) for r in rows] for k in schema}, schema=schema)


def _mergeKeepingSchema(target: Path, newRows: list[dict], schema: dict, accessions: set[str]) -> pl.DataFrame:
    """기존 artifact 에서 ``accessions`` 행 제거 후 newRows append — schema 정렬 보존.

    같은 accession(정정/재제출)은 기존 행 제거 후 재삽입(idempotent). 기존 부재면 newRows 만.
    """
    newDf = _rowsToDf(newRows, schema)
    if not target.exists():
        return newDf
    try:
        existing = pl.read_parquet(str(target))
    except (OSError, pl.exceptions.PolarsError):
        return newDf
    for c in schema:  # schema 진화 대비 — 누락 컬럼 null 보강
        if c not in existing.columns:
            existing = existing.with_columns(pl.lit(None).alias(c))
    existing = existing.select(list(schema)).filter(~pl.col("rceptNo").is_in(list(accessions)))
    merged = pl.concat([existing, newDf], how="vertical_relaxed")
    # vertical_relaxed 는 *기존* dtype 으로 수렴 → 옛 parquet 의 dtype drift(Utf8/Int64 등)가
    # 살아남아 schema 계약 위반. 병합 후 schema dtype 으로 강제 재캐스트. strict=True 면 옛 parquet
    # 1개의 drift 가 ticker 전체 빌드를 죽이므로 strict=False(실패시 null)로 회복력 우선 — 단 비-null
    # 값이 null 로 *조용히* 사라지면(오버플로/파싱불가=진짜 손실) 경고로 관측화.
    recast = merged.select([pl.col(c).cast(dt, strict=False) for c, dt in schema.items()])
    for c, dt in schema.items():
        if dt == pl.Utf8:
            continue  # Utf8 캐스트는 사실상 무손실 — 수치 컬럼만 손실 검사
        before = int(merged.select(pl.col(c).is_not_null().sum()).item())
        after = int(recast.select(pl.col(c).is_not_null().sum()).item())
        if after < before:
            _log.warning(
                "edgar merge cast %s: 비-null→null %d (dtype drift 손실) target=%s", c, before - after, target.name
            )
    return recast


def _writeDf(df: pl.DataFrame, target: Path) -> int:
    """DataFrame → parquet atomic write(tmp→replace). 행 수 반환."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".parquet.tmp")
    df.write_parquet(str(tmp), compression="zstd")
    tmp.replace(target)
    return int(df.height)


def _capContentRawDf(df: pl.DataFrame) -> pl.DataFrame:
    """병합 board 의 누적 content_raw bytes 가 cap 초과면 비움(append 시 OOM 가드, df 버전)."""
    if "contentRaw" not in df.columns:
        return df
    total = df.select(pl.col("contentRaw").str.len_bytes().sum()).item() or 0
    if total > _CONTENT_RAW_MEM_CAP:
        _log.warning("edgar append content_raw ~%.1fGB > cap — content_raw 비움", total / 1e9)
        return df.with_columns(pl.lit("").alias("contentRaw"))
    return df


def appendFilingsToPanel(ticker: str, txtPaths: list[Path], *, verbose: bool = False) -> dict[str, int]:
    """신규 filing ``.txt`` 들을 기존 panel/panelCell 에 **append** (accession dedup, atomic).

    Capabilities:
        - 전체 history 재빌드 없이 신규 accession 의 보드/셀만 기존 artifact 에 병합한다
          (per-filing 증분). 같은 accession 이 기존에 있으면 제거 후 재삽입(정정 idempotent).
          기존 artifact 부재면 받은 filing 들만으로 생성. raw txt 폐기 전략과 정합 — 호출부가
          신규 accession 의 .txt 만 받아 넘기면 되고 full 디스크 history 가 불필요.

    Args:
        ticker: US ticker.
        txtPaths: 신규 filing full submission ``.txt`` 경로 list.
        verbose: 진행 로그.

    Returns:
        ``{"rows","cells","appended"}`` — 병합 후 보드/셀 총행수 + append 한 accession 수.

    Raises:
        없음 — 파싱 실패 filing 은 흡수.

    Example:
        >>> appendFilingsToPanel("AAR", [Path(".../0001410578-25-001475.txt")])  # doctest: +SKIP
        {'rows': 4220, 'cells': 12900, 'appended': 1}

    SeeAlso:
        - ``buildEdgarPanel`` — 단일 ticker 전체 빌드(부트스트랩/신규 종목).
        - ``existingAccessions`` — append 전 중복 판정.
        - ``gather.original.edgar.collect.listRecentFilings`` — 신규 발견.

    Requires:
        - polars. lxml. 신규 filing ``.txt``.

    When:
        - EDGAR panel 일간 증분: 기존 종목에 신규 공시 1+ 건 도착 시.

    How:
        - filingToBoardAndCells 누적 → 기존 parquet 에서 동일 accession 제거 후 concat → 2 parquet write.

    AIContext:
        - offline 자급(network 0). per-ticker 소량 메모리.

    LLM Specifications:
        AntiPatterns:
            - 신규 외 전 history .txt 를 넘기지 말 것 — 그건 buildEdgarPanel(overwrite) 영역.
            - 동일 accession 중복 우려로 호출부에서 직접 dedup 하지 말 것 — 본 함수가 처리.
        OutputSchema:
            - ``dict[str, int]``.
        Prerequisites:
            - 신규 filing .txt + (선택)기존 artifact.
        Freshness:
            - 신규 공시 도착 시 append.
        Dataflow:
            - 신규 .txt → 보드/셀 → 기존 merge(dedup) → write.
        TargetMarkets:
            - US.
    """
    newBoard: list[dict] = []
    newCells: list[dict] = []
    for tp in txtPaths:
        b, c = filingToBoardAndCells(tp, ticker=ticker)
        if b:
            newBoard.extend(b)
            newCells.extend(c)
    if not newBoard:
        return {"rows": 0, "cells": 0, "appended": 0}

    _applyContentRawCap(newBoard, ticker.upper())
    accessions = {r["rceptNo"] for r in newBoard}

    mergedBoard = _mergeKeepingSchema(panelPath(ticker), newBoard, PANEL_SCHEMA, accessions)
    mergedBoard = _capContentRawDf(mergedBoard)  # 병합 후 누적 cap(existing+new 합산)
    nRows = _writeDf(mergedBoard, panelPath(ticker))

    # panelCell 도 *항상* accessions 로 prune — newCells 가 비어도(셀 0 공시/셀 없는 정정) 기존
    # 동일 accession 의 옛 셀을 제거해 board↔cell 정합(idempotent append)을 유지한다. 단 기존
    # cell 파일도 없고 새 셀도 없으면 빈 파일 생성을 피한다(board-only 종목).
    nCells = 0
    cellTarget = panelCellPath(ticker)
    if newCells or cellTarget.exists():
        mergedCells = _mergeKeepingSchema(cellTarget, newCells, EDGAR_CELL_SCHEMA, accessions)
        nCells = _writeDf(mergedCells, cellTarget)

    if verbose:
        _log.info(
            "edgar panel append %s: +%d filings → %d board rows, %d cells",
            ticker.upper(),
            len(accessions),
            nRows,
            nCells,
        )
    return {"rows": nRows, "cells": nCells, "appended": len(accessions)}


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
