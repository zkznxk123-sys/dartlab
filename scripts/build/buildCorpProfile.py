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


def _fetchOne(client: DartClient, row: dict, *, retry: int = 2, delay: float = 0.1) -> dict | None:
    """단일 corp_code 의 companyInfo() 호출 → dict 반환. 실패 시 None."""
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
            time.sleep(delay * (attempt + 1))
    return None


def main() -> int:
    """전 corp_code 대상 companyInfo() prefetch + parquet 저장."""
    parser = argparse.ArgumentParser(description="DART corp_profile prefetch 빌드")
    parser.add_argument("--limit", type=int, default=0, help="처리할 최대 종목 수 (0=무제한, 테스트용)")
    parser.add_argument("--workers", type=int, default=8, help="동시 호출 수 (rate limit 주의)")
    parser.add_argument("--stockOnly", action="store_true", help="stock_code 있는 종목만 (상장사)")
    parser.add_argument("--output", type=str, default="", help="출력 path (기본 data/dart/scan/corpProfile.parquet)")
    args = parser.parse_args()

    apiKey = _resolveApiKey()
    client = DartClient(apiKey=apiKey)

    print("[corpProfile] corp_code master 로드 ...")
    master = loadCorpCodes(client)
    print(f"[corpProfile] master rows: {master.height}")

    if args.stockOnly:
        master = master.filter(
            pl.col("stock_code").is_not_null() & (pl.col("stock_code") != "") & (pl.col("stock_code") != " ")
        )
        print(f"[corpProfile] stock_code 있는 종목만: {master.height}")

    if args.limit > 0:
        master = master.head(args.limit)
        print(f"[corpProfile] limit 적용: {master.height}")

    rows = master.to_dicts()
    results: list[dict] = []
    failed = 0
    t0 = time.perf_counter()

    print(f"[corpProfile] companyInfo 병렬 prefetch (workers={args.workers}) ...")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_fetchOne, client, row) for row in rows]
        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result is None:
                failed += 1
            else:
                results.append(result)
            if i % 200 == 0:
                elapsed = time.perf_counter() - t0
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  [{i}/{len(rows)}] {len(results)}ok {failed}fail {rate:.1f}/s")

    elapsed = time.perf_counter() - t0
    print(f"[corpProfile] 완료: {len(results)}ok {failed}fail {elapsed:.0f}초")

    if not results:
        print("[corpProfile] 결과 없음 — 종료")
        return 1

    df = pl.DataFrame(results)

    outPath = Path(args.output) if args.output else Path(_dataDir("scan")) / "corpProfile.parquet"
    outPath.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(outPath), compression="zstd")
    diskKb = outPath.stat().st_size / 1024
    print(f"[corpProfile] saved: {outPath} ({df.height} rows, {diskKb:.0f}KB)")

    # 결산월 분포 요약
    acc_dist = (
        df.filter((pl.col("stockCode") != "") & (pl.col("acc_mt") != ""))
        .group_by("acc_mt")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print("[corpProfile] 상장사 결산월 분포:")
    print(acc_dist)

    return 0


if __name__ == "__main__":
    sys.exit(main())
