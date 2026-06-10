"""공공데이터포털(공공누리/KOGL, 비상업+출처표시 재배포 가능) 주가 → 회사별 parquet 빌드 + HF push.

`gather/gov` 를 source 로 회사별 parquet (`gov/prices/company/{code}.parquet`) 을 매일
덮어쓰기(merge, 일자별 파일 X) — 차트가 50KB 1파일만 읽으면 된다.

모드:
    --stock CODE   종목 하나 전체이력 → 기존 parquet 과 merge(이력 보존) → 덮어쓰기.
                   (프론트 /__gov 미들웨어가 캐시 미스 시 백그라운드 spawn)
    --migrate      HF 보관 raw-{year} → 회사별 parquet 파생(2010~ 과거 이력 포함).
    --daily        어제 basDt 전종목(1콜) → 회사별 merge. (cron 증분)

키: DATA_GO_KR_KEY(디코딩) + HF_TOKEN. 환경변수 우선, 없으면 repo 루트 .env 직독
(미들웨어 spawn 대비).
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

import polars as pl

# raw 컬럼 → 회사 표준 schema (gov normalizeGovFrame 출력과 동일 컬럼).
_RAW_TO_COMPANY = {
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
_REPO = "eddmpython/dartlab-data"
_HF_BASE = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main"
_NUM = (
    "open",
    "high",
    "low",
    "close",
    "priceChange",
    "fluctuationRate",
    "volume",
    "tradedValue",
    "marketCap",
    "listedShares",
)


def _env(name: str) -> str:
    """환경변수 우선, 없으면 repo 루트 .env 직독."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    envPath = Path(__file__).resolve().parents[3] / ".env"
    if envPath.exists():
        m = dict(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", envPath.read_text(encoding="utf-8"), re.M))
        return m.get(name, "").strip().strip('"').strip("'")
    return ""


def _readHfParquet(pathInRepo: str) -> pl.DataFrame | None:
    """HF 의 기존 parquet 읽기 (없으면 None)."""
    try:
        return pl.read_parquet(f"{_HF_BASE}/{pathInRepo}")
    except Exception:
        return None


def _uploadParquet(df: pl.DataFrame, pathInRepo: str, hfToken: str, msg: str) -> None:
    from huggingface_hub import HfApi

    buf = io.BytesIO()
    df.write_parquet(buf, compression="zstd")
    buf.seek(0)
    HfApi(token=hfToken).upload_file(
        path_or_fileobj=buf, path_in_repo=pathInRepo, repo_id=_REPO, repo_type="dataset", commit_message=msg
    )


def _mergeDedup(existing: pl.DataFrame | None, fresh: pl.DataFrame) -> pl.DataFrame:
    """기존 + 신규 → date 기준 dedup(신규 우선) + 정렬. 이력 보존(덮어쓰기여도 과거 안 잃음)."""
    if existing is not None and not existing.is_empty():
        cols = [c for c in fresh.columns if c in existing.columns]
        fresh = pl.concat([existing.select(cols), fresh.select(cols)], how="diagonal_relaxed").unique(
            subset=["date"], keep="last"
        )
    return fresh.sort("date")


def produceStock(code: str, *, apiKey: str, hfToken: str, merge: bool = True) -> int:
    """종목 하나 gov 전체이력 → 회사별 parquet (기존과 merge) → HF 업로드. 반환: 행수."""
    from dartlab.gather.gov.govApi import fetchGovStock, normalizeGovFrame

    fresh = normalizeGovFrame(fetchGovStock(code, apiKey=apiKey))
    if fresh.is_empty():
        print(f"[gov/stock] {code}: gov 데이터 없음")
        return 0
    existing = _readHfParquet(f"gov/prices/company/{code}.parquet") if merge else None
    out = _mergeDedup(existing, fresh)
    _uploadParquet(out, f"gov/prices/company/{code}.parquet", hfToken, f"추가: gov 회사별 주가 {code} ({out.height}행)")
    print(
        f"[gov/stock] {code}: {out.height}행 ({out['date'].min()}~{out['date'].max()}) → gov/prices/company/{code}.parquet"
    )
    return out.height


def _rawUrls() -> list[str]:
    from datetime import date

    return [f"{_HF_BASE}/gov/prices/raw-{y}.parquet" for y in range(2010, date.today().year + 1)]


def migrate(*, hfToken: str, limit: int | None = None) -> int:
    """HF 보관 raw(전종목) → 회사별 gov/prices/company/{code}.parquet 파생(2010~). 반환: 종목수."""
    frames = []
    for url in _rawUrls():
        try:
            frames.append(pl.read_parquet(url))
        except Exception:
            continue
    if not frames:
        print("[gov/migrate] raw 없음 — 중단")
        return 0
    raw = pl.concat(frames, how="diagonal_relaxed")
    present = [k for k in _RAW_TO_COMPANY if k in raw.columns]
    std = (
        raw.select([pl.col(k).alias(_RAW_TO_COMPANY[k]) for k in present])
        .with_columns(
            pl.col("date").cast(pl.Utf8),
            pl.col("stockCode").cast(pl.Utf8).str.replace(r"^A", ""),
            *[pl.col(c).cast(pl.Float64, strict=False) for c in _NUM if c in [_RAW_TO_COMPANY[k] for k in present]],
        )
        .filter(pl.col("stockCode").str.len_chars() == 6)
        .sort(["stockCode", "date"])
    )
    from huggingface_hub import HfApi

    api = HfApi(token=hfToken)
    groups = list(std.partition_by("stockCode", as_dict=True).items())
    if limit:
        groups = groups[:limit]
    n = 0
    for key, grp in groups:
        code = key[0] if isinstance(key, tuple) else key
        if not code:
            continue
        existing = _readHfParquet(f"gov/prices/company/{code}.parquet")
        out = _mergeDedup(existing, grp)
        buf = io.BytesIO()
        out.write_parquet(buf, compression="zstd")
        buf.seek(0)
        api.upload_file(
            path_or_fileobj=buf,
            path_in_repo=f"gov/prices/company/{code}.parquet",
            repo_id=_REPO,
            repo_type="dataset",
            commit_message=f"추가: gov 회사별 주가 {code}",
        )
        n += 1
        if n % 100 == 0:
            print(f"[gov/migrate] {n}/{len(groups)} 업로드…")
    print(f"[gov/migrate] {n}사 → gov/prices/")
    return n


def daily(*, apiKey: str, hfToken: str, basDt: str | None = None) -> int:
    """어제(또는 basDt) 전종목 1콜 → 종목별 merge 덮어쓰기. 반환: 갱신 종목수."""
    from datetime import date, timedelta

    from dartlab.gather.gov.govApi import GOV_TO_STD, fetchGovBydd

    day = (basDt or (date.today() - timedelta(days=1)).strftime("%Y%m%d")).replace("-", "")
    raw = fetchGovBydd(day, apiKey=apiKey)
    if raw.is_empty():
        print(f"[gov/daily] {day}: 데이터 없음(휴장/미확정)")
        return 0
    rename = {k: v for k, v in GOV_TO_STD.items() if k in raw.columns}
    std = raw.rename(rename).with_columns(
        pl.col("date").cast(pl.Utf8),
        pl.col("stockCode").cast(pl.Utf8),
        *[pl.col(c).cast(pl.Float64, strict=False) for c in _NUM if c in [GOV_TO_STD.get(k) for k in raw.columns]],
    )
    keep = [v for v in GOV_TO_STD.values() if v in std.columns]
    std = std.select(keep).filter(pl.col("stockCode").str.len_chars() == 6)
    from huggingface_hub import HfApi

    api = HfApi(token=hfToken)
    n = 0
    for key, grp in std.partition_by("stockCode", as_dict=True).items():
        code = key[0] if isinstance(key, tuple) else key
        existing = _readHfParquet(f"gov/prices/company/{code}.parquet")
        out = _mergeDedup(existing, grp)
        buf = io.BytesIO()
        out.write_parquet(buf, compression="zstd")
        buf.seek(0)
        api.upload_file(
            path_or_fileobj=buf,
            path_in_repo=f"gov/prices/company/{code}.parquet",
            repo_id=_REPO,
            repo_type="dataset",
            commit_message=f"갱신: gov 회사별 주가 {code} ({day})",
        )
        n += 1
    print(f"[gov/daily] {day}: {n}사 갱신")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="공공데이터포털 주가 → 회사별 parquet 빌드")
    ap.add_argument("--stock", help="종목 하나 gov 전체이력 merge 덮어쓰기")
    ap.add_argument("--migrate", action="store_true", help="raw → 회사별 parquet 파생(2010~)")
    ap.add_argument("--daily", action="store_true", help="어제 전종목 1콜 증분 merge")
    ap.add_argument("--basDt", help="--daily 기준일자 YYYYMMDD (기본 어제)")
    ap.add_argument("--limit", type=int, help="--migrate 종목수 상한(테스트)")
    args = ap.parse_args()

    hfToken = _env("HF_TOKEN")
    if not hfToken:
        print("HF_TOKEN 필수")
        return 1
    if args.stock:
        apiKey = _env("DATA_GO_KR_KEY")
        if not apiKey:
            print("DATA_GO_KR_KEY 필수")
            return 1
        produceStock(args.stock.strip(), apiKey=apiKey, hfToken=hfToken)
        return 0
    if args.migrate:
        migrate(hfToken=hfToken, limit=args.limit)
        return 0
    if args.daily:
        apiKey = _env("DATA_GO_KR_KEY")
        if not apiKey:
            print("DATA_GO_KR_KEY 필수")
            return 1
        daily(apiKey=apiKey, hfToken=hfToken, basDt=args.basDt)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
