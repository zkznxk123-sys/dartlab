"""DuckDB document catalog prototype for search index builds.

The experiment keeps DartLab's existing CSR BM25 runtime and moves only the
large-corpus bookkeeping into DuckDB: staging, text-hash diffing, and export of
new or changed rows to the existing `buildContentSegment()` builder.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

import duckdb
import polars as pl

DEFAULT_UPDATED_AT = "1970-01-01T00:00:00Z"

DOC_SCHEMA: dict[str, pl.DataType] = {
    "doc_key": pl.Utf8,
    "source": pl.Utf8,
    "rcept_no": pl.Utf8,
    "section_order": pl.Int64,
    "corp_code": pl.Utf8,
    "corp_name": pl.Utf8,
    "stock_code": pl.Utf8,
    "rcept_dt": pl.Utf8,
    "report_nm": pl.Utf8,
    "section_title": pl.Utf8,
    "section_content": pl.Utf8,
    "text_hash": pl.Utf8,
    "content_len": pl.Int64,
    "deleted": pl.Boolean,
    "updated_at": pl.Utf8,
}

DOC_COLUMNS = tuple(DOC_SCHEMA)


def connectCatalog(path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Open a DuckDB catalog connection and ensure the prototype schema.

    Args:
        path: DuckDB database path. Use ``":memory:"`` for fast experiments.

    Returns:
        DuckDB connection with catalog tables initialized.

    Raises:
        duckdb.Error: DuckDB connection or DDL failure.

    Example:
        >>> con = connectCatalog()
        >>> catalogSummary(con)["documents"]
        0
    """
    con = duckdb.connect(path)
    ensureSchema(con)
    return con


