"""운영자 review CLI — staging parquet 의 mapping 후보 결정.

`scripts/audit/mappingLedgerCompact.py` 가 만든 평가 parquet 의 status
컬럼을 갱신만 수행. accountMappings.json 미수정 — prod patch 는 별도
`scripts/dev/mappingPromote.py` 의 단독 권한.

서브커맨드:
    list      [--status=...] [--auto-eligible-only] [--min-count=N]
    inspect   <accountNm>
    confirm   <accountNm> --to=<snakeId>
    reject    <accountNm> --reason="..."
    alias     <accountNm> --to=<snakeId>     # ACCOUNT_NAME_SYNONYMS 후보 csv 별도 저장
    defer     <accountNm> --reason="..."
    export-pr [--status=confirmed] --out=<patch.json>

상태 전이:
    new / auto_proposed / human_review  →  confirmed / rejected / alias_only / deferred
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

_DEFAULT_PARQUET = Path("data") / "mapping_candidates.parquet"
_DEFAULT_ALIAS_CSV = Path("data") / "mapping_alias_candidates.csv"


def _readStaging(path: Path) -> pl.DataFrame:
    """Args:
        path: staging parquet 경로.

    Returns:
        Polars DataFrame. 파일 부재 시 빈 schema 반환.

    Example:
        >>> df = _readStaging(_DEFAULT_PARQUET)  # doctest: +SKIP
        >>> isinstance(df, pl.DataFrame)
        True

    Raises:
        FileNotFoundError: 경로 부재.
    """
    if not path.exists():
        raise FileNotFoundError(f"staging parquet 부재: {path}")
    return pl.read_parquet(path)


def _writeStaging(df: pl.DataFrame, path: Path) -> None:
    """parquet atomic write (tempfile + replace).

    Args:
        df: 저장할 DataFrame.
        path: 출력 경로.

    Returns:
        None.

    Example:
        >>> _writeStaging(pl.DataFrame(), Path("/tmp/out.parquet"))  # doctest: +SKIP

    Raises:
        OSError: 쓰기 실패.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.write_parquet(tmp)
    tmp.replace(path)


def _nowIso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _setRow(
    df: pl.DataFrame,
    accountNm: str,
    status: str,
    *,
    suggestedSnakeId: str | None = None,
    operatorNote: str | None = None,
) -> pl.DataFrame:
    """accountNm 매칭 행의 status/suggestedSnakeId/operatorNote/decidedAt 갱신.

    Args:
        df: 입력 DataFrame.
        accountNm: 매칭 키 (1 행 보장 가정 — 같은 accountNm 다중 행은 모두 갱신).
        status: 새 status enum 값.
        suggestedSnakeId: confirm/alias 시 채움. None 이면 기존 값 보존.
        operatorNote: reject/defer 시 reason. None 이면 기존 값 보존.

    Returns:
        새 DataFrame.

    Example:
        >>> df = pl.DataFrame({"accountNm": ["a"], "status": ["new"],
        ...     "suggestedSnakeId": [None], "operatorNote": [None],
        ...     "decidedAt": [None]})
        >>> out = _setRow(df, "a", "confirmed", suggestedSnakeId="x")
        >>> out.row(0, named=True)["status"]
        'confirmed'

    Raises:
        ValueError: accountNm 매칭 행 0 건.
    """
    matched = df.filter(pl.col("accountNm") == accountNm)
    if matched.height == 0:
        raise ValueError(f"accountNm '{accountNm}' staging 부재")

    nowIso = _nowIso()
    updates: dict[str, pl.Expr] = {
        "status": pl.when(pl.col("accountNm") == accountNm).then(pl.lit(status)).otherwise(pl.col("status")),
        "decidedAt": pl.when(pl.col("accountNm") == accountNm).then(pl.lit(nowIso)).otherwise(pl.col("decidedAt")),
    }
    if suggestedSnakeId is not None:
        updates["suggestedSnakeId"] = (
            pl.when(pl.col("accountNm") == accountNm)
            .then(pl.lit(suggestedSnakeId))
            .otherwise(pl.col("suggestedSnakeId"))
        )
    if operatorNote is not None:
        updates["operatorNote"] = (
            pl.when(pl.col("accountNm") == accountNm).then(pl.lit(operatorNote)).otherwise(pl.col("operatorNote"))
        )
    return df.with_columns(**updates)


