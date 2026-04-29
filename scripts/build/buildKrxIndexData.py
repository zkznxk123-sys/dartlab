"""KRX 지수 bulk 수집 스크립트.

Summary
-------
KRX OpenAPI ``idx`` 카테고리에서 KRX/KOSPI/KOSDAQ 시장군 전체 지수를 수집해
연도별 raw parquet 으로 저장하고, 선택적으로 HF dataset 에 업로드한다.

Description
-----------
``gather("krxIndex", ...)`` 의 Mode A 운영자 경로다. 사용자 기본 호출은 이
스크립트가 만든 ``krx/indices/raw-{YYYY}.parquet`` 를 HF에서 읽는다. 종목 가격
수집(``buildKrxData.py``)과 같은 운영 패턴을 따르지만, KRX OpenAPI 권한이
``sto`` 와 분리된 ``idx`` 카테고리라 workflow 도 별도 파일로 둔다.

Modes
-----
``incremental``:
    장마감 데이터 준비 이후에는 마지막 저장일 다음날부터 당일(T-0)까지 수집한다.
    준비시각 전 수동 실행은 직전 평일까지만 보고, 캐시 miss 또는 cron 누락으로
    생긴 gap 을 자동으로 메운다.
``backfill``:
    ``--start`` 와 ``--end`` 사이를 최근 연도부터 과거 연도 순으로 수집한다.

Data Contract
-------------
Output directory:
    ``data/krx/indices`` (``DATA_RELEASES["krxIndices"].dir``)
Output files:
    ``raw-{YYYY}.parquet``
Dedup key:
    ``BAS_DD`` + ``MARKET_GROUP`` + ``IDX_CLSS`` + ``IDX_NM``

Requires
--------
``KRX_API_KEY``:
    KRX OpenAPI 인증키. idx 카테고리 권한 필요.
``HF_TOKEN``:
    ``--push`` 사용 시 필요한 HuggingFace write token.

Examples
--------
``uv run python -X utf8 scripts/build/buildKrxIndexData.py --mode incremental --push``
``uv run python -X utf8 scripts/build/buildKrxIndexData.py --mode backfill --start 2010-01-01 --end 2026-04-28 --push``

Notes
-----
HTTP 403/429/5xx 는 ``fetchKrxIndexRange`` 에서 재시도한다. 재시도 후에도
실패하면 예외를 올려 결측 parquet 이 HF에 push 되는 것을 막는다.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import polars as pl

from dartlab.gather.krxApi import _normalizeDate
from dartlab.gather.krxIndex import fetchKrxIndexRange

_KST = timezone(timedelta(hours=9))
_KRX_READY_KST = time(18, 30)
_MARKETS = ("KRX", "KOSPI", "KOSDAQ")


def _getKey() -> str:
    """운영자 bulk 빌드용 KRX key 를 환경변수에서 읽는다.

    Returns
    -------
    str
        KRX OpenAPI 인증키.

    Raises
    ------
    SystemExit
        ``KRX_API_KEY`` 가 없을 때. 메시지는 idx 권한 신청 경로를 포함한다.
    """
    key = os.environ.get("KRX_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "KRX_API_KEY 환경변수 필수 (KRX idx 운영자 빌드).\n"
            "  - 발급: https://openapi.krx.co.kr (마이페이지 → API 인증키 신청)\n"
            "  - idx 카테고리 권한 별도 신청 필요"
        )
    return key


def _todayKst() -> date:
    return datetime.now(_KST).date()


def _previousWeekday(d: date) -> date:
    cur = d
    while cur.weekday() >= 5:
        cur -= timedelta(days=1)
    return cur


def _latestFetchableDate(today: date | None = None) -> date:
    """자동 수집 최신일.

    KST 20:20 cron 에서는 당일 장마감 지수를 기대한다. 준비시각 전 수동 실행은
    직전 평일까지만 대상으로 잡는다.
    """
    if today is None:
        now = datetime.now(_KST)
        base = now.date()
        if now.time() >= _KRX_READY_KST:
            return _previousWeekday(base)
        return _previousWeekday(base - timedelta(days=1))
    return _previousWeekday(today)


def _requiredLatestDate(requestedEnd: date) -> date:
    now = datetime.now(_KST)
    today = now.date()
    if requestedEnd < today:
        return _previousWeekday(requestedEnd)
    if now.time() >= _KRX_READY_KST:
        return min(_previousWeekday(today), _previousWeekday(requestedEnd))
    return _previousWeekday(min(today - timedelta(days=1), requestedEnd))


def _validateFreshFetch(df: pl.DataFrame, *, startD: date, endD: date, context: str) -> None:
    required = _requiredLatestDate(endD)
    if required < startD:
        return
    latest = None
    if not df.is_empty() and "BAS_DD" in df.columns:
        s = df["BAS_DD"].max()
        latest = date(int(s[:4]), int(s[4:6]), int(s[6:8])) if s else None
    if latest is None or latest < required:
        raise RuntimeError(
            f"KRX index fresh 데이터 누락: context={context}, required>={required}, "
            f"latest={latest}, range={startD}~{endD}. "
            "이 상태를 success 로 처리하면 HF 가 오래된 raw parquet 으로 남습니다."
        )


def _loadExisting(out: Path, year: int) -> pl.DataFrame | None:
    """기존 연도 parquet 을 로컬 우선, HF fallback 순서로 로드한다.

    캐시가 비어 있는 GitHub Actions run 에서 1일치만 push 해 기존 HF 파일을
    축소시키는 사고를 막기 위한 방어다.
    """
    if out.exists():
        return pl.read_parquet(out)
    try:
        from dartlab.gather._hfIndexBulk import _loadYear

        df = _loadYear(year)
        if df is not None and not df.is_empty():
            print(f"[krxIndex] {year}: 로컬 캐시 miss → HF fetch ({df.height} rows)")
            return df
    except Exception as exc:
        print(f"[krxIndex] {year}: HF fallback 실패 ({type(exc).__name__}: {exc})")
    return None


def _appendYearly(df: pl.DataFrame, outDir: Path) -> dict[int, int]:
    """raw idx DataFrame 을 연도별 parquet 에 append 후 중복 제거한다.

    Parameters
    ----------
    df : pl.DataFrame
        KRX/KOSPI/KOSDAQ raw long DataFrame.
    outDir : Path
        ``data/krx/indices`` 출력 디렉토리.

    Returns
    -------
    dict[int, int]
        연도별 저장 후 row 수.
    """
    if df.is_empty():
        return {}
    df2 = df.with_columns(pl.col("BAS_DD").str.slice(0, 4).alias("_year"))
    counts: dict[int, int] = {}
    for partKey, grp in df2.partition_by("_year", as_dict=True).items():
        year = int(partKey[0]) if isinstance(partKey, tuple) else int(partKey)
        out = outDir / f"raw-{year}.parquet"
        grp = grp.drop("_year")
        existing = _loadExisting(out, year)
        if existing is not None and not existing.is_empty():
            grp = pl.concat([existing, grp], how="diagonal_relaxed").unique(
                subset=["BAS_DD", "MARKET_GROUP", "IDX_CLSS", "IDX_NM"],
                keep="last",
            )
        grp = grp.sort(["BAS_DD", "MARKET_GROUP", "IDX_CLSS", "IDX_NM"])
        grp.write_parquet(out, compression="zstd")
        counts[year] = grp.height
        print(f"[krxIndex] {year}: {grp.height} rows → {out}")
    return counts


def _findLastBasDd(outDir: Path) -> date | None:
    """저장된 raw parquet 에서 가장 최근 ``BAS_DD`` 를 찾는다.

    로컬 파일이 없으면 HF 현재 연도 파일을 시도한다. incremental 모드의 gap
    계산 기준이며, None 이면 최신 가능일 하루치만 수집한다.
    """
    files = sorted(outDir.glob("raw-*.parquet"))
    if files:
        df = pl.read_parquet(files[-1], columns=["BAS_DD"])
        if not df.is_empty():
            s = df["BAS_DD"].max()
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    try:
        from dartlab.gather._hfIndexBulk import _loadYear

        df = _loadYear(date.today().year)
        if df is not None and not df.is_empty():
            s = df["BAS_DD"].max()
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except Exception as exc:
        print(f"[krxIndex] HF last-date 조회 실패: {type(exc).__name__}: {exc}")
    return None


async def _fetchAllMarkets(
    start: str,
    end: str,
    apiKey: str,
    *,
    concurrency: int = 1,
    sleepSec: float = 0.1,
) -> pl.DataFrame:
    """KRX/KOSPI/KOSDAQ 시장군 전체를 같은 기간으로 수집한다.

    Returns
    -------
    pl.DataFrame
        세 시장군을 합친 raw long DataFrame. 각 row 는 ``MARKET_GROUP`` 을 가진다.

    Notes
    -----
    기본 동시성은 1이다. KRX idx endpoint 는 빠른 병렬 호출에서 403을 반환할 수
    있어 운영자 backfill 은 보수적으로 순차 처리한다.
    """
    frames: list[pl.DataFrame] = []
    for market in _MARKETS:
        print(f"[krxIndex] fetch {market}: {start} ~ {end}", flush=True)
        df = await fetchKrxIndexRange(
            start,
            end,
            market=market,
            apiKey=apiKey,
            concurrency=concurrency,
            retries=5,
            sleepSec=sleepSec,
        )
        if not df.is_empty():
            frames.append(df)
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


async def buildIncremental(outDir: Path, apiKey: str) -> dict[int, int]:
    """마지막 저장일 다음날부터 최신 fetch 가능 거래일까지 자동 수집한다.

    Returns
    -------
    dict[int, int]
        변경된 연도별 row 수. up-to-date 이면 빈 dict.
    """
    targetEnd = _latestFetchableDate()
    last = _findLastBasDd(outDir)
    if last is None:
        startD = targetEnd
        print(f"[krxIndex] last-date 없음 → 최신 가능일 1일치만 ({startD}). 전체 backfill 은 --mode backfill")
    else:
        startD = last + timedelta(days=1)
        if startD > targetEnd:
            print(f"[krxIndex] up-to-date (last={last}, targetEnd={targetEnd})")
            return {}

    s = startD.strftime("%Y-%m-%d")
    e = targetEnd.strftime("%Y-%m-%d")
    df = await _fetchAllMarkets(s, e, apiKey)
    _validateFreshFetch(df, startD=startD, endD=targetEnd, context="incremental")
    if df.is_empty():
        print(f"[krxIndex] {s}~{e}: empty")
        return {}
    return _appendYearly(df, outDir)


async def buildBackfill(
    outDir: Path,
    start: str,
    end: str,
    apiKey: str,
    *,
    chunkYears: int = 1,
) -> dict[int, int]:
    """기간 backfill 을 최근 연도부터 과거 연도 순으로 수행한다.

    Parameters
    ----------
    outDir : Path
        출력 디렉토리.
    start : str
        시작일.
    end : str
        종료일.
    apiKey : str
        KRX idx 권한이 있는 인증키.
    chunkYears : int
        한 번에 처리할 연도 수. 기본 1년.

    Returns
    -------
    dict[int, int]
        저장된 연도별 row 수.
    """
    startD = datetime.strptime(_normalizeDate(start), "%Y%m%d").date()
    endD = datetime.strptime(_normalizeDate(end), "%Y%m%d").date()
    if startD > endD:
        startD, endD = endD, startD

    counts: dict[int, int] = {}
    cursor = endD
    while cursor >= startD:
        chunkStartYear = max(startD.year, cursor.year - chunkYears + 1)
        chunkStart = max(startD, date(chunkStartYear, 1, 1))
        chunkS = chunkStart.strftime("%Y-%m-%d")
        chunkE = cursor.strftime("%Y-%m-%d")
        df = await _fetchAllMarkets(chunkS, chunkE, apiKey)
        if df.is_empty():
            print(f"[krxIndex] {chunkS} ~ {chunkE}: empty", flush=True)
        else:
            counts.update(_appendYearly(df, outDir))
        cursor = chunkStart - timedelta(days=1)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    parser.add_argument("--start", help="backfill 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", help="backfill 종료일 (YYYY-MM-DD)")
    parser.add_argument(
        "--out",
        default="data/krx/indices",
        help="로컬 출력 디렉토리 (default: data/krx/indices, DATA_RELEASES['krxIndices'].dir)",
    )
    parser.add_argument(
        "--repo-id",
        default="eddmpython/dartlab-data",
        help="HF dataset repo (default: eddmpython/dartlab-data, path: krx/indices)",
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
        from dartlab.gather._hfDeploy import deployKrxIndexToHF

        if counts:
            result = deployKrxIndexToHF(outDir, repoId=args.repo_id)
            print(f"[hf] {result}")
        else:
            print("[hf] 변경된 KRX index 데이터 없음 — HF push skip")

    return 0 if counts or args.mode == "incremental" else 1


if __name__ == "__main__":
    sys.exit(main())
