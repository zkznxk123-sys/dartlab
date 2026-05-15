"""prod JSON patch CLI — `accountMappings.json` `mappings` 키 단독 권한 갱신.

`scripts/dev/mappingReview.py` 가 status=confirmed 로 결정한 staging 행만
취합하여 atomic write 로 추가. 본 CLI 는 `accountMappings.json` 을 직접
변경하는 유일한 진입점.

서브커맨드:
    dryrun    confirmed 행 → 추가 예정 diff 미리보기 (파일 미수정)
    apply     atomic write + _metadata 갱신 + AccountMapper.release() + lru_cache 무효화
    rollback  --to=<gitsha>  이전 commit 의 accountMappings.json 복원

규약:
    - 추가만 (overwrite reject). 기존 한글명 충돌 시 자세히 stdout 노출, 미적용.
    - `_metadata.lastUpdate` / `_metadata.addedCount` / `_metadata.promoteCommit` 갱신.
    - apply 후 동일 프로세스의 AccountMapper 싱글턴 캐시 무효화.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import polars as pl

_DEFAULT_STAGING = Path("data") / "mapping_candidates.parquet"
_DEFAULT_JSON = Path("src/dartlab/reference/data/accountMappings.json")


def _loadJson(path: Path) -> dict:
    """Args:
        path: JSON 경로.

    Returns:
        파싱된 dict.

    Example:
        >>> _loadJson(_DEFAULT_JSON)  # doctest: +SKIP

    Raises:
        FileNotFoundError: 경로 부재.
    """
    if not path.exists():
        raise FileNotFoundError(f"accountMappings.json 부재: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _readConfirmed(stagingPath: Path) -> dict[str, str]:
    """staging parquet 에서 status=confirmed 의 (accountNm, suggestedSnakeId) 추출.

    Args:
        stagingPath: staging parquet 경로.

    Returns:
        ``{accountNm: snakeId}`` dict.

    Example:
        >>> _readConfirmed(Path("data/x.parquet"))  # doctest: +SKIP

    Raises:
        FileNotFoundError: 경로 부재.
    """
    if not stagingPath.exists():
        raise FileNotFoundError(f"staging parquet 부재: {stagingPath}")
    df = pl.read_parquet(stagingPath)
    df = df.filter(pl.col("status") == "confirmed")
    df = df.filter(pl.col("suggestedSnakeId").is_not_null())
    out: dict[str, str] = {}
    for row in df.iter_rows(named=True):
        nm = row["accountNm"]
        snake = row["suggestedSnakeId"]
        if nm and snake:
            out[nm] = snake
    return out


def _computeDiff(
    existing: dict[str, str], confirmed: dict[str, str]
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """추가 후보와 충돌을 분리.

    Args:
        existing: 현 ``accountMappings.json::mappings``.
        confirmed: staging confirmed dict.

    Returns:
        (additions, conflicts) — additions 는 신규 매핑, conflicts 는
        ``{accountNm: (existingSnakeId, proposedSnakeId)}`` (값이 다르면 충돌).

    Example:
        >>> _computeDiff({}, {"a": "x"})
        ({'a': 'x'}, {})

    Raises:
        없음.
    """
    additions: dict[str, str] = {}
    conflicts: dict[str, tuple[str, str]] = {}
    for nm, snake in confirmed.items():
        if nm in existing:
            if existing[nm] != snake:
                conflicts[nm] = (existing[nm], snake)
            # 같은 값이면 idempotent — additions 에 넣지 않음
            continue
        additions[nm] = snake
    return additions, conflicts


def _writeJsonAtomic(path: Path, data: dict, *, compact: bool = True) -> None:
    """atomic write — tempfile + replace.

    원본이 single-line 컴팩트 JSON (DART accountMappings.json) 인 경우
    diff 폭증 회피 위해 동일 형식 유지. ``compact=False`` 시 indent=2.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if compact:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _resetMapperCache() -> None:
    """AccountMapper 싱글턴 + labels lru_cache 모두 무효화."""
    try:
        from dartlab.core.utils.labels import _loadAccountMappings
        from dartlab.providers.dart.finance.mapper import AccountMapper

        _loadAccountMappings.cache_clear()
        AccountMapper.release()
    except ImportError:  # pragma: no cover - import 실패 시 동일 프로세스 캐시 미해제
        pass


