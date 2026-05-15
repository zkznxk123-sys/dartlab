"""finance parquet 전수 스캔 → 미커버 (accountId, accountNm) 후보 산출.

`ENV DARTLAB_MAPPING_LEDGER` 옵트인 누적은 종목 1 개씩 점진 사용 때 효과적
이지만, 이미 보유한 전 종목 parquet 을 한 번에 훑어 미커버 후보를 일괄
추출하는 게 본 스크립트.

Polars lazy scan 으로 finance dir 의 모든 parquet 을 글로빙 → (stockCode,
sjDiv, accountId, accountNm) 컬럼만 select → AccountMapper.map() 적용 후
None 인 행만 collect → 5 신호 평가 → staging parquet 출력.

호출:
    uv run python -X utf8 scripts/audit/mappingScanAllParquet.py \
        --finance-dir data/dart/finance \
        --out data/mapping_candidates.parquet \
        [--mappings src/dartlab/reference/data/accountMappings.json]

본 스크립트는 prod JSON 미수정 — staging parquet 만 생성. 매핑 사전 patch
는 `scripts/dev/mappingPromote.py apply` 의 단독 권한.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from dartlab.core.observability import mapping_signals
from dartlab.providers.dart.finance.mapper import AccountMapper

_DEFAULT_FINANCE_DIR = Path("data") / "dart" / "finance"
_DEFAULT_OUT = Path("data") / "mapping_candidates.parquet"
_DEFAULT_MAPPINGS = Path("src/dartlab/reference/data/accountMappings.json")


def _loadMappings(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Args:
        path: accountMappings.json 경로.

    Returns:
        (standardAccounts, mappings).

    Example:
        >>> sa, mp = _loadMappings(_DEFAULT_MAPPINGS)  # doctest: +SKIP

    Raises:
        FileNotFoundError: 경로 부재.
    """
    if not path.exists():
        raise FileNotFoundError(f"accountMappings.json 부재: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("standardAccounts", {}), data.get("mappings", {})


def scanAllParquet(financeDir: Path, mappingsPath: Path, limit: int | None = None) -> pl.DataFrame:
    """finance parquet 전수 스캔 → 미커버 후보 + 5 신호 평가.

    Args:
        financeDir: finance parquet 디렉토리 (종목코드.parquet 글로빙).
        mappingsPath: accountMappings.json 경로 (읽기 전용).

    Returns:
        15 컬럼 staging DataFrame.

    Example:
        >>> df = scanAllParquet(Path("data/dart/finance"), _DEFAULT_MAPPINGS)  # doctest: +SKIP
        >>> "autoEligible" in df.columns
        True

    Raises:
        FileNotFoundError: financeDir 또는 mappingsPath 부재.
    """
    if not financeDir.exists():
        raise FileNotFoundError(f"financeDir 부재: {financeDir}")
    standardAccounts, mappings = _loadMappings(mappingsPath)
    mapper = AccountMapper.get()
    nowIso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 종목별 분할 처리 — Polars Rust 힙 누수 회피 + 진행률 가시화.
    # accumulator key = (accountId, accountNm), value = {occ, stockCodes set, sjDivs set}
    accumulator: dict[tuple[str, str], dict] = {}
    parquetFiles = sorted(financeDir.glob("*.parquet"))
    if limit is not None:
        parquetFiles = parquetFiles[:limit]
    total = len(parquetFiles)
    for idx, parquetPath in enumerate(parquetFiles, 1):
        try:
            df = pl.read_parquet(
                parquetPath,
                columns=["stock_code", "sj_div", "account_id", "account_nm"],
            )
        except Exception as exc:  # noqa: BLE001 — schema drift 종목 skip
            print(f"  skip {parquetPath.name}: {exc}", file=sys.stderr)
            continue
        if df.height == 0:
            continue
        grouped = (
            df.with_columns(
                pl.col("account_id").cast(pl.String).fill_null(""),
                pl.col("account_nm").cast(pl.String).fill_null(""),
                pl.col("sj_div").cast(pl.String).fill_null(""),
                pl.col("stock_code").cast(pl.String).fill_null(""),
            )
            .filter(pl.col("account_nm") != "")
            .group_by(["account_id", "account_nm", "sj_div"])
            .agg(pl.len().alias("cnt"), pl.col("stock_code").first().alias("stockCode"))
        )
        for row in grouped.iter_rows(named=True):
            accountId = row["account_id"] or ""
            accountNm = row["account_nm"] or ""
            sjDiv = row["sj_div"] or ""
            if mapper.map(accountId, accountNm) is not None:
                continue
            key = (accountId, accountNm)
            agg = accumulator.setdefault(key, {"occ": 0, "stockCodes": set(), "sjDivs": set()})
            agg["occ"] += int(row["cnt"] or 0)
            if row["stockCode"]:
                agg["stockCodes"].add(row["stockCode"])
            if sjDiv:
                agg["sjDivs"].add(sjDiv)
        if idx % 200 == 0 or idx == total:
            print(f"  [{idx}/{total}] 누적 미커버 {len(accumulator)} 그룹", file=sys.stderr)

    records: list[dict] = []
    for (accountId, accountNm), agg in accumulator.items():
        stockCodes = sorted(agg["stockCodes"])
        result = mapping_signals.evaluate(
            accountId=accountId,
            accountNm=accountNm,
            occurrenceCount=agg["occ"],
            stockCodes=stockCodes,
            standardAccounts=standardAccounts,
            mappings=mappings,
        )
        status = "auto_proposed" if result.autoEligible else "human_review"
        records.append(
            {
                "firstSeenAt": nowIso,
                "lastSeenAt": nowIso,
                "accountId": accountId,
                "accountNm": accountNm,
                "occurrenceCount": agg["occ"],
                "stockCodes": stockCodes,
                "sjDivs": sorted(agg["sjDivs"]),
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

    if records:
        df = pl.DataFrame(
            records,
            schema={
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
            },
        )
        return df.sort("occurrenceCount", descending=True)
    return pl.DataFrame(
        schema={
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
    )


def _parseArgs(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--finance-dir", type=Path, default=_DEFAULT_FINANCE_DIR, dest="finance_dir")
    p.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--mappings", type=Path, default=_DEFAULT_MAPPINGS)
    p.add_argument("--limit", type=int, default=None, help="처음 N 종목만 — 디버그용.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: argparse 인자 리스트.

    Returns:
        프로세스 exit code.

    Example:
        >>> main([])  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: financeDir 또는 mappings 경로 부재.
    """
    args = _parseArgs(list(sys.argv[1:] if argv is None else argv))
    df = scanAllParquet(args.finance_dir, args.mappings, limit=args.limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(args.out)
    auto = df.filter(pl.col("autoEligible") == True).height  # noqa: E712
    print(f"[mappingScanAllParquet] 미커버 그룹 {df.height} (autoEligible={auto}) → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
