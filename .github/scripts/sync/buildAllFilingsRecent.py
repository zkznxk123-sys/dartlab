"""비정기(수시)공시 최근 통합 parquet 빌드 + HF push — 랜딩 터미널 콘솔청결 전용.

allFilings 는 일자별 ``dart/allFilings/{YYYYMMDD}.parquet`` 로 샤딩돼 있어, 브라우저가
회사별로 보려면 수십 일치 파일을 스캔해야 하고 휴일(파일 부재)마다 404 콘솔 오염이 난다.
HF tree API 는 CORS(huggingface.co only)라 브라우저 목록조회도 불가.

→ 운영자 머신/CI 에서 비정기공시 본문 parquet 을 **메타 컬럼만**(content_raw 제외) 모아
``dart/allFilings/recent.parquet`` 단일 통합 파일로 push. stock_code 정렬 → 브라우저
filter pushdown 이 회사 row-group 만 읽음 (scan/report·corpList 와 동일 "전역 1파일 +
stock_code 필터" 패턴). HF 증식 아님(파일 1개, 매번 덮어씀).

⚠ 전 이력 유지 — 과거 400일 trim 은 비정기 과거 dot(예: 2015)을 통째로 가려 폐기.
백필(allFilingsBackfill, floor 2015-01)이 깊어질수록 이 통합 파일도 깊어진다(HF baseline
merge 라 매 run 누적). 메타 6컬럼·zstd 라 전 이력도 작고 회사별 read 는 row-group 하나.
다시 trim 되살리지 말 것.

Usage:
    uv run python -X utf8 .github/scripts/sync/buildAllFilingsRecent.py [--no-push]
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


def _localFrames() -> list[pl.DataFrame]:
    """로컬 일자 parquet 의 메타 컬럼만 — 전 이력(ephemeral CI 면 forward 수집분만 존재).

    옛 ``[-days:]`` 슬라이스 제거: 운영자 머신의 백필분(2015~)까지 전부 포함해야 통합 파일이
    전 이력을 담는다. CI 는 로컬 forward 분만 있고 과거는 HF baseline merge 가 보존한다.
    """
    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem and f.stem != "recent")
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
    from dartlab.core.hfRetry import retryHfCall  # HF read SSOT — transient 429/timeout 재시도(thin-publish 창 제거)

    try:
        return retryHfCall(pl.read_parquet, url, columns=_KEEP)
    except Exception:  # noqa: BLE001 — 최초 빌드(파일 부재)·영구 실패면 None(다음 cron 자가복구)
        return None


def build(*, mergeHf: bool = True) -> Path:
    """로컬 일자분 + (옵션) 기존 HF recent.parquet 을 merge·dedup → 단일 전 이력 파일.

    operator 머신(전체 로컬 store)이든 ephemeral CI(forward 7일만 로컬)든, HF baseline 과
    합쳐 dedup 하므로 결과가 같게 수렴. trim 없음 — 백필이 깊어질수록 누적된다.
    """
    frames = _localFrames()
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
    # trim 없음 — 전 이력 유지(과거 dot 완결성). 백필(floor 2015-01)이 깊어질수록 누적.
    out = out.sort(["stock_code", "rcept_dt"], descending=[False, True])

    dest = _allFilingsDir() / _RECENT_NAME
    out.write_parquet(dest, compression="zstd", row_group_size=20_000)
    span = f"{out['rcept_dt'].min()}~{out['rcept_dt'].max()}"
    print(
        f"[build] {out.height:,} rows ({out['stock_code'].n_unique():,} 종목, {span}) → {dest} ({dest.stat().st_size / 1e6:.2f} MB)"
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
    ap.add_argument("--days", type=int, default=400, help="(deprecated·무시 — 전 이력 유지)")
    ap.add_argument("--no-push", action="store_true", help="빌드만, HF push 생략")
    args = ap.parse_args()

    dest = build()
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