def cmdDryrun(args: argparse.Namespace) -> int:
    """dryrun 서브커맨드 — diff 만 출력, 파일 미수정.

    Args:
        args: argparse Namespace (staging, json).

    Returns:
        exit code 0 (충돌 있어도 0 — dryrun 은 보고만).

    Example:
        >>> cmdDryrun(args)  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: staging / json 경로 부재.
    """
    confirmed = _readConfirmed(args.staging)
    data = _loadJson(args.json)
    existing = data.get("mappings", {})
    additions, conflicts = _computeDiff(existing, confirmed)

    print(f"[mappingPromote dryrun] 추가 예정 {len(additions)} 매핑:")
    for nm, snake in sorted(additions.items()):
        print(f"  + {nm!r} → {snake}")
    if conflicts:
        print(f"\n  ⚠ 충돌 {len(conflicts)} 매핑 (apply 시 reject):")
        for nm, (old, new) in sorted(conflicts.items()):
            print(f"    ! {nm!r}: 기존={old} vs 신규={new}")
    return 0


def cmdApply(args: argparse.Namespace) -> int:
    """apply 서브커맨드 — accountMappings.json patch.

    Args:
        args: argparse Namespace (staging, json, force).

    Returns:
        exit code 0 (성공) / 1 (충돌 발견, force 아님).

    Example:
        >>> cmdApply(args)  # doctest: +SKIP
        0

    Raises:
        FileNotFoundError: staging / json 경로 부재.
    """
    confirmed = _readConfirmed(args.staging)
    data = _loadJson(args.json)
    existing = data.get("mappings", {})
    additions, conflicts = _computeDiff(existing, confirmed)

    if conflicts and not args.force:
        print(f"[mappingPromote apply] 충돌 {len(conflicts)} 매핑 — 적용 중단.")
        for nm, (old, new) in sorted(conflicts.items()):
            print(f"  ! {nm!r}: 기존={old} vs 신규={new}")
        print("  → 운영자가 mappingReview.py 로 alias/reject 결정 후 재시도.")
        return 1
    if not additions:
        print("[mappingPromote apply] 추가할 매핑 없음 (이미 동기화 상태).")
        return 0

    # patch
    merged = dict(existing)
    merged.update(additions)
    data["mappings"] = merged
    meta = data.setdefault("_metadata", {})
    meta["lastUpdate"] = date.today().isoformat()
    meta["addedCount"] = int(meta.get("addedCount", 0)) + len(additions)
    meta["promoteCommit"] = _gitHead() or meta.get("promoteCommit", "")

    _writeJsonAtomic(args.json, data)
    _resetMapperCache()

    print(f"[mappingPromote apply] {len(additions)} 매핑 추가, _metadata 갱신.")
    print(f"  lastUpdate: {meta['lastUpdate']}")
    print(f"  addedCount(누적): {meta['addedCount']}")
    return 0


def cmdRollback(args: argparse.Namespace) -> int:
    """rollback 서브커맨드 — 이전 git commit 의 accountMappings.json 복원.

    Args:
        args: argparse Namespace (to, json).

    Returns:
        exit code 0.

    Example:
        >>> cmdRollback(args)  # doctest: +SKIP
        0

    Raises:
        subprocess.CalledProcessError: git show 실패.
    """
    result = subprocess.run(
        ["git", "show", f"{args.to}:{args.json.as_posix()}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    args.json.write_text(result.stdout, encoding="utf-8")
    _resetMapperCache()
    print(f"[mappingPromote rollback] {args.json} ← {args.to}")
    return 0


def _gitHead() -> str | None:
    """현재 HEAD sha (rollback 추적용). git 없으면 None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _buildParser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--staging", type=Path, default=_DEFAULT_STAGING)
    p.add_argument("--json", type=Path, default=_DEFAULT_JSON)
    sub = p.add_subparsers(dest="cmd", required=True)

    pd_ = sub.add_parser("dryrun")
    pd_.set_defaults(func=cmdDryrun)

    pa = sub.add_parser("apply")
    pa.add_argument(
        "--force",
        action="store_true",
        help="충돌이 있어도 새 매핑 추가 (overwrite 는 여전히 금지).",
    )
    pa.set_defaults(func=cmdApply)

    pr = sub.add_parser("rollback")
    pr.add_argument("--to", required=True)
    pr.set_defaults(func=cmdRollback)

    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: argparse 인자 리스트. None 이면 ``sys.argv[1:]``.

    Returns:
        프로세스 exit code.

    Example:
        >>> main(["dryrun"])  # doctest: +SKIP
        0

    Raises:
        SystemExit: argparse 실패 시.
    """
    args = _buildParser().parse_args(list(sys.argv[1:] if argv is None else argv))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