def ensureSchema(con: duckdb.DuckDBPyConnection) -> None:
    """Create prototype catalog tables if they do not exist.

    Args:
        con: DuckDB connection.

    Returns:
        None.

    Raises:
        duckdb.Error: Schema creation failure.

    Example:
        >>> con = connectCatalog()
        >>> ensureSchema(con)
    """
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_key VARCHAR,
            source VARCHAR,
            rcept_no VARCHAR,
            section_order BIGINT,
            corp_code VARCHAR,
            corp_name VARCHAR,
            stock_code VARCHAR,
            rcept_dt VARCHAR,
            report_nm VARCHAR,
            section_title VARCHAR,
            section_content VARCHAR,
            text_hash VARCHAR,
            content_len BIGINT,
            deleted BOOLEAN,
            updated_at VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS segments (
            segment_id VARCHAR,
            kind VARCHAR,
            schema_version BIGINT,
            tokenizer_version VARCHAR,
            built_at VARCHAR,
            min_date VARCHAR,
            max_date VARCHAR,
            doc_count BIGINT,
            artifact_path VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS segment_docs (
            segment_id VARCHAR,
            doc_key VARCHAR,
            local_doc_id BIGINT,
            text_hash VARCHAR
        )
        """
    )


def stageDocuments(con: duckdb.DuckDBPyConnection, docs: Iterable[Mapping[str, Any]]) -> pl.DataFrame:
    """Normalize incoming documents into a DuckDB staging table.

    Args:
        con: DuckDB connection.
        docs: Records with production-like metadata. Accepts either snake-case
            fields (``rcept_no``) or current panel-style aliases
            (``rceptNo``, ``sectionContent``).

    Returns:
        Normalized Polars DataFrame inserted into temporary ``stagingDocs``.

    Raises:
        duckdb.Error: Staging table creation failure.

    Example:
        >>> con = connectCatalog()
        >>> stageDocuments(con, [{"source": "allFilings", "rcept_no": "1", "section_content": "배당"}]).height
        1
    """
    rows = [_normalizeDocument(row) for row in docs]
    frame = pl.DataFrame(rows, schema=DOC_SCHEMA)
    con.execute("DROP TABLE IF EXISTS stagingDocs")
    con.register("incomingDocs", frame.to_arrow())
    try:
        con.execute(
            """
            CREATE TEMP TABLE stagingDocs AS
            SELECT
                CAST(doc_key AS VARCHAR) AS doc_key,
                CAST(source AS VARCHAR) AS source,
                CAST(rcept_no AS VARCHAR) AS rcept_no,
                CAST(section_order AS BIGINT) AS section_order,
                CAST(corp_code AS VARCHAR) AS corp_code,
                CAST(corp_name AS VARCHAR) AS corp_name,
                CAST(stock_code AS VARCHAR) AS stock_code,
                CAST(rcept_dt AS VARCHAR) AS rcept_dt,
                CAST(report_nm AS VARCHAR) AS report_nm,
                CAST(section_title AS VARCHAR) AS section_title,
                CAST(section_content AS VARCHAR) AS section_content,
                CAST(text_hash AS VARCHAR) AS text_hash,
                CAST(content_len AS BIGINT) AS content_len,
                CAST(deleted AS BOOLEAN) AS deleted,
                CAST(updated_at AS VARCHAR) AS updated_at
            FROM incomingDocs
            """
        )
    finally:
        con.unregister("incomingDocs")
    return frame


def diffStagedDocuments(con: duckdb.DuckDBPyConnection, *, includeUnchanged: bool = False) -> pl.DataFrame:
    """Classify staged rows as new, changed, or unchanged.

    Args:
        con: DuckDB connection with ``stagingDocs`` loaded.
        includeUnchanged: True keeps unchanged rows in the returned frame.

    Returns:
        Polars DataFrame with an extra ``change_type`` column.

    Raises:
        duckdb.Error: Missing staging table or SQL failure.

    Example:
        >>> con = connectCatalog()
        >>> stageDocuments(con, [{"source": "x", "rcept_no": "1", "section_content": "본문"}])
        shape: (1, 15)
        ...
        >>> diffStagedDocuments(con).select("change_type").item()
        'new'
    """
    whereClause = "" if includeUnchanged else "WHERE change_type != 'unchanged'"
    return con.execute(
        f"""
        WITH classified AS (
            SELECT
                s.*,
                CASE
                    WHEN d.doc_key IS NULL THEN 'new'
                    WHEN d.text_hash != s.text_hash THEN 'changed'
                    WHEN d.deleted != s.deleted THEN 'changed'
                    ELSE 'unchanged'
                END AS change_type
            FROM stagingDocs s
            LEFT JOIN documents d ON d.doc_key = s.doc_key
        )
        SELECT * FROM classified
        {whereClause}
        ORDER BY rcept_dt DESC, doc_key ASC
        """
    ).pl()


def commitStagedDocuments(con: duckdb.DuckDBPyConnection) -> int:
    """Upsert staged documents into the persistent catalog.

    Args:
        con: DuckDB connection with ``stagingDocs`` loaded.

    Returns:
        Number of staged rows committed.

    Raises:
        duckdb.Error: Missing staging table or SQL failure.

    Example:
        >>> con = connectCatalog()
        >>> stageDocuments(con, [{"source": "x", "rcept_no": "1", "section_content": "본문"}])
        shape: (1, 15)
        ...
        >>> commitStagedDocuments(con)
        1
    """
    stagedCount = int(con.execute("SELECT count(*) FROM stagingDocs").fetchone()[0])
    con.execute("DELETE FROM documents WHERE doc_key IN (SELECT doc_key FROM stagingDocs)")
    con.execute(
        f"""
        INSERT INTO documents ({", ".join(DOC_COLUMNS)})
        SELECT {", ".join(DOC_COLUMNS)}
        FROM stagingDocs
        """
    )
    return stagedCount


def exportChangedForCsr(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Return staged new/changed rows in the shape expected by buildContentSegment.

    Args:
        con: DuckDB connection with staged documents.

    Returns:
        Polars DataFrame excluding unchanged and deleted rows.

    Raises:
        duckdb.Error: Missing staging table or SQL failure.

    Example:
        >>> con = connectCatalog()
        >>> stageDocuments(con, [{"source": "x", "rcept_no": "1", "section_content": "배당"}])
        shape: (1, 15)
        ...
        >>> exportChangedForCsr(con).height
        1
    """
    changed = diffStagedDocuments(con)
    if changed.is_empty():
        return changed
    return changed.filter(~pl.col("deleted")).select(
        [
            "rcept_no",
            "section_order",
            "corp_code",
            "corp_name",
            "stock_code",
            "rcept_dt",
            "report_nm",
            "section_title",
            "section_content",
            "source",
        ]
    )


def buildChangedSegment(con: duckdb.DuckDBPyConnection) -> tuple[dict, pl.DataFrame, pl.DataFrame]:
    """Build the existing CSR BM25 segment from DuckDB-changed rows.

    Args:
        con: DuckDB connection with staged documents.

    Returns:
        ``(index, meta, docs)`` where ``index`` and ``meta`` come from the
        production ``buildContentSegment`` helper, and ``docs`` is the DuckDB
        export used as input.

    Raises:
        duckdb.Error: Diff/export SQL failure.

    Example:
        >>> con = connectCatalog()
        >>> stageDocuments(con, [{"source": "x", "rcept_no": "1", "section_content": "배당"}])
        shape: (1, 15)
        ...
        >>> idx, meta, docs = buildChangedSegment(con)
        >>> idx["nDocs"], meta.height, docs.height
        (1, 1, 1)
    """
    from dartlab.providers.dart.search.fieldIndex import buildContentSegment

    docs = exportChangedForCsr(con)
    idx, meta = buildContentSegment(docs.to_dicts(), showProgress=False)
    return idx, meta, docs


def catalogSummary(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Return table counts for quick demo output.

    Args:
        con: DuckDB connection.

    Returns:
        Count summary for persistent catalog tables and current staging rows.

    Raises:
        duckdb.Error: SQL failure.

    Example:
        >>> catalogSummary(connectCatalog())["documents"]
        0
    """
    out: dict[str, int] = {}
    for tableName in ("documents", "segments", "segment_docs"):
        out[tableName] = int(con.execute(f"SELECT count(*) FROM {tableName}").fetchone()[0])
    stagingExists = bool(
        con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'stagingDocs'").fetchone()[0]
    )
    out["stagingDocs"] = int(con.execute("SELECT count(*) FROM stagingDocs").fetchone()[0]) if stagingExists else 0
    return out


def _normalizeDocument(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one production-like row into the prototype catalog schema."""
    source = _string(row.get("source") or "unknown")
    rceptNo = _string(row.get("rcept_no") or row.get("rceptNo") or row.get("url") or "")
    sectionOrder = int(row.get("section_order") or row.get("sectionOrder") or 0)
    docKey = _string(row.get("doc_key") or row.get("docKey") or f"{source}:{rceptNo}:{sectionOrder}")
    text = _string(
        row.get("section_content")
        or row.get("sectionContent")
        or row.get("content")
        or row.get("content_raw")
        or row.get("text")
        or ""
    )
    textHash = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return {
        "doc_key": docKey,
        "source": source,
        "rcept_no": rceptNo,
        "section_order": sectionOrder,
        "corp_code": _string(row.get("corp_code") or row.get("corpCode") or ""),
        "corp_name": _string(row.get("corp_name") or row.get("corpName") or ""),
        "stock_code": _string(row.get("stock_code") or row.get("stockCode") or ""),
        "rcept_dt": _string(row.get("rcept_dt") or row.get("rceptDt") or row.get("date") or ""),
        "report_nm": _string(row.get("report_nm") or row.get("reportNm") or row.get("report_type") or ""),
        "section_title": _string(row.get("section_title") or row.get("sectionTitle") or ""),
        "section_content": text,
        "text_hash": textHash,
        "content_len": len(text),
        "deleted": bool(row.get("deleted") or False),
        "updated_at": _string(row.get("updated_at") or row.get("updatedAt") or DEFAULT_UPDATED_AT),
    }


def _string(value: Any) -> str:
    """Convert optional values to stable catalog strings."""
    if value is None:
        return ""
    return str(value)
