"""HF dataset → 로컬 parquet seed (idempotent) — 옛 ``seedFromHf.seedCategory`` 정본.

HF 를 single source of truth 로: category prefix tree 1회 + 로컬 size-대조 + 누락분만
GET 으로 cold-start death-spiral 차단(snapshot_download 의 파일당 HEAD rate-limit 회피).
429 는 Retry-After/310s window 존중, 5xx/네트워크는 지수 백오프, tmp→rename atomic.
``upload`` 의 ``core.hfRetry`` 와 별 경로(여긴 urllib GET, hf_hub 아님)라 둘 다 보존.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def _download(url: str, dest: Path, token: str | None, timeout: int = 60) -> int:
    """단일 파일 HTTP GET — 429/5xx/네트워크 transient 재시도, tmp→rename atomic.

    Args:
        url: HF resolve URL.
        dest: 저장 경로.
        token: HF 토큰(있으면 Authorization 헤더).
        timeout: 소켓 타임아웃 초.

    Returns:
        다운로드 바이트 수.

    Raises:
        urllib.error.HTTPError: 비-transient 또는 재시도 소진.

    Example:
        >>> _download("https://example/x", Path("/tmp/x"), None)  # doctest: +SKIP
        1024
    """
    import urllib.error
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    maxRetries = 5
    baseWait = 310.0  # HF rate-limit window 5분 + 버퍼
    transientCodes = {500, 502, 503, 504}

    for attempt in range(maxRetries):
        try:
            req = urllib.request.Request(url)
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            bytesWritten = 0
            with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as f:
                while chunk := resp.read(1 << 20):
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
                print(f"[seed] 429 ({dest.name}) — {wait:.0f}s 후 재시도 {attempt + 1}/{maxRetries}", flush=True)
                time.sleep(wait)
                continue
            if e.code in transientCodes and attempt < maxRetries - 1:
                wait = min(30.0 * (2**attempt), 180.0)
                print(
                    f"[seed] HTTP {e.code} ({dest.name}) — {wait:.0f}s 후 재시도 {attempt + 1}/{maxRetries}", flush=True
                )
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == maxRetries - 1:
                raise
            wait = min(15.0 * (2**attempt), 120.0)
            print(f"[seed] network ({dest.name}) — {wait:.0f}s 후 재시도 {attempt + 1}/{maxRetries}: {e}", flush=True)
            time.sleep(wait)
    return 0


def _seedOne(category: str, dataDir: Path, token: str | None) -> tuple[int, int, float]:
    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, repoFor
    from dartlab.core.hfRetry import retryHfCall

    if category not in DATA_RELEASES:
        raise ValueError(f"unknown category '{category}' — {list(DATA_RELEASES)}")

    dirPath = DATA_RELEASES[category]["dir"]
    repo = repoFor(category)  # 전용 repo(dartOriginal 등) 존중 — HF_REPO 하드코딩 시 빈 seed
    api = HfApi(token=token)
    print(f"[seed] {category}: list-tree {repo}/{dirPath}/", flush=True)
    remoteFiles = _remoteTreeFiles(api, repo=repo, dirPath=dirPath, token=token)
    print(f"[seed] {category}: HF {len(remoteFiles)}개 발견", flush=True)

    missing = [(rel, size) for rel, size in remoteFiles.items() if not _isFresh(dataDir / rel, size)]
    downloadedBytes = 0
    if missing:
        print(f"[seed] {category}: {len(missing)}개 다운로드", flush=True)
        baseUrl = f"https://huggingface.co/datasets/{repo}/resolve/main"
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(_download, f"{baseUrl}/{rel}", dataDir / rel, token): rel for rel, _ in missing}
            for fut in as_completed(futures):
                downloadedBytes += fut.result()
    else:
        print(f"[seed] {category}: 로컬 모두 최신 — skip", flush=True)

    localCat = dataDir / dirPath
    total = sum(1 for p in localCat.rglob("*") if p.is_file()) if localCat.exists() else 0
    mb = downloadedBytes / 1024 / 1024
    print(f"[seed] {category}: 로컬 {total}개, 신규 {len(missing)}개 / {mb:.1f}MB", flush=True)
    return total, len(missing), mb


def _remoteTreeFiles(api: Any, *, repo: str, dirPath: str, token: str | None) -> dict[str, int]:
    """HF dataset 의 특정 category prefix 아래 파일만 열거한다.

    ``repo_info(files_metadata=True)`` 는 dataset 전체 siblings metadata 를 읽어
    ``/api/datasets/{repo}?blobs=True`` 쿼터를 크게 소모한다. prebuild 의 panel seed 는
    이 경로에서 반복적으로 429 를 맞았으므로, category path 로 scope 된 tree endpoint 만
    사용한다.
    """

    from dartlab.core.hfRetry import retryHfCall

    def _listTree() -> list[Any]:
        return list(
            api.list_repo_tree(
                repo_id=repo,
                path_in_repo=dirPath,
                repo_type="dataset",
                recursive=True,
                expand=True,
                token=token,
            )
        )

    entries = retryHfCall(_listTree)
    files: dict[str, int] = {}
    for item in entries:
        rel = getattr(item, "rfilename", None) or getattr(item, "path", "")
        if not rel or rel.endswith("/"):
            continue
        size = getattr(item, "size", 0) or 0
        files[str(rel)] = int(size)
    return files


def _isFresh(local: Path, size: int) -> bool:
    return local.exists() and local.stat().st_size == size


def seedCategoriesFromHf(
    categories: list[str],
    *,
    dataDir: str | None = None,
    token: str | None = None,
) -> dict[str, tuple[int, int, float]]:
    """여러 category 를 HF 에서 idempotent seed — 로컬 누락/크기불일치만 다운로드.

    Args:
        categories: DATA_RELEASES 카테고리명 목록.
        dataDir: 데이터 루트(기본 env/`./data`).
        token: HF 토큰(없으면 public rate-limit 완화만 못 받음).

    Returns:
        {category: (로컬총수, 신규다운로드수, 다운로드MB)} dict.

    Raises:
        ValueError: 미등록 category.

    Example:
        >>> seedCategoriesFromHf(["finance"])  # doctest: +SKIP
        {'finance': (2900, 12, 4.3)}
    """
    root = Path(dataDir or os.environ.get("DARTLAB_DATA_DIR") or "./data").resolve()
    root.mkdir(parents=True, exist_ok=True)
    tok = token or os.environ.get("HF_TOKEN") or None
    return {c.strip(): _seedOne(c.strip(), root, tok) for c in categories if c and c.strip()}
