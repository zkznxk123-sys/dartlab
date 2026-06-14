"""Small JSON demo for the DuckDB search catalog experiment.

Run:
    uv run python -X utf8 tests/_attempts/searchCatalogDuckdb/demo.py
"""

from __future__ import annotations

import json

from attempt01CatalogDiffTest import nextDocs, seedDocs
from catalogDuckdb import (
    buildChangedSegment,
    catalogSummary,
    commitStagedDocuments,
    connectCatalog,
    diffStagedDocuments,
    stageDocuments,
)


def main() -> None:
    """Print a compact demonstration summary."""
    con = connectCatalog()
    stageDocuments(con, seedDocs())
    firstDiff = diffStagedDocuments(con, includeUnchanged=True)
    commitStagedDocuments(con)

    stageDocuments(con, nextDocs())
    secondDiff = diffStagedDocuments(con, includeUnchanged=True)
    idx, meta, docs = buildChangedSegment(con)

    payload = {
        "firstBatch": _counts(firstDiff),
        "secondBatch": _counts(secondDiff),
        "changedExportRows": docs.height,
        "csrDocs": int(idx["nDocs"]),
        "csrStems": len(idx["stemDict"]),
        "metaRows": meta.height,
        "catalogBeforeSecondCommit": catalogSummary(con),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    con.close()


def _counts(frame) -> dict[str, int]:
    """Count rows by change type."""
    return {row["change_type"]: row["count"] for row in frame.get_column("change_type").value_counts().to_dicts()}


if __name__ == "__main__":
    main()
