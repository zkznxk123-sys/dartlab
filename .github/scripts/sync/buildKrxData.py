"""KRX OpenAPI → 연도별 raw parquet 빌드 + (옵션) HF push.

GitHub Actions workflow (`.github/workflows/buildKrxData.yml`) 가 호출.
로컬에서도 ``uv run python -X utf8 .github/scripts/sync/buildKrxData.py ...`` 로 실행 가능.

모드:
    incremental — 매 실행마다 어제~오늘 2일을 재조회 → 현재 연도 parquet upsert
    backfill    — ``--start ~ --end`` 기간 → 연도별 parquet 통합/append

요구사항:
    KRX_API_KEY 환경변수 — 이 스크립트가 read 후 ``fetchKrxRange(..., apiKey=key)`` 명시 전달.
        - 발급: https://openapi.krx.co.kr (회원가입 → API 인증키 신청)
        - GitHub Actions: repository secrets 에 ``KRX_API_KEY`` 등록
        - 로컬: ``.env`` 또는 ``export KRX_API_KEY=...``
    HF_TOKEN 환경변수 — ``--push`` 옵션 사용 시. https://huggingface.co/settings/tokens
        Write 권한 필요.

이 스크립트가 환경변수 read 하는 **유일한 경로** (`engines.gather §9` Mode A).
라이브러리 (`gather/krxApi.py::gatherKrx`) 는 환경변수 자동 read 안 함 — 명시 전달만.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import polars as pl

from dartlab.gather.krx.krxApi import _normalizeDate, fetchKrxRange

_KST = timezone(timedelta(hours=9))
_KRX_READY_KST = time(17, 0)
_COMPANY_PRICE_MIN_LOCAL_YEARS = 2

_COMPANY_PRICE_COLUMNS = {
    "BAS_DD": "date",
    "ISU_CD": "stockCode",
    "ISU_NM": "name",
    "MKT_NM": "market",
    "TDD_OPNPRC": "open",
    "TDD_HGPRC": "high",
    "TDD_LWPRC": "low",
    "TDD_CLSPRC": "close",
    "CMPPREVDD_PRC": "priceChange",
    "FLUC_RT": "fluctuationRate",
    "ACC_TRDVOL": "volume",
    "ACC_TRDVAL": "tradedValue",
    "MKTCAP": "marketCap",
    "LIST_SHRS": "listedShares",
}


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


def _loadExisting(out: Path, year: int) -> pl.DataFrame | None:
    """기존 데이터 로드 — 로컬 우선, 없으면 HF (캐시 miss 시 사고 방지 SSOT)."""
    if out.exists():
        return pl.read_parquet(out)
    # GitHub Actions cache miss / 첫 run / 캐시 eviction 대비 — HF 의 raw-{year} 다운로드
    try:
        from dartlab.gather.bulkData.hfBulk import _loadYear

        df = _loadYear(year)
        if df is not None and not df.is_empty():
            print(f"[krx] {year}: 로컬 캐시 miss → HF 에서 fetch ({df.height} rows) → merge 후 재 push")
            return df
    except Exception as exc:
        print(f"[krx] {year}: HF fallback 실패 ({type(exc).__name__}: {exc}) — 신규 파일로 진행")
    return None


def _appendYearly(df: pl.DataFrame, outDir: Path) -> dict[int, int]:
    """df 를 연도별로 분리해서 raw-{year}.parquet 에 append (중복 제거).

    캐시 miss 시 HF 의 기존 데이터를 fetch-merge 후 push — `upload_folder` 가 무조건
    덮어쓰기라 로컬 1일치만 있는 상태에서 push 하면 HF 의 16MB 가 1일치로 줄어드는
    사고 발생 (2026-04-26 회귀). `_loadExisting` 이 단일 SSOT.
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
            grp = pl.concat([existing, grp], how="diagonal_relaxed").unique(subset=["BAS_DD", "ISU_CD"], keep="last")
        grp = grp.sort(["BAS_DD", "ISU_CD"])
        grp.write_parquet(out, compression="zstd")
        counts[year] = grp.height
        print(f"[krx] {year}: {grp.height} rows → {out}")
    return counts


