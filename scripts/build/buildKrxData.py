"""KRX OpenAPI → 연도별 raw parquet 빌드 + (옵션) HF push.

GitHub Actions workflow (`.github/workflows/buildKrxData.yml`) 가 호출.
로컬에서도 ``uv run python -X utf8 scripts/build/buildKrxData.py ...`` 로 실행 가능.

모드:
    incremental — 어제 (T-1) 1일치 → 현재 연도 parquet append
    backfill    — ``--start ~ --end`` 기간 → 연도별 parquet 통합/append

요구사항:
    KRX_API_KEY 환경변수 — 이 스크립트가 read 후 ``fetchKrxRange(..., apiKey=key)`` 명시 전달.
        - 발급: https://openapi.krx.co.kr (회원가입 → API 인증키 신청)
        - GitHub Actions: repository secrets 에 ``KRX_API_KEY`` 등록
        - 로컬: ``.env`` 또는 ``export KRX_API_KEY=...``
    HF_TOKEN 환경변수 — ``--push`` 옵션 사용 시. https://huggingface.co/settings/tokens
        Write 권한 필요.

이 스크립트가 환경변수 read 하는 **유일한 경로** (`ops/gather.md §9` Mode A).
라이브러리 (`gather/krxApi.py::gatherKrx`) 는 환경변수 자동 read 안 함 — 명시 전달만.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import polars as pl

from dartlab.gather.krxApi import _normalizeDate, fetchKrxRange


def _getKey() -> str:
    """환경변수 ``KRX_API_KEY`` read (운영자 cron 빌드 전용 SSOT)."""
    key = os.environ.get("KRX_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "KRX_API_KEY 환경변수 필수 (운영자 cron 빌드).\n"
            "  - 발급: https://openapi.krx.co.kr (회원가입 → API 인증키 신청, 무료)\n"
            "  - GitHub Actions: repository secrets 에 KRX_API_KEY 등록\n"
            "  - 로컬: .env 파일에 KRX_API_KEY=... 또는 셸에서 export KRX_API_KEY=..."
        )
    return key


def _appendYearly(df: pl.DataFrame, outDir: Path) -> dict[int, int]:
    """df 를 연도별로 분리해서 raw-{year}.parquet 에 append (중복 제거)."""
    if df.is_empty():
        return {}
    df2 = df.with_columns(pl.col("BAS_DD").str.slice(0, 4).alias("_year"))
    counts: dict[int, int] = {}
    for partKey, grp in df2.partition_by("_year", as_dict=True).items():
        year = int(partKey[0]) if isinstance(partKey, tuple) else int(partKey)
        out = outDir / f"raw-{year}.parquet"
        grp = grp.drop("_year")
        if out.exists():
            existing = pl.read_parquet(out)
            grp = pl.concat([existing, grp], how="diagonal_relaxed").unique(subset=["BAS_DD", "ISU_CD"], keep="last")
        grp = grp.sort(["BAS_DD", "ISU_CD"])
        grp.write_parquet(out, compression="zstd")
        counts[year] = grp.height
        print(f"[krx] {year}: {grp.height} rows → {out}")
    return counts


async def buildIncremental(outDir: Path, apiKey: str) -> dict[int, int]:
    """어제 1일치 (KOSPI + KOSDAQ) → 현재 연도 parquet append."""
    yest = date.today() - timedelta(days=1)
    s = e = yest.strftime("%Y-%m-%d")
    df = await fetchKrxRange(s, e, market="ALL", sleepSec=0.5, apiKey=apiKey)
    if df.is_empty():
        print(f"[krx] {yest}: empty (휴장일 또는 미확정)")
        return {}
    return _appendYearly(df, outDir)


async def buildBackfill(
    outDir: Path,
    start: str,
    end: str,
    apiKey: str,
    *,
    chunkYears: int = 2,
) -> dict[int, int]:
    """기간 풀 빌드 — chunk 단위 (기본 2년) 역방향 처리.

    메모리 안전: chunk 별로 fetch + 즉시 parquet write (전기간 메모리 누적 회피).
    역방향: 최근 chunk → 과거 chunk 순서 (사용자 명시).
    """
    from datetime import date as _d

    startD = datetime.strptime(_normalizeDate(start), "%Y%m%d").date()
    endD = datetime.strptime(_normalizeDate(end), "%Y%m%d").date()
    if startD > endD:
        startD, endD = endD, startD

    counts: dict[int, int] = {}
    cursor = endD
    while cursor >= startD:
        chunkStartYear = max(startD.year, cursor.year - chunkYears + 1)
        chunkStart = max(startD, _d(chunkStartYear, 1, 1))
        chunkS = chunkStart.strftime("%Y-%m-%d")
        chunkE = cursor.strftime("%Y-%m-%d")
        print(f"[chunk] {chunkS} ~ {chunkE} fetch 시작", flush=True)
        df = await fetchKrxRange(chunkS, chunkE, market="ALL", sleepSec=0.5, apiKey=apiKey)
        if df.is_empty():
            print(f"[chunk] {chunkS} ~ {chunkE}: empty", flush=True)
        else:
            partCounts = _appendYearly(df, outDir)
            counts.update(partCounts)
        # 다음 chunk = 현재 chunk 시작 -1일
        cursor = chunkStart - timedelta(days=1)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["incremental", "backfill"],
        default="incremental",
    )
    parser.add_argument("--start", help="backfill 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", help="backfill 종료일 (YYYY-MM-DD)")
    parser.add_argument(
        "--out",
        default="data/krx/prices",
        help="로컬 출력 디렉토리 (default: data/krx/prices, DATA_RELEASES['krxPrices'].dir)",
    )
    parser.add_argument(
        "--repo-id",
        default="eddmpython/dartlab-data",
        help="HF dataset repo (default: eddmpython/dartlab-data, path: krx/prices)",
    )
    parser.add_argument("--push", action="store_true", help="HF 업로드 실행")
    args = parser.parse_args()

    apiKey = _getKey()
    outDir = Path(args.out)
    outDir.mkdir(parents=True, exist_ok=True)

    if args.mode == "incremental":
        counts = asyncio.run(buildIncremental(outDir, apiKey))
    else:
        if not (args.start and args.end):
            parser.error("backfill 모드는 --start, --end 필수")
        counts = asyncio.run(buildBackfill(outDir, args.start, args.end, apiKey))

    if args.push:
        from dartlab.gather._hfDeploy import deployKrxToHF

        result = deployKrxToHF(outDir, repoId=args.repo_id)
        print(f"[hf] {result}")

    return 0 if counts or args.mode == "incremental" else 1


if __name__ == "__main__":
    sys.exit(main())
