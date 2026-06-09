"""비정기(수시)공시 최근 통합 parquet 빌드 + HF push — 랜딩 터미널 콘솔청결 전용.

allFilings 는 일자별 ``dart/allFilings/{YYYYMMDD}.parquet`` 로 샤딩돼 있어, 브라우저가
회사별로 보려면 수십 일치 파일을 스캔해야 하고 휴일(파일 부재)마다 404 콘솔 오염이 난다.
HF tree API 는 CORS(huggingface.co only)라 브라우저 목록조회도 불가.

→ 운영자 머신/CI 에서 최근 N 일치 본문 parquet 을 **메타 컬럼만**(content_raw 제외) 모아
``dart/allFilings/recent.parquet`` 단일 롤링 파일로 push. stock_code 정렬 → 브라우저
filter pushdown 이 회사 row-group 만 읽음. HF 증식 아님(파일 1개, 매번 덮어씀).

Usage:
    uv run python -X utf8 .github/scripts/sync/buildAllFilingsRecent.py [--days 400]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES, repoFor
from dartlab.gather.dart.allFilingsCollector import _ALLFILINGS_DIR_KEY, _META_SUFFIX, _allFilingsDir

# 랜딩 로더가 쓰는 메타 컬럼 (content_raw·fetch_status 제외)
_KEEP = ["stock_code", "corp_name", "rcept_dt", "report_nm", "rcept_no", "flr_nm"]
_REGULAR = ("사업보고서", "반기보고서", "분기보고서")
_RECENT_NAME = "recent.parquet"


def _localFrames(days: int) -> list[pl.DataFrame]:
    """로컬 일자 parquet 의 메타 컬럼만 (ephemeral CI 면 forward 수집분만 존재)."""
    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem and f.stem != "recent")
    files = files[-days:]
    frames: list[pl.DataFrame] = []
    for f in files:
        try:
            schema = pl.read_parquet_schema(f)
            frames.append(pl.read_parquet(f, columns=[c for c in _KEEP if c in schema]))
        except Exception:  # noqa: BLE001 — 손상 파일 격리
            continue
    return frames


def _hfBaseFrame() -> pl.DataFrame | None:
    """기존 HF recent.parquet (있으면) — CI 증분 merge 의 baseline."""
    relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    url = f"https://huggingface.co/datasets/{repoFor(_ALLFILINGS_DIR_KEY)}/resolve/main/{relDir}/{_RECENT_NAME}"
    try:
        return pl.read_parquet(url, columns=_KEEP)
    except Exception:  # noqa: BLE001 — 최초 빌드(파일 부재)·네트워크 실패면 None
        return None


def build(days: int, *, mergeHf: bool = True) -> Path:
    """로컬 일자분 + (옵션) 기존 HF recent.parquet 을 merge·dedup·trim → 단일 파일.

    operator 머신(전체 로컬 store)이든 ephemeral CI(forward 7일만 로컬)든, HF baseline 과
    합쳐 dedup 하므로 결과가 같게 수렴. rcept_dt 최근 ``days`` 일로 trim → 파일 크기 bound.
    """
    frames = _localFrames(days)
    if mergeHf:
        base = _hfBaseFrame()
        if base is not None:
            frames.append(base)
    if not frames:
        raise SystemExit("로컬·HF 어느쪽도 allFilings parquet 없음 — 수집/백필 먼저")

    out = pl.concat(frames, how="diagonal_relaxed").with_columns(pl.col(c).cast(pl.Utf8) for c in _KEEP)
    # 비정기만 — 정기보고서 명칭 제외 (수집단계서 대부분 제외돼 있으나 belt-and-suspenders)
    out = out.filter(
        pl.col("stock_code").str.strip_chars().str.len_chars().eq(6)
        & ~pl.col("report_nm").fill_null("").str.contains("|".join(_REGULAR))
    )
    out = out.unique(subset=["rcept_no"], keep="first")
    # rcept_dt 최근 days 일로 trim (파일 크기 bound — backfill 로 로컬이 2015 까지 커져도)
    cutoff = out.select(pl.col("rcept_dt").max()).item()
    if cutoff:
        from datetime import datetime, timedelta

        try:
            floor = (datetime.strptime(str(cutoff)[:8], "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
            out = out.filter(pl.col("rcept_dt").str.slice(0, 8) >= floor)
        except ValueError:
            pass
    out = out.sort(["stock_code", "rcept_dt"], descending=[False, True])

    dest = _allFilingsDir() / _RECENT_NAME
    out.write_parquet(dest, compression="zstd", row_group_size=20_000)
    print(
        f"[build] {out.height:,} rows ({out['stock_code'].n_unique():,} 종목, ≤{days}일) → {dest} ({dest.stat().st_size / 1e6:.2f} MB)"
    )
    return dest


def push(dest: Path, token: str) -> None:
    from huggingface_hub import HfApi

    from dartlab.core.hfRetry import retryHfCall

    relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    api = HfApi(token=token)
    retryHfCall(
        api.upload_file,
        path_or_fileobj=str(dest),
        path_in_repo=f"{relDir}/{_RECENT_NAME}",
        repo_id=repoFor(_ALLFILINGS_DIR_KEY),
        repo_type="dataset",
        commit_message="allFilings recent: 비정기공시 최근 통합 롤링 parquet",
    )
    print(f"[HF↑] pushed {relDir}/{_RECENT_NAME} → {repoFor(_ALLFILINGS_DIR_KEY)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=400, help="포함할 최근 일자 수 (로컬 파일 기준)")
    ap.add_argument("--no-push", action="store_true", help="빌드만, HF push 생략")
    args = ap.parse_args()

    dest = build(args.days)
    if args.no_push:
        return 0
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        # .env 로드 시도
        envp = Path(_cfg.__file__).resolve().parents[2] / ".env"
        if envp.exists():
            for line in envp.read_text(encoding="utf-8").splitlines():
                if line.startswith("HF_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not token:
        print("[HF↑] HF_TOKEN 없음 — push skip (빌드만 완료)", file=sys.stderr)
        return 1
    push(dest, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
