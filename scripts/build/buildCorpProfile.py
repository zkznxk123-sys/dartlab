"""DART corp_profile prefetch — 결산월(acc_mt) 권위 SSOT 빌드 (P-S11, Phase 3).

OpenDART ``companyInfo()`` 의 ``acc_mt`` (결산월) 를 corp_code 전종목에 대해 prefetch
하여 ``data/dart/scan/corpProfile.parquet`` 으로 저장. ``_fiscalMonthMap()`` 가 1순위로
사용하여 listing (KIND) 누락 + raw rcept_no 추정 한계 (사업보고서 없는 신규 상장사
12 fallback) 를 해소한다.

사용법::

    uv run python -X utf8 scripts/build/buildCorpProfile.py
    uv run python -X utf8 scripts/build/buildCorpProfile.py --limit 100   # 테스트
    uv run python -X utf8 scripts/build/buildCorpProfile.py --workers 5   # 동시 호출 수

환경변수: ``OPEN_DART_KEY`` 또는 ``DART_API_KEY`` 필수.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# repo 루트에서 실행 가능하도록 경로 정리
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import polars as pl  # noqa: E402

from dartlab.core.dataLoader import _dataDir  # noqa: E402
from dartlab.providers.dart.openapi.client import DartClient  # noqa: E402
from dartlab.providers.dart.openapi.corpCode import loadCorpCodes  # noqa: E402
from dartlab.providers.dart.openapi.disclosure import companyInfo  # noqa: E402


def _resolveApiKey() -> str:
    """DART OpenAPI 키 환경변수에서 추출."""
    for key in ("OPEN_DART_KEY", "DART_API_KEY"):
        value = os.environ.get(key)
        if value:
            return value
    raise RuntimeError("OPEN_DART_KEY 또는 DART_API_KEY 환경변수 필요")


def _atomicWriteParquet(combined: dict[str, dict], outPath: Path) -> None:
    """corp_code 매핑 dict → parquet 으로 atomic 저장 (temp → rename).

    중간 저장과 최종 저장 모두 호출. 도중 실패해도 기존 파일 보존 (PolarsError 가
    write 중 났을 때 partial file 이 ``corpProfile.parquet`` 을 덮어쓰지 않게).
    """
    df = pl.DataFrame(list(combined.values()))
    tmp = outPath.with_suffix(outPath.suffix + ".tmp")
    df.write_parquet(str(tmp), compression="zstd")
    tmp.replace(outPath)


def _fetchOne(client: DartClient, row: dict, *, retry: int = 5, delay: float = 0.5) -> dict | None:
    """단일 corp_code 의 companyInfo() 호출 → dict 반환. 실패 시 None.

    DART OpenAPI 가 일시적 "Server disconnected" 다발 시 exponential backoff 로 재시도.
    """
    corpCode = row["corp_code"]
    stockCode = row.get("stock_code", "") or ""
    corpName = row.get("corp_name", "") or ""

    for attempt in range(retry + 1):
        try:
            info = companyInfo(client, corpCode)
            return {
                "corp_code": corpCode,
                "stockCode": stockCode,
                "corp_name": corpName,
                "acc_mt": info.get("acc_mt", ""),
                "induty_code": info.get("induty_code", ""),
                "est_dt": info.get("est_dt", ""),
                "corp_cls": info.get("corp_cls", ""),
            }
        except Exception as e:
            if attempt >= retry:
                print(f"  ⚠ {corpCode} ({corpName}) 실패: {e}", file=sys.stderr)
                return None
            # exponential backoff: 0.5s → 1s → 2s → 4s → 8s
            time.sleep(delay * (2**attempt))
    return None


def buildCorpProfile(
    *,
    stockOnly: bool = True,
    workers: int = 5,
    limit: int = 0,
    output: Path | None = None,
    resume: bool = True,
) -> Path | None:
    """전 corp_code 대상 companyInfo() prefetch + parquet 저장.

    매 prebuild 사이클 (Data Sync 직후) 호출되어 신규 상장 / 상장폐지 / 결산월
    변경을 즉시 반영하는 corp_profile dataset 갱신. 기존 결과가 있으면 누락된
    corp_code 만 incremental 호출 (resume=True) 하여 DART OpenAPI rate limit 으로
    부분 실패한 호출도 누적 완성.

    Parameters
    ----------
    stockOnly : bool
        True 면 ``stock_code`` 있는 종목 (상장사 ~3964) 만. False 면 전종목 (~117K).
    workers : int
        ThreadPool 동시 호출 수. DART OpenAPI rate limit 고려 (기본 5 보수).
    limit : int
        0 = 무제한, > 0 = 첫 N 종목 (테스트용).
    output : Path | None
        결과 parquet 저장 경로. None 이면 ``data/dart/scan/corpProfile.parquet``.
    resume : bool
        True (기본) 면 기존 parquet 의 corp_code 는 skip, missing 만 호출. False
        면 전종목 재호출.

    Returns
    -------
    Path | None
        저장된 parquet 경로. API 키 없거나 결과 0 이면 None.
    """
    try:
        apiKey = _resolveApiKey()
    except RuntimeError as e:
        print(f"[corpProfile] {e} — 스킵")
        return None

    client = DartClient(apiKey=apiKey)

    print("[corpProfile] corp_code master 로드 ...")
    master = loadCorpCodes(client)
    print(f"[corpProfile] master rows: {master.height}")

    if stockOnly:
        master = master.filter(
            pl.col("stock_code").is_not_null() & (pl.col("stock_code") != "") & (pl.col("stock_code") != " ")
        )
        print(f"[corpProfile] stock_code 있는 종목만: {master.height}")

    if limit > 0:
        master = master.head(limit)
        print(f"[corpProfile] limit 적용: {master.height}")

    outPath = output if output else Path(_dataDir("scan")) / "corpProfile.parquet"

    # resume: 기존 결과 있으면 corp_code 매핑 미리 로드, missing 만 호출
    existing: dict[str, dict] = {}
    if resume and outPath.exists():
        try:
            existDf = pl.read_parquet(str(outPath))
            existing = {row["corp_code"]: row for row in existDf.to_dicts()}
            print(f"[corpProfile] resume: 기존 {len(existing)}개 skip, missing 만 호출")
        except (pl.exceptions.PolarsError, OSError) as e:
            print(f"[corpProfile] resume 실패 (재시작): {e}")
            existing = {}

    allRows = master.to_dicts()
    rows = [r for r in allRows if r["corp_code"] not in existing]
    print(f"[corpProfile] 호출 대상: {len(rows)} (skip {len(existing)})")
    results: list[dict] = []
    failed = 0
    t0 = time.perf_counter()

    outPath.parent.mkdir(parents=True, exist_ok=True)

    # 중간 저장 빈도 — 인터럽트/quota 소진 시점까지 누적된 결과 보존.
    FLUSH_EVERY = 500
    combined: dict[str, dict] = dict(existing)

    print(f"[corpProfile] companyInfo 병렬 prefetch (workers={workers}) ...")
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_fetchOne, client, row) for row in rows]
            for i, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                if result is None:
                    failed += 1
                else:
                    results.append(result)
                    combined[result["corp_code"]] = result
                if i % 200 == 0:
                    elapsed = time.perf_counter() - t0
                    rate = i / elapsed if elapsed > 0 else 0
                    print(f"  [{i}/{len(rows)}] {len(results)}ok {failed}fail {rate:.1f}/s")
                if i % FLUSH_EVERY == 0 and combined:
                    _atomicWriteParquet(combined, outPath)
                    print(f"  → 중간 저장: {len(combined)} rows")
    except KeyboardInterrupt:
        print("[corpProfile] 인터럽트 — 누적 결과 저장 후 종료")
        if combined:
            _atomicWriteParquet(combined, outPath)
        raise

    elapsed = time.perf_counter() - t0
    print(f"[corpProfile] 완료: {len(results)}ok {failed}fail {elapsed:.0f}초")

    if not combined:
        print("[corpProfile] 결과 없음 — 종료")
        return None

    _atomicWriteParquet(combined, outPath)
    df = pl.read_parquet(str(outPath))
    diskKb = outPath.stat().st_size / 1024
    print(f"[corpProfile] saved: {outPath} ({df.height} rows, {diskKb:.0f}KB)")

    # 결산월 분포 요약
    accDist = (
        df.filter((pl.col("stockCode") != "") & (pl.col("acc_mt") != ""))
        .group_by("acc_mt")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print("[corpProfile] 상장사 결산월 분포:")
    print(accDist)

    return outPath


def main() -> int:
    """CLI wrapper — argparse + buildCorpProfile()."""
    parser = argparse.ArgumentParser(description="DART corp_profile prefetch 빌드")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 종목 수 (0=무제한, 테스트용)")
    parser.add_argument("--workers", type=int, default=5, help="동시 호출 수 (rate limit, 기본 5)")
    parser.add_argument(
        "--allCorps",
        action="store_true",
        help="비상장 포함 전종목 (~117K, 기본은 상장사 ~3964만)",
    )
    parser.add_argument("--output", type=str, default="", help="출력 path (기본 data/dart/scan/corpProfile.parquet)")
    parser.add_argument("--noResume", action="store_true", help="기존 결과 무시하고 전종목 재호출")
    args = parser.parse_args()

    result = buildCorpProfile(
        stockOnly=not args.allCorps,
        workers=args.workers,
        limit=args.limit,
        output=Path(args.output) if args.output else None,
        resume=not args.noResume,
    )
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
