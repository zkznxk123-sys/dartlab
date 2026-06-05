"""EDGAR panel build — SEC full-submission text → 16-col panel (DART panel.build mirror).

SEC full-submission ``.txt`` 는 디스크 원본 artifact 로 저장하지 않는다. 호출자가 fetch 한 텍스트를
메모리로 넘기면 build 가 즉시 파싱해 ``data/edgar/panel/{ticker}.parquet`` 만 생산한다. native
재무 셀은 같은 panel row ``contentRaw`` payload 로 보존해 read-time 분해한다. 별도 artifact 는 없다.

LLM Specifications:
    AntiPatterns:
        - sections/gather/meta import 금지 — full-submission text 자급 파싱.
        - 전 ticker 동시 로드 금지 — per-ticker 순차(거대 `.txt` 메모리 bound).
        - 비-재무 폼(8-K/DEF 14A) 포함 금지 — 10-K/10-Q/20-F/40-F 만.
    OutputSchema:
        - ``buildEdgarPanel(ticker, filings, ...) -> dict`` ({"rows","periods","filings"}).
        - ``filingTextToBoard(txt, *, ticker, accession=None) -> list``.
    Prerequisites:
        - polars. lxml(walker, build 전용). tickers.parquet.
    Freshness:
        - SEC fetch 결과 변경 시 재빌드.
    Dataflow:
        - full-submission text → submission/linkbase/walker/native payload → panel parquet.
    TargetMarkets:
        - US.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import polars as pl

import dartlab.config as _cfg
from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
from dartlab.providers.edgar.panel.native import encodeNativeCellsPayload

from .instance import extractContexts, extractFacts, extractInstanceFacts
from .linkbase import parseLabels, parsePresentation
from .mapper import periodFromReport
from .nativeCells import buildNativeCells
from .submission import parseSubmission
from .walker import buildStatementConcepts, walkBody

_log = logging.getLogger(__name__)

_PANEL_REL = "edgar/panel"
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


def _attachNativePayload(
    board: list[dict],
    cells: list[dict],
    *,
    form: str,
    filingPeriod: str,
    ticker: str,
    accession: str,
) -> None:
    """native cells 를 statement row ``contentRaw`` 에 payload 로 붙인다."""
    if not cells:
        return
    byStmt: dict[str, list[dict]] = {}
    for cell in cells:
        stmt = cell.get("statement")
        if stmt:
            byStmt.setdefault(stmt, []).append(cell)
    if not byStmt:
        return
    nextOrder = max((int(r.get("blockOrder") or 0) for r in board), default=-1) + 1
    for stmt, stmtCells in byStmt.items():
        payload = encodeNativeCellsPayload(stmtCells)
        if not payload:
            continue
        target = next((r for r in board if r.get("disclosureKey") == stmt), None)
        if target is not None:
            target["contentRaw"] = (target.get("contentRaw") or "") + payload
            continue
        board.append(
            {
                "chapter": form,
                "sectionLeaf": stmt,
                "sectionPath": f"{form}␟{stmt}",
                "leafType": "table",
                "blockLeaf": stmt,
                "xbrlClass": None,
                "xbrlMatched": True,
                "xbrlMatchScore": 1.0,
                "atocId": None,
                "aassocnote": None,
                "blockOrder": nextOrder,
                "contentRaw": payload,
                "period": filingPeriod,
                "corp": ticker.upper(),
                "rceptNo": accession,
                "disclosureKey": stmt,
            }
        )
        nextOrder += 1


def filingTextToBoard(txt: str, *, ticker: str, accession: str | None = None) -> list[dict]:
    """1 full-submission text → panel board rows. 비-재무 폼/파싱불가는 ``[]``.

    submission → (header, primary HTML, EX-101.PRE/LAB/INS) → presentation role → walker.
    EDGAR 재무표는 ``disclosureKey`` 로 앵커링하고 native cell 은 row payload 로 보존한다.

    Args:
        txt: SEC full-submission 원문.
        ticker: US ticker (corp 컬럼).
        accession: header accession 이 없을 때 쓸 fallback.

    Returns:
        보드 행 list. 행은 16-col ``PANEL_SCHEMA`` 키.

    Raises:
        없음 — parse 실패는 ``[]``.

    Example:
        >>> board = filingTextToBoard("...", ticker="AAR")  # doctest: +SKIP

    SeeAlso:
        - ``submission.parseSubmission`` / ``walker.walkBody``.
    """
    sub = parseSubmission(txt)
    form = (sub.get("form") or "").upper()
    if form not in _REGULAR_FORMS or not sub.get("primaryHtml"):
        return []
    filingPeriod = periodFromReport(form, sub.get("periodOfReport"))
    if not filingPeriod:
        return []
    accessionNo = sub.get("accession") or accession or ""
    if not accessionNo:
        return []

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
                "rceptNo": accessionNo,
                "disclosureKey": r["disclosureKey"],
            }
        )
    insXml = sub.get("ex101Ins") or ""
    facts = extractFacts(primaryHtml) + extractInstanceFacts(insXml)
    contexts = extractContexts(primaryHtml)
    if insXml:
        for cid, cval in extractContexts(insXml).items():
            contexts.setdefault(cid, cval)
    fyEnd = sub.get("fiscalYearEnd")
    fyEndMonth = int(fyEnd[:2]) if fyEnd and len(fyEnd) == 4 and fyEnd[:2].isdigit() else None
    cells = buildNativeCells(
        facts,
        contexts,
        roles,
        labels,
        meta={
            "ticker": ticker.upper(),
            "accession": accessionNo,
            "filingPeriod": filingPeriod,
            "fyEndMonth": fyEndMonth,
        },
    )
    _attachNativePayload(board, cells, form=form, filingPeriod=filingPeriod, ticker=ticker, accession=accessionNo)
    return board


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


def _recordTextAndAccession(record: str | Mapping[str, Any]) -> tuple[str, str | None]:
    """fetch result record → ``(text, accession)``."""
    if isinstance(record, str):
        return record, None
    text = record.get("text") or record.get("content") or record.get("txt") or ""
    accession = record.get("accession_no") or record.get("accession") or record.get("rceptNo")
    return str(text), str(accession) if accession else None


def buildEdgarPanel(
    ticker: str,
    filings: Iterable[str | Mapping[str, Any]] | None = None,
    *,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, int]:
    """1 ticker: full-submission texts → panel 단일 artifact.

    ``filings`` 로 받은 SEC full-submission text 를 순차 파싱해
    ``data/edgar/panel/{ticker}.parquet`` 만 쓴다. 원문 `.txt` 저장과 별도 ``panelCell`` 저장은 하지 않는다.

    Args:
        ticker: US ticker.
        filings: full-submission text 또는 ``{"text", "accession_no"}`` record iterable.
        overwrite: False 면 보드 artifact 존재 시 skip(증분).
        verbose: 진행 로그.

    Returns:
        ``{"rows", "periods", "filings"}``.

    Raises:
        없음 — 필링별 실패는 흡수(resumable).

    Example:
        >>> buildEdgarPanel("AAR", [{"text": "...", "accession_no": "..."}])  # doctest: +SKIP
        {'rows': 4100, 'periods': 17, 'filings': 17}

    SeeAlso:
        - ``filingTextToBoard`` — 1 필링.
        - ``providers.dart.panel.Panel`` — 보드 read(marketNs="us").

    Requires:
        - polars. lxml. SEC full-submission text.

    Capabilities:
        - 한 회사 필링들을 XBRL 앵커 보드로 — DART buildPanel 의 EDGAR 미러.

    Guide:
        - pipeline/sync 가 fetch 한 text record 를 넘겨 호출.

    AIContext:
        - 거대 full-submission text per-filing 처리 + mem-cap.

    When:
        - SEC fetch 직후 panel artifact 생산.

    How:
        - text records → filingTextToBoard 누적 → panel parquet.

    LLM Specifications:
        AntiPatterns:
            - 비-재무 폼 포함 금지. 전 ticker 병렬 금지(순차).
        OutputSchema:
            - ``dict[str, int]``.
        Prerequisites:
            - full-submission text records.
        Freshness:
            - 재빌드 시.
        Dataflow:
            - text → board → write.
        TargetMarkets:
            - US.
    """
    target = panelPath(ticker)
    if not overwrite and target.exists():
        try:
            ex = pl.read_parquet(str(target), columns=["period"])
            return {"rows": int(ex.height), "periods": int(ex["period"].n_unique()), "filings": 0}
        except (OSError, pl.exceptions.PolarsError):
            pass
    if filings is None:
        if verbose:
            _log.info("edgar panel %s: filing text 0 — skip", ticker.upper())
        return {"rows": 0, "periods": 0, "filings": 0}

    board: list[dict] = []
    nFilings = 0
    for record in filings:
        txt, accession = _recordTextAndAccession(record)
        if not txt:
            continue
        b = filingTextToBoard(txt, ticker=ticker, accession=accession)
        if b:
            board.extend(b)
            nFilings += 1
    if not board:
        return {"rows": 0, "periods": 0, "filings": 0}

    _applyContentRawCap(board, ticker.upper())
    nRows = _writeParquet(board, PANEL_SCHEMA, target)
    periods = len({r["period"] for r in board})
    if verbose:
        _log.info(
            "edgar panel %s: %d board rows, %d periods, %d filings",
            ticker.upper(),
            nRows,
            periods,
            nFilings,
        )
    return {"rows": nRows, "periods": periods, "filings": nFilings}


def buildEdgarPanelAll(
    filingsByTicker: Mapping[str, Iterable[str | Mapping[str, Any]]] | None = None,
    *,
    overwrite: bool = True,
    verbose: bool = False,
) -> dict[str, dict]:
    """여러 ticker 순차 build (resumable, OOM 가드 — per-ticker).

    Args:
        filingsByTicker: ``{ticker: full-submission text records}``.
        overwrite: False 면 기존 보드 skip(증분).
        verbose: 진행 로그.

    Returns:
        ``{ticker: {"rows","cells","periods","filings"}}``.

    Raises:
        없음.

    Example:
        >>> buildEdgarPanelAll({"AAR": [{"text": "..."}]})  # doctest: +SKIP

    SeeAlso:
        - ``buildEdgarPanel`` — 단일.
    """
    out: dict[str, dict] = {}
    if not filingsByTicker:
        return out
    for tk, filings in filingsByTicker.items():
        out[tk.upper()] = buildEdgarPanel(tk, filings, overwrite=overwrite, verbose=verbose)
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


def appendFilingTextsToPanel(
    ticker: str, filings: Iterable[str | Mapping[str, Any]], *, verbose: bool = False
) -> dict[str, int]:
    """신규 full-submission text 들을 기존 panel 에 **append** (accession dedup, atomic).

    Capabilities:
        - 전체 history 재빌드 없이 신규 accession 의 보드만 기존 artifact 에 병합한다.
          같은 accession 이 기존에 있으면 제거 후 재삽입(정정 idempotent). 기존 artifact 부재면
          받은 filing 들만으로 생성한다.

    Args:
        ticker: US ticker.
        filings: 신규 filing full-submission text 또는 ``{"text", "accession_no"}`` records.
        verbose: 진행 로그.

    Returns:
        ``{"rows","appended"}`` — 병합 후 보드 총행수 + append 한 accession 수.

    Raises:
        없음 — 파싱 실패 filing 은 흡수.

    Example:
        >>> appendFilingTextsToPanel("AAR", [{"text": "...", "accession_no": "..."}])  # doctest: +SKIP
        {'rows': 4220, 'appended': 1}

    SeeAlso:
        - ``buildEdgarPanel`` — 단일 ticker 전체 빌드(부트스트랩/신규 종목).
        - ``existingAccessions`` — append 전 중복 판정.
        - ``gather.original.edgar.collect.listRecentFilings`` — 신규 발견.

    Requires:
        - polars. lxml. 신규 filing full-submission text.

    When:
        - EDGAR panel 일간 증분: 기존 종목에 신규 공시 1+ 건 도착 시.

    How:
        - filingTextToBoard 누적 → 기존 parquet 에서 동일 accession 제거 후 concat → panel write.

    AIContext:
        - offline 자급(network 0). per-ticker 소량 메모리.

    LLM Specifications:
        AntiPatterns:
            - 신규 외 전 history text 를 넘기지 말 것 — 그건 buildEdgarPanel(overwrite) 영역.
            - 동일 accession 중복 우려로 호출부에서 직접 dedup 하지 말 것 — 본 함수가 처리.
        OutputSchema:
            - ``dict[str, int]``.
        Prerequisites:
            - 신규 filing text + (선택)기존 artifact.
        Freshness:
            - 신규 공시 도착 시 append.
        Dataflow:
            - 신규 text → 보드 → 기존 merge(dedup) → write.
        TargetMarkets:
            - US.
    """
    newBoard: list[dict] = []
    for record in filings:
        txt, accession = _recordTextAndAccession(record)
        if not txt:
            continue
        b = filingTextToBoard(txt, ticker=ticker, accession=accession)
        if b:
            newBoard.extend(b)
    if not newBoard:
        return {"rows": 0, "appended": 0}

    _applyContentRawCap(newBoard, ticker.upper())
    accessions = {r["rceptNo"] for r in newBoard}

    mergedBoard = _mergeKeepingSchema(panelPath(ticker), newBoard, PANEL_SCHEMA, accessions)
    mergedBoard = _capContentRawDf(mergedBoard)  # 병합 후 누적 cap(existing+new 합산)
    nRows = _writeDf(mergedBoard, panelPath(ticker))

    if verbose:
        _log.info(
            "edgar panel append %s: +%d filings → %d board rows",
            ticker.upper(),
            len(accessions),
            nRows,
        )
    return {"rows": nRows, "appended": len(accessions)}
