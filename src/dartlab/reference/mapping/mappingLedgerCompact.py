"""ledger ndjson → 5 신호 평가 후 staging parquet.

`DARTLAB_MAPPING_LEDGER` ENV 가 켜진 동안 `_pivotToSeries` 가 흘려보낸
ndjson 을 (accountId, accountNm) 단위로 그룹화하고, 각 그룹에 5 신호
(`mapping_signals.evaluate`) 를 적용한다. 결과 parquet 은 운영자 review CLI
(`src/dartlab/reference/mapping/mappingReview.py`) 의 입력.

호출:
    uv run python -X utf8 src/dartlab/reference/mapping/mappingLedgerCompact.py \
        --raw data/mapping_candidates_raw.ndjson \
        --out data/mapping_candidates.parquet \
        [--mappings src/dartlab/reference/data/accountMappings.json]

prod 동작 0 영향 — accountMappings.json 미수정 (읽기만).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from dartlab.core.observability import mapping_ledger, mapping_signals

_DEFAULT_RAW = Path("data") / "mapping_candidates_raw.ndjson"
_DEFAULT_OUT = Path("data") / "mapping_candidates.parquet"
_DEFAULT_MAPPINGS = Path("src/dartlab/reference/data/accountMappings.json")


def _loadMappings(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """accountMappings.json → (standardAccounts, mappings) 튜플.

    Args:
        path: accountMappings.json 경로.

    Returns:
        (standardAccounts, mappings) — JSON top-level 키 그대로.

    Example:
        >>> sa, mp = _loadMappings(_DEFAULT_MAPPINGS)
        >>> isinstance(sa, dict) and isinstance(mp, dict)
        True

    Raises:
        FileNotFoundError: 경로 부재.
    """
    if not path.exists():
        raise FileNotFoundError(f"accountMappings.json 부재: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("standardAccounts", {}), data.get("mappings", {})


def _groupRows(rows: list[dict]) -> dict[tuple[str, str], dict[str, Any]]:
    """ledger ndjson 행을 (accountId, accountNm) 단위로 집계.

    Args:
        rows: ``mapping_ledger.readAll()`` 결과.

    Returns:
        ``{(accountId, accountNm): aggregate}`` — aggregate 는
        firstSeenAt / lastSeenAt / occurrenceCount / stockCodes / sjDivs.

    Example:
        >>> rows = [{"accountId": "x", "accountNm": "y", "sjDiv": "BS",
        ...          "occurrenceCount": 3, "stockCode": "005930",
        ...          "observedAt": "2026-05-15T00:00:00+00:00"}]
        >>> g = _groupRows(rows)
        >>> g[("x", "y")]["occurrenceCount"]
        3

    Raises:
        없음.
    """
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("accountId", ""), row.get("accountNm", ""))
        agg = grouped.setdefault(
            key,
            {
                "firstSeenAt": row.get("observedAt", ""),
                "lastSeenAt": row.get("observedAt", ""),
                "occurrenceCount": 0,
                "stockCodes": [],
                "sjDivs": [],
            },
        )
        observed = row.get("observedAt", "") or ""
        if observed and observed < agg["firstSeenAt"]:
            agg["firstSeenAt"] = observed
        if observed and observed > agg["lastSeenAt"]:
            agg["lastSeenAt"] = observed
        agg["occurrenceCount"] += int(row.get("occurrenceCount", 0))
        code = row.get("stockCode", "") or ""
        if code:
            agg["stockCodes"].append(code)
        sj = row.get("sjDiv", "") or ""
        if sj:
            agg["sjDivs"].append(sj)
    return grouped


def compact(rawPath: Path, outPath: Path, mappingsPath: Path) -> int:
    """raw ndjson → 평가된 parquet.

    Args:
        rawPath: ledger ndjson 경로.
        outPath: 출력 parquet 경로 (디렉토리는 자동 생성).
        mappingsPath: accountMappings.json 경로 (읽기 전용).

    Returns:
        평가된 그룹 수 (parquet 행 수).

    Example:
        >>> n = compact(Path("data/raw.ndjson"), Path("data/out.parquet"),
        ...             _DEFAULT_MAPPINGS)  # doctest: +SKIP
        >>> isinstance(n, int)
        True

    Raises:
        FileNotFoundError: accountMappings.json 부재.
    """
    standardAccounts, mappings = _loadMappings(mappingsPath)
    rows = mapping_ledger.readAll(rawPath)
    grouped = _groupRows(rows)

    nowIso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict] = []
    for (accountId, accountNm), agg in grouped.items():
        result = mapping_signals.evaluate(
            accountId=accountId,
            accountNm=accountNm,
            occurrenceCount=int(agg["occurrenceCount"]),
            stockCodes=list(agg["stockCodes"]),
            standardAccounts=standardAccounts,
            mappings=mappings,
        )
        status = "auto_proposed" if result.autoEligible else "human_review"
        records.append(
            {
                "firstSeenAt": agg["firstSeenAt"],
                "lastSeenAt": agg["lastSeenAt"] or nowIso,
                "accountId": accountId,
                "accountNm": accountNm,
                "occurrenceCount": int(agg["occurrenceCount"]),
                "stockCodes": sorted(set(agg["stockCodes"])),
                "sjDivs": sorted(set(agg["sjDivs"])),
                "corporateDispersion": result.corporateDispersion,
                "suggestedSnakeId": result.suggestedSnakeId,
                "confidence": float(result.confidence),
                "signalBreakdown": json.dumps(result.breakdown(), ensure_ascii=False),
                "autoEligible": bool(result.autoEligible),
                "status": status,
                "operatorNote": None,
                "decidedAt": None,
            }
        )

    schema = {
        "firstSeenAt": pl.String,
        "lastSeenAt": pl.String,
        "accountId": pl.String,
        "accountNm": pl.String,
        "occurrenceCount": pl.Int64,
        "stockCodes": pl.List(pl.String),
        "sjDivs": pl.List(pl.String),
        "corporateDispersion": pl.Int64,
        "suggestedSnakeId": pl.String,
        "confidence": pl.Float64,
        "signalBreakdown": pl.String,
        "autoEligible": pl.Boolean,
        "status": pl.String,
        "operatorNote": pl.String,
        "decidedAt": pl.String,
    }
    df = pl.DataFrame(records, schema=schema)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(outPath)
    return df.height


def _parseArgs(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--raw", type=Path, default=_DEFAULT_RAW)
    p.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--mappings", type=Path, default=_DEFAULT_MAPPINGS)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: argparse 인자 리스트. None 이면 ``sys.argv[1:]``.

    Returns:
        프로세스 exit code (성공 시 0).

    Example:
        >>> main(["--raw", "data/raw.ndjson", "--out", "data/out.parquet"])  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: ``--mappings`` 경로 부재 시.
    """
    args = _parseArgs(list(sys.argv[1:] if argv is None else argv))
    n = compact(args.raw, args.out, args.mappings)
    print(f"[mappingLedgerCompact] {n} 그룹 평가 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
