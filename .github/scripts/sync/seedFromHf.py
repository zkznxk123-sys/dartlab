"""HF dataset 에서 category별 parquet 다운로드 (idempotent seed).

HF 를 single source of truth 로 격상. GHA cache 가 miss/stale 이어도 이 step 이 부족분을 채워
cold start death spiral 차단.

설계:
  1. `list_repo_files` 로 HF 의 파일 목록 1회 조회 (resolver 1 request)
  2. 로컬에 이미 있는 파일은 건너뜀 (HEAD 안 씀 → rate limit 회피)
  3. 누락/신규만 직접 HTTP GET 으로 다운로드 (파일당 1 request)
  4. 파일 크기로 로컬 완결성 검증 (HF metadata size 와 비교)

왜 `snapshot_download` 가 아닌가:
  - snapshot_download 는 파일마다 HEAD 로 etag 검증 → 2920 HEAD + 2920 GET = 5840 requests
  - HF rate limit: 5000 resolvers/5min/IP → cold start 에서 초과
  - 이 스크립트는 list 1회 + 누락분 GET 만 → cold 풀다운로드도 2920 requests

사용:
  uv run python -X utf8 .github/scripts/seedFromHf.py --category finance
  uv run python -X utf8 .github/scripts/seedFromHf.py --category finance,report,docs

환경변수:
  DARTLAB_DATA_DIR: 데이터 루트 (기본 ./data)
  HF_TOKEN: HF 토큰 (private dataset 이면 필수, public 에선 rate limit 완화용)
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _download(url: str, dest: Path, token: str | None, timeout: int = 60) -> int:
    """단일 파일 HTTP GET. 429/5xx/일시 네트워크 오류는 대기 후 재시도.

    반환: 다운로드 바이트 수.

    HF 제한: 5000 resolvers / 5분 / account. cold seed 로 3 카테고리 풀다운로드하면
    ~8800 요청 → 도중 429 히트. 429 응답의 Retry-After (보통 60~300s) 존중.
    502/503/504 같은 resolver 일시 장애는 짧은 지수 백오프로 복구한다.
    """
    import urllib.error
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")

    maxRetries = 5
    # HF rate limit window = 5분. 첫 retry 부터 window 완전 재설정 + 10초 버퍼.
    baseWait = 310.0
    transientCodes = {500, 502, 503, 504}

    for attempt in range(maxRetries):
        try:
            req = urllib.request.Request(url)
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            bytesWritten = 0
            with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as f:
                while chunk := resp.read(1 << 20):  # 1MB
                    f.write(chunk)
                    bytesWritten += len(chunk)
            tmp.replace(dest)
            return bytesWritten
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < maxRetries - 1:
                retryAfter = e.headers.get("Retry-After")
                try:
                    wait = max(float(retryAfter), baseWait) if retryAfter else baseWait * (1 + attempt * 0.5)
                except ValueError:
                    wait = baseWait * (1 + attempt * 0.5)
                print(
                    f"[seed] 429 rate limit ({dest.name}) — {wait:.0f}s 대기 후 재시도 {attempt + 1}/{maxRetries}",
                    flush=True,
                )
                time.sleep(wait)
                continue
            if e.code in transientCodes and attempt < maxRetries - 1:
                wait = min(30.0 * (2**attempt), 180.0)
                print(
                    f"[seed] HTTP {e.code} transient ({dest.name}) — {wait:.0f}s 대기 후 재시도 {attempt + 1}/{maxRetries}",
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == maxRetries - 1:
                raise
            wait = min(15.0 * (2**attempt), 120.0)
            print(
                f"[seed] network transient ({dest.name}) — {wait:.0f}s 대기 후 재시도 {attempt + 1}/{maxRetries}: {e}",
                flush=True,
            )
            time.sleep(wait)


def seedCategory(cat: str, dataDir: Path) -> tuple[int, int, float]:
    """반환: (총 파일 수, 신규 다운로드 수, 다운로드 MB)."""
    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    if cat not in DATA_RELEASES:
        print(f"[seed] ERROR: unknown category '{cat}' — {list(DATA_RELEASES)}")
        sys.exit(1)

    dirPath = DATA_RELEASES[cat]["dir"]
    token = os.environ.get("HF_TOKEN") or None

    api = HfApi(token=token)

    # 1. HF 파일 목록 + size 조회 (resolver 1 request).
    # dirPath 하위 전부 (확장자 무관, 서브디렉토리 포함) — dart/* 는 parquet, landing/map 은 json.
    print(f"[seed] {cat}: list {HF_REPO}/{dirPath}/", flush=True)
    repoInfo = api.repo_info(repo_id=HF_REPO, repo_type="dataset", files_metadata=True)
    remoteFiles: dict[str, int] = {}  # relpath -> size
    prefix = f"{dirPath}/"
    for sibling in repoInfo.siblings or []:
        if sibling.rfilename.startswith(prefix) and not sibling.rfilename.endswith("/"):
            remoteFiles[sibling.rfilename] = sibling.size or 0

    print(f"[seed] {cat}: HF {len(remoteFiles)}개 파일 발견", flush=True)

    # 2. 로컬 대조 — 파일 존재 + 크기 일치하면 스킵
    missing: list[tuple[str, int]] = []
    for rel, size in remoteFiles.items():
        local = dataDir / rel
        if local.exists() and local.stat().st_size == size:
            continue
        missing.append((rel, size))

    if not missing:
        print(f"[seed] {cat}: 로컬 모두 최신 — 스킵", flush=True)
        downloadedBytes = 0
    else:
        print(f"[seed] {cat}: {len(missing)}개 다운로드", flush=True)

        # 3. 병렬 GET (동시 4 — rate limit 대비 여유)
        baseUrl = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"
        downloadedBytes = 0
        started = time.time()

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(_download, f"{baseUrl}/{rel}", dataDir / rel, token): rel for rel, _ in missing}
            done = 0
            for fut in as_completed(futures):
                rel = futures[fut]
                try:
                    downloadedBytes += fut.result()
                except Exception as e:
                    print(f"[seed] {cat} FAIL {rel}: {type(e).__name__}: {str(e)[:120]}", flush=True)
                    raise
                done += 1
                if done % 100 == 0 or done == len(missing):
                    elapsed = time.time() - started
                    mb = downloadedBytes / 1024 / 1024
                    print(f"[seed] {cat}: {done}/{len(missing)} ({mb:.1f}MB, {elapsed:.0f}s)", flush=True)

    localCat = dataDir / dirPath
    localFiles = [p for p in localCat.rglob("*") if p.is_file()]
    totalCount = len(localFiles)
    downloadedMb = downloadedBytes / 1024 / 1024
    print(f"[seed] {cat}: 로컬 {totalCount}개, 이번 신규 {len(missing)}개 / {downloadedMb:.1f}MB", flush=True)
    return totalCount, len(missing), downloadedMb


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--category",
        required=True,
        help="쉼표 구분 (예: finance,report,docs). DATA_RELEASES 키 중 택일 가능",
    )
    p.add_argument(
        "--data-dir",
        default=os.environ.get("DARTLAB_DATA_DIR", "./data"),
        help="데이터 루트 (기본 $DARTLAB_DATA_DIR 또는 ./data)",
    )
    args = p.parse_args()

    dataDir = Path(args.data_dir).resolve()
    dataDir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, tuple[int, int, float]] = {}
    for cat in args.category.split(","):
        cat = cat.strip()
        if not cat:
            continue
        summary[cat] = seedCategory(cat, dataDir)

    print(f"[seed] done: {summary}")

    # GitHub Actions step summary
    stepSummary = os.environ.get("GITHUB_STEP_SUMMARY")
    if stepSummary:
        with open(stepSummary, "a", encoding="utf-8") as f:
            f.write("## HF Seed\n\n| 카테고리 | 로컬 총 | 신규 다운로드 | 다운로드 크기 |\n|---|---|---|---|\n")
            for cat, (total, newCount, mb) in summary.items():
                f.write(f"| {cat} | {total} | {newCount} | {mb:.1f}MB |\n")


if __name__ == "__main__":
    main()