def cmdList(args: argparse.Namespace) -> int:
    """list 서브커맨드 — status / autoEligible / 빈도 필터로 행 표 출력.

    Args:
        args: argparse Namespace (status, auto_eligible_only, min_count, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdList(args)  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: staging parquet 부재.
    """
    df = _readStaging(args.parquet)
    if args.status:
        df = df.filter(pl.col("status") == args.status)
    if args.auto_eligible_only:
        df = df.filter(pl.col("autoEligible") == True)  # noqa: E712
    if args.min_count is not None:
        df = df.filter(pl.col("occurrenceCount") >= args.min_count)
    cols = [
        "accountNm",
        "accountId",
        "occurrenceCount",
        "corporateDispersion",
        "suggestedSnakeId",
        "confidence",
        "autoEligible",
        "status",
    ]
    avail = [c for c in cols if c in df.columns]
    print(df.select(avail))
    print(f"[mappingReview list] {df.height} 행")
    return 0


def cmdInspect(args: argparse.Namespace) -> int:
    """inspect 서브커맨드 — 단일 accountNm 행의 모든 컬럼 노출.

    Args:
        args: argparse Namespace (accountNm, parquet).

    Returns:
        exit code 0 또는 2 (행 부재).

    Example:
        >>> cmdInspect(args)  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: staging parquet 부재.
    """
    df = _readStaging(args.parquet)
    matched = df.filter(pl.col("accountNm") == args.accountNm)
    if matched.height == 0:
        print(f"[mappingReview inspect] '{args.accountNm}' 부재")
        return 2
    row = matched.row(0, named=True)
    for key, value in row.items():
        if key == "signalBreakdown" and isinstance(value, str) and value:
            try:
                value = json.dumps(json.loads(value), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        print(f"  {key}: {value}")
    return 0


def cmdConfirm(args: argparse.Namespace) -> int:
    """confirm 서브커맨드.

    Args:
        args: argparse Namespace (accountNm, to, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdConfirm(args)  # doctest: +SKIP
        0

    Raises:
        ValueError: staging 에 accountNm 부재.
    """
    df = _readStaging(args.parquet)
    df = _setRow(
        df,
        args.accountNm,
        "confirmed",
        suggestedSnakeId=args.to,
    )
    _writeStaging(df, args.parquet)
    print(f"[mappingReview confirm] {args.accountNm} → {args.to}")
    return 0


def cmdReject(args: argparse.Namespace) -> int:
    """reject 서브커맨드.

    Args:
        args: argparse Namespace (accountNm, reason, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdReject(args)  # doctest: +SKIP
        0

    Raises:
        ValueError: staging 에 accountNm 부재.
    """
    df = _readStaging(args.parquet)
    df = _setRow(df, args.accountNm, "rejected", operatorNote=args.reason)
    _writeStaging(df, args.parquet)
    print(f"[mappingReview reject] {args.accountNm} ({args.reason})")
    return 0


def cmdDefer(args: argparse.Namespace) -> int:
    """defer 서브커맨드 — 다음 사이클 재평가 대기.

    Args:
        args: argparse Namespace (accountNm, reason, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdDefer(args)  # doctest: +SKIP
        0

    Raises:
        ValueError: staging 에 accountNm 부재.
    """
    df = _readStaging(args.parquet)
    df = _setRow(df, args.accountNm, "deferred", operatorNote=args.reason)
    _writeStaging(df, args.parquet)
    print(f"[mappingReview defer] {args.accountNm} ({args.reason})")
    return 0


def cmdAlias(args: argparse.Namespace) -> int:
    """alias 결정 — staging status 만 ``alias_only`` 로, 별도 csv 에 추가.

    ACCOUNT_NAME_SYNONYMS 는 Python in-code dict 이므로 본 CLI 가 직접 patch
    하지 않는다. csv 출력만 — 운영자가 mapper.py 에 별도 PR 로 반영.

    Args:
        args: argparse Namespace (accountNm, to, alias_csv, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdAlias(args)  # doctest: +SKIP
        0

    Raises:
        ValueError: staging 에 accountNm 부재.
    """
    df = _readStaging(args.parquet)
    df = _setRow(df, args.accountNm, "alias_only", suggestedSnakeId=args.to)
    _writeStaging(df, args.parquet)

    args.alias_csv.parent.mkdir(parents=True, exist_ok=True)
    fileExists = args.alias_csv.exists()
    with args.alias_csv.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not fileExists:
            writer.writerow(["accountNm", "suggestedSnakeId", "decidedAt"])
        writer.writerow([args.accountNm, args.to, _nowIso()])
    print(f"[mappingReview alias] {args.accountNm} → {args.to} (csv 추가: {args.alias_csv})")
    return 0


def cmdExportPr(args: argparse.Namespace) -> int:
    """status filter 의 행을 accountMappings.json `mappings` 형식으로 export.

    Args:
        args: argparse Namespace (status, out, parquet).

    Returns:
        exit code 0.

    Example:
        >>> cmdExportPr(args)  # doctest: +SKIP
        0

    Raises:
        OSError: out 파일 쓰기 실패.
    """
    df = _readStaging(args.parquet)
    df = df.filter(pl.col("status") == args.status)
    df = df.filter(pl.col("suggestedSnakeId").is_not_null())
    patch: dict[str, str] = {}
    for row in df.iter_rows(named=True):
        nm = row["accountNm"]
        snake = row["suggestedSnakeId"]
        if nm and snake:
            patch[nm] = snake
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(patch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[mappingReview export-pr] {len(patch)} 매핑 → {args.out}")
    return 0


def _buildParser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--parquet", type=Path, default=_DEFAULT_PARQUET)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl_ = sub.add_parser("list")
    pl_.add_argument("--status", type=str, default=None)
    pl_.add_argument("--auto-eligible-only", action="store_true")
    pl_.add_argument("--min-count", type=int, default=None)
    pl_.set_defaults(func=cmdList)

    pi = sub.add_parser("inspect")
    pi.add_argument("accountNm")
    pi.set_defaults(func=cmdInspect)

    pc = sub.add_parser("confirm")
    pc.add_argument("accountNm")
    pc.add_argument("--to", required=True)
    pc.set_defaults(func=cmdConfirm)

    pr = sub.add_parser("reject")
    pr.add_argument("accountNm")
    pr.add_argument("--reason", required=True)
    pr.set_defaults(func=cmdReject)

    pd = sub.add_parser("defer")
    pd.add_argument("accountNm")
    pd.add_argument("--reason", required=True)
    pd.set_defaults(func=cmdDefer)

    pa = sub.add_parser("alias")
    pa.add_argument("accountNm")
    pa.add_argument("--to", required=True)
    pa.add_argument("--alias-csv", type=Path, default=_DEFAULT_ALIAS_CSV, dest="alias_csv")
    pa.set_defaults(func=cmdAlias)

    pe = sub.add_parser("export-pr")
    pe.add_argument("--status", type=str, default="confirmed")
    pe.add_argument("--out", type=Path, required=True)
    pe.set_defaults(func=cmdExportPr)

    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: argparse 인자 리스트. None 이면 ``sys.argv[1:]``.

    Returns:
        프로세스 exit code.

    Example:
        >>> main(["list"])  # doctest: +SKIP
        0

    Raises:
        SystemExit: argparse 실패 시.
    """
    args = _buildParser().parse_args(list(sys.argv[1:] if argv is None else argv))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
