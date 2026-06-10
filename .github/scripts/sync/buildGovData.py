"""공공데이터포털(공공누리/KOGL, 비상업+출처표시 재배포 가능) 주가·지수 HF 캐시 빌드.

HF = 캐시. 미리 전부 수집(bulk)하지 않는다. 두 갈래:

1. **date/ (전종목·전지수 일별)** — 엔진(scan/quant/benchmark)이 전시장 횡단을 쓰므로
   매일 어제 1콜로 `date/{year}` 1파일만 upsert (운영자 cron).
       gov/prices/date/{year}.parquet     전종목 횡단(KRX raw schema)
       gov/indices/date/{year}.parquet    전지수 횡단(KRX 지수 schema)

2. **company/{code}·index/{key} (엔티티별)** — 프론트가 종목/지수 하나를 **온디맨드**로
   호출할 때만 채운다. HF 캐시 hit 면 그대로, 미스면 라이브 호출→그리고→HF 저장
   (draw-first-save-later). 미리 수집 안 함.
       gov/prices/company/{code}.parquet  종목 1개 호출 캐시 (--stock, gov 라이브)
       gov/indices/index/{key}.parquet    지수 1개 호출 캐시 (--index, date/ 추출)

모드:
    --daily         어제 전종목 1콜 → date/{year} upsert (cron).
    --daily-index   어제 전지수 1콜 → date/{year} upsert (cron).
    --stock CODE    종목 하나 → company/{code} (프론트 온디맨드 캐시 채움).
    --index "M|NM"  지수 하나(시장군|지수명) → index/{key} (프론트 온디맨드 캐시 채움).

키: DATA_GO_KR_KEY(디코딩) + HF_TOKEN. 환경변수 우선, 없으면 repo 루트 .env 직독.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import polars as pl

_REPO = "eddmpython/dartlab-data"
_HF_BASE = "https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main"
_NOW_YEAR = date.today().year


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


def _hfRead(pathInRepo: str) -> pl.DataFrame | None:
    """HF parquet 읽기 (없으면 None) — cold-cache 시 기존 이력 seed(축소 사고 방지)."""
    try:
        return pl.read_parquet(f"{_HF_BASE}/{pathInRepo}")
    except Exception:
        return None


def _deployFolder(localRoot: Path, pathInRepo: str, hfToken: str, msg: str) -> int:
    """로컬 폴더(서브디렉토리 포함)를 HF 에 폴더 단위 1커밋 업로드. 반환: parquet 수."""
    files = list(localRoot.rglob("*.parquet"))
    if not files:
        print(f"[gov/deploy] 업로드 대상 0건: {localRoot}")
        return 0
    from huggingface_hub import HfApi, create_repo

    create_repo(_REPO, token=hfToken, repo_type="dataset", exist_ok=True)
    HfApi(token=hfToken).upload_folder(
        folder_path=str(localRoot),
        path_in_repo=pathInRepo,
        repo_id=_REPO,
        repo_type="dataset",
        commit_message=msg,
    )
    print(f"[gov/deploy] {len(files)} files → {pathInRepo}")
    return len(files)


def _uploadFile(df: pl.DataFrame, pathInRepo: str, hfToken: str, msg: str) -> None:
    """단일 parquet → HF 업로드 (온디맨드 캐시 채움용)."""
    from huggingface_hub import HfApi

    buf = io.BytesIO()
    df.write_parquet(buf, compression="zstd")
    buf.seek(0)
    HfApi(token=hfToken).upload_file(
        path_or_fileobj=buf, path_in_repo=pathInRepo, repo_id=_REPO, repo_type="dataset", commit_message=msg
    )


# ─────────────────────────── 주가 (prices) ───────────────────────────


def _appendYearlyRaw(df: pl.DataFrame, dateDir: Path) -> dict[int, int]:
    """KRX-raw 전종목 df 를 연도별 date/{year}.parquet 에 upsert (BAS_DD+ISU_CD dedup).

    로컬 cold-cache 시 HF 기존 연도 파일을 seed 후 merge — 1일치로 전년 축소 방지.
    """
    if df.is_empty():
        return {}
    dateDir.mkdir(parents=True, exist_ok=True)
    out: dict[int, int] = {}
    df2 = df.with_columns(pl.col("BAS_DD").str.slice(0, 4).alias("_year"))
    for partKey, grp in df2.partition_by("_year", as_dict=True).items():
        year = int(partKey[0]) if isinstance(partKey, tuple) else int(partKey)
        grp = grp.drop("_year")
        path = dateDir / f"{year}.parquet"
        existing = pl.read_parquet(path) if path.exists() else _hfRead(f"gov/prices/date/{year}.parquet")
        if existing is not None and not existing.is_empty():
            grp = pl.concat([existing, grp], how="diagonal_relaxed").unique(subset=["BAS_DD", "ISU_CD"], keep="last")
        grp = grp.sort(["BAS_DD", "ISU_CD"])
        grp.write_parquet(path, compression="zstd")
        out[year] = grp.height
        print(f"[gov/price] {year}: {grp.height}행 → {path}")
    return out


def daily(*, apiKey: str, hfToken: str, basDt: str | None = None) -> int:
    """어제(또는 basDt) 전종목 1콜 → date/{year} 1파일만 upsert → HF push (cron). 반환: 행수.

    회사별 company/{code} 는 여기서 안 받는다 — 프론트가 종목 하나를 `--stock` 온디맨드로
    채운다(HF=캐시). date/ 는 엔진 전시장 스캔용.
    """
    from dartlab.gather.gov.govApi import fetchGovBydd, normalizeGovToKrxRaw

    day = (basDt or (date.today() - timedelta(days=1)).strftime("%Y%m%d")).replace("-", "")
    raw = normalizeGovToKrxRaw(fetchGovBydd(day, apiKey=apiKey))
    if raw.is_empty():
        print(f"[gov/daily] {day}: 데이터 없음(휴장/미확정)")
        return 0
    dateDir = Path("data/gov/prices/date")
    counts = _appendYearlyRaw(raw, dateDir)
    _deployFolder(dateDir, "gov/prices/date", hfToken, f"갱신: 주가 일별 {day}")
    total = sum(counts.values())
    print(f"[gov/daily] {day}: date {len(counts)}개 연도, {total}행")
    return total


def produceStock(code: str, *, apiKey: str, hfToken: str, merge: bool = True) -> int:
    """종목 하나 gov 전체이력 → company/{code} merge → HF 단일 업로드(프론트 온디맨드). 반환: 행수."""
    from dartlab.gather.gov.govApi import fetchGovStock, normalizeGovFrame

    fresh = normalizeGovFrame(fetchGovStock(code, apiKey=apiKey))
    if fresh.is_empty():
        print(f"[gov/stock] {code}: gov 데이터 없음")
        return 0
    existing = _hfRead(f"gov/prices/company/{code}.parquet") if merge else None
    if existing is not None and not existing.is_empty():
        cols = [c for c in fresh.columns if c in existing.columns]
        fresh = pl.concat([existing.select(cols), fresh.select(cols)], how="diagonal_relaxed").unique(
            subset=["date"], keep="last"
        )
    out = fresh.sort("date")
    _uploadFile(out, f"gov/prices/company/{code}.parquet", hfToken, f"갱신: 회사별 주가 {code} ({out.height}행)")
    print(f"[gov/stock] {code}: {out.height}행 ({out['date'].min()}~{out['date'].max()})")
    return out.height


# ─────────────────────────── 지수 (indices) ───────────────────────────

_RESERVED = '/\\:*?"<>|'


def indexKey(market: str, idxNm: str) -> str:
    """(market, idxNm) → 파일시스템 안전 키. '/' 등 9개 예약문자+공백만 '_' 치환(한글 유지)."""
    s = unicodedata.normalize("NFC", str(idxNm)).strip()
    for ch in _RESERVED:
        s = s.replace(ch, "_")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return f"{market}-{s}"


def _appendYearlyIndex(df: pl.DataFrame, dateDir: Path) -> dict[int, int]:
    """KRX-지수 df 를 연도별 date/{year}.parquet 에 upsert (BAS_DD+MARKET_GROUP+IDX_CLSS+IDX_NM dedup)."""
    if df.is_empty():
        return {}
    dateDir.mkdir(parents=True, exist_ok=True)
    keys = ["BAS_DD", "MARKET_GROUP", "IDX_CLSS", "IDX_NM"]
    out: dict[int, int] = {}
    df2 = df.with_columns(pl.col("BAS_DD").str.slice(0, 4).alias("_year"))
    for partKey, grp in df2.partition_by("_year", as_dict=True).items():
        year = int(partKey[0]) if isinstance(partKey, tuple) else int(partKey)
        grp = grp.drop("_year")
        path = dateDir / f"{year}.parquet"
        existing = pl.read_parquet(path) if path.exists() else _hfRead(f"gov/indices/date/{year}.parquet")
        if existing is not None and not existing.is_empty():
            grp = pl.concat([existing, grp], how="diagonal_relaxed").unique(subset=keys, keep="last")
        grp = grp.sort(keys)
        grp.write_parquet(path, compression="zstd")
        out[year] = grp.height
        print(f"[gov/index] {year}: {grp.height}행 → {path}")
    return out


def dailyIndex(*, apiKey: str, hfToken: str, basDt: str | None = None) -> int:
    """어제(또는 basDt) 전지수 1콜 → date/{year} 1파일만 upsert → HF push (cron). 반환: 행수.

    지수별 index/{key} 는 여기서 안 받는다 — 프론트가 지수 하나를 `--index` 온디맨드로 채운다.
    """
    from dartlab.gather.gov.govApi import fetchGovIndex, normalizeGovIndexFrame

    day = (basDt or (date.today() - timedelta(days=1)).strftime("%Y%m%d")).replace("-", "")
    norm = normalizeGovIndexFrame(fetchGovIndex(day, apiKey=apiKey))
    if norm.is_empty():
        print(f"[gov/daily-index] {day}: 데이터 없음(휴장/미확정)")
        return 0
    dateDir = Path("data/gov/indices/date")
    counts = _appendYearlyIndex(norm, dateDir)
    _deployFolder(dateDir, "gov/indices/date", hfToken, f"갱신: 지수 일별 {day}")
    total = sum(counts.values())
    print(f"[gov/daily-index] {day}: date {len(counts)}개 연도, {total}행")
    return total


def produceIndex(market: str, idxNm: str, *, hfToken: str) -> int:
    """지수 하나 → date/ 전체에서 추출 → index/{key} 단일 업로드(프론트 온디맨드). 반환: 행수.

    지수는 종목별 likeSrtnCd 같은 단일-엔티티 API 가 없어, 전지수를 담은 date/ 에서 뽑는다.
    """
    frames = []
    for y in range(2010, _NOW_YEAR + 1):
        df = _hfRead(f"gov/indices/date/{y}.parquet")
        if df is not None and not df.is_empty():
            frames.append(df.filter((pl.col("MARKET_GROUP") == market) & (pl.col("IDX_NM") == idxNm)))
    if not frames:
        print(f"[gov/index1] {market}|{idxNm}: date 없음")
        return 0
    out = pl.concat(frames, how="diagonal_relaxed").unique(subset=["BAS_DD"], keep="last").sort("BAS_DD")
    if out.is_empty():
        print(f"[gov/index1] {market}|{idxNm}: 매칭 행 없음")
        return 0
    key = indexKey(market, idxNm)
    _uploadFile(out, f"gov/indices/index/{key}.parquet", hfToken, f"갱신: 지수별 {key} ({out.height}행)")
    print(f"[gov/index1] {key}: {out.height}행")
    return out.height


def main() -> int:
    ap = argparse.ArgumentParser(description="공공데이터포털 주가·지수 HF 캐시 빌드 (date daily + 엔티티 온디맨드)")
    ap.add_argument("--daily", action="store_true", help="어제 전종목 1콜 → date/{year} (cron)")
    ap.add_argument(
        "--daily-index", dest="dailyIndex", action="store_true", help="어제 전지수 1콜 → date/{year} (cron)"
    )
    ap.add_argument("--stock", help="종목 하나 → company/{code} 온디맨드 캐시")
    ap.add_argument("--index", dest="indexSpec", help='지수 하나 "시장군|지수명" → index/{key} 온디맨드 캐시')
    ap.add_argument("--basDt", help="--daily/--daily-index 기준일자 YYYYMMDD (기본 어제)")
    args = ap.parse_args()

    hfToken = _env("HF_TOKEN")
    if not hfToken:
        print("HF_TOKEN 필수")
        return 1

    if args.indexSpec:
        if "|" not in args.indexSpec:
            print('--index 형식: "시장군|지수명" (예: "KOSPI|코스피 200")')
            return 1
        market, idxNm = args.indexSpec.split("|", 1)
        produceIndex(market.strip(), idxNm.strip(), hfToken=hfToken)
        return 0

    apiKey = _env("DATA_GO_KR_KEY")
    if (args.stock or args.daily or args.dailyIndex) and not apiKey:
        print("DATA_GO_KR_KEY 필수")
        return 1
    if args.stock:
        produceStock(args.stock.strip(), apiKey=apiKey, hfToken=hfToken)
        return 0
    if args.daily:
        daily(apiKey=apiKey, hfToken=hfToken, basDt=args.basDt)
        return 0
    if args.dailyIndex:
        dailyIndex(apiKey=apiKey, hfToken=hfToken, basDt=args.basDt)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