def _companyPriceFrame(frame: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
    """KRX raw long table 을 랜딩 회사 워크스페이스용 schema 로 정규화한다."""
    schemaNames = frame.collect_schema().names() if isinstance(frame, pl.LazyFrame) else list(frame.schema)
    missing = [col for col in _COMPANY_PRICE_COLUMNS if col not in schemaNames]
    if missing:
        raise RuntimeError(f"KRX raw parquet schema 누락: {missing}")

    projected = (
        frame.select([pl.col(src).alias(dst) for src, dst in _COMPANY_PRICE_COLUMNS.items()])
        .with_columns(
            pl.col("date").cast(pl.Utf8),
            pl.col("stockCode").cast(pl.Utf8).str.replace(r"^A", ""),
            pl.col("name").cast(pl.Utf8),
            pl.col("market").cast(pl.Utf8),
            pl.col("open").cast(pl.Float64, strict=False),
            pl.col("high").cast(pl.Float64, strict=False),
            pl.col("low").cast(pl.Float64, strict=False),
            pl.col("close").cast(pl.Float64, strict=False),
            pl.col("priceChange").cast(pl.Float64, strict=False),
            pl.col("fluctuationRate").cast(pl.Float64, strict=False),
            pl.col("volume").cast(pl.Float64, strict=False),
            pl.col("tradedValue").cast(pl.Float64, strict=False),
            pl.col("marketCap").cast(pl.Float64, strict=False),
            pl.col("listedShares").cast(pl.Float64, strict=False),
        )
        .filter(pl.col("stockCode").str.len_chars() == 6)
        .sort(["stockCode", "date"])
    )
    if isinstance(projected, pl.LazyFrame):
        return projected.collect()
    return projected


def buildCompanyPriceArtifacts(
    outDir: Path,
    *,
    companyDir: Path | None = None,
    minYears: int = _COMPANY_PRICE_MIN_LOCAL_YEARS,
) -> dict[str, int]:
    """연도별 KRX raw parquet 에서 회사별 가격 parquet 을 파생한다.

    랜딩의 단일회사 대시보드는 전종목 연도 파일을 브라우저에서 반복 스캔하지 않는다.
    이 함수가 ``krx/prices/company/{stockCode}.parquet`` 를 만들어 가격 탭의 SSOT 로
    제공한다. 로컬 raw 파일이 너무 적으면 cache miss 로 인한 부분 artifact 업로드를
    피하기 위해 생성을 건너뛴다.
    """
    files = sorted(outDir.glob("raw-*.parquet"))
    if len(files) < minYears:
        print(f"[krx/company] raw parquet {len(files)}년치만 존재 → 부분 artifact 방지로 skip")
        return {}

    target = companyDir or (outDir / "company")
    target.mkdir(parents=True, exist_ok=True)

    frame = pl.scan_parquet([str(path) for path in files])
    rows = _companyPriceFrame(frame)
    counts: dict[str, int] = {}
    for key, group in rows.partition_by("stockCode", as_dict=True).items():
        code = key[0] if isinstance(key, tuple) else key
        if not code:
            continue
        out = target / f"{code}.parquet"
        group.write_parquet(out, compression="zstd")
        counts[str(code)] = group.height

    print(f"[krx/company] {len(counts)}사 price timeline → {target}")
    return counts


def _findLastBasDd(outDir: Path) -> date | None:
    """저장된 raw parquet 들에서 가장 최근 BAS_DD 추출 (로컬 → HF fallback)."""
    files = sorted(outDir.glob("raw-*.parquet"))
    if files:
        df = pl.read_parquet(files[-1], columns=["BAS_DD"])
        if not df.is_empty():
            s = df["BAS_DD"].max()
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    # 로컬 비어있으면 HF 현재 연도 시도 (캐시 miss 대비)
    try:
        from dartlab.gather.bulkData.hfBulk import _loadYear

        df = _loadYear(date.today().year)
        if df is not None and not df.is_empty():
            s = df["BAS_DD"].max()
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except Exception as exc:
        print(f"[krx] HF last-date 조회 실패: {type(exc).__name__}: {exc}")
    return None


def _todayKst() -> date:
    return datetime.now(_KST).date()


def _previousWeekday(d: date) -> date:
    cur = d
    while cur.weekday() >= 5:
        cur -= timedelta(days=1)
    return cur


def _incrementalRange(today: date | None = None) -> tuple[date, date]:
    """운영자 incremental 재조회 범위.

    KRX 일별 API 는 휴장일/미확정일에 빈 응답을 정상적으로 반환할 수 있다.
    자동 수집은 최신일 추정으로 실패시키지 않고, 매번 어제와 오늘을 실제로
    호출한 뒤 응답이 있는 일자만 기존 parquet 에 upsert 한다.
    """
    endD = today or _todayKst()
    return endD - timedelta(days=1), endD


def _latestFetchableDate(today: date | None = None, currentTime: time | None = None) -> date:
    """호환용 최신 조회 대상 — incremental 은 항상 오늘까지 직접 확인한다."""
    _ = currentTime
    return today or _todayKst()


def _requiredLatestDate(
    requestedEnd: date,
    today: date | None = None,
    currentTime: time | None = None,
) -> date | None:
    """자동 incremental 은 빈 응답 일자를 최신 필수값으로 강제하지 않는다."""
    _ = (requestedEnd, today, currentTime)
    return None


def _validateFreshFetch(df: pl.DataFrame, *, startD: date, endD: date, context: str) -> None:
    required = _requiredLatestDate(endD)
    if required is None or required < startD:
        return
    latest = None
    if not df.is_empty() and "BAS_DD" in df.columns:
        s = df["BAS_DD"].max()
        latest = date(int(s[:4]), int(s[4:6]), int(s[6:8])) if s else None
    if latest is None or latest < required:
        raise RuntimeError(
            f"KRX fresh 데이터 누락: context={context}, required>={required}, "
            f"latest={latest}, range={startD}~{endD}. "
            "이 상태를 success 로 처리하면 HF 가 오래된 raw parquet 으로 남습니다."
        )


async def buildIncremental(outDir: Path, apiKey: str) -> dict[int, int]:
    """어제~오늘 2일을 매번 재조회해 기존 parquet 에 upsert 한다.

    이미 저장된 일자도 다시 호출한다. KRX 가 휴장일/미확정일을 빈 응답으로
    반환하면 실패시키지 않고, 응답이 있는 일자만 ``unique(..., keep="last")`` 로
    최신 값으로 교체한다.
    """
    today = _todayKst()
    startD, targetEnd = _incrementalRange(today)
    last = _findLastBasDd(outDir)
    if last is None:
        print(f"[krx] last-date 없음 → 어제~오늘 재조회 ({startD}~{targetEnd}). 전체 backfill 은 --mode backfill")
    else:
        print(f"[krx] 어제~오늘 강제 재조회: last={last}, range={startD}~{targetEnd}")
    s = startD.strftime("%Y-%m-%d")
    e = targetEnd.strftime("%Y-%m-%d")
    print(f"[krx] incremental fetch: {s} ~ {e}")
    df = await fetchKrxRange(s, e, market="ALL", sleepSec=0.5, apiKey=apiKey)
    if df.is_empty():
        print(f"[krx] {s}~{e}: empty (휴장일 / 미확정 / 비거래일 구간)")
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
    parser.add_argument(
        "--company-out",
        help="회사별 주가 parquet 출력 디렉토리 (default: <out>/company)",
    )
    parser.add_argument(
        "--skip-company-artifacts",
        action="store_true",
        help="krx/prices/company/{stockCode}.parquet 파생 생성을 건너뜀",
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

    companyCounts: dict[str, int] = {}
    if counts and not args.skip_company_artifacts:
        companyCounts = buildCompanyPriceArtifacts(
            outDir,
            companyDir=Path(args.company_out) if args.company_out else None,
        )

    if args.push:
        from dartlab.gather.bulkData.hfDeploy import deployKrxToHF

        if counts:
            result = deployKrxToHF(outDir, repoId=args.repo_id)
            print(f"[hf] {result}")
            # T7-2 — sync 단계 data lineage 자동 기록
            try:
                from dartlab.core.dataAudit import recordLineage

                rowCountTotal = sum(counts.values()) if isinstance(counts, dict) else 0
                recordLineage(
                    source="KRX prices",
                    version=args.end or "incremental",
                    rowCount=rowCountTotal,
                    extra={
                        "mode": args.mode,
                        "outDir": str(outDir),
                        "companyArtifacts": len(companyCounts),
                    },
                )
            except ImportError:
                pass  # dartlab 미설치 환경 graceful
        else:
            print("[hf] 변경된 KRX 데이터 없음 — HF push skip")

    return 0 if counts or args.mode == "incremental" else 1


if __name__ == "__main__":
    sys.exit(main())
