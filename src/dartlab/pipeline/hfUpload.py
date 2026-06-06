"""HuggingFace 업로드 — 옛 ``uploadData._uploadHf`` 정본 이동.

증분(changed 매니페스트) 우선, 없으면 전체 폴더 fallback. nested 대용량(panel·원본 zip/txt)은
``upload_large_folder``(resumable·병렬·자체 backoff), 일반은 ``create_commit`` 배치(300/commit).
모든 HF 호출은 ``core.hfRetry.retryHfCall`` 로 감싼다(429·LFS-RuntimeError unwrap).

원본(DART 정기 zip·EDGAR 원본)도 ``nested`` 카테고리로 업로드 가능 — 옛 "원본 비공개"
가드는 폐기(원본=SSOT 전략 전환). 원본 repo 는 ``DATA_RELEASES[...]['public']=False`` 로 비공개.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dartlab.core.hfRetry import retryHfCall
from dartlab.pipeline.changed import changedPath, readChanged

_BATCH_INTERVAL_SECONDS = 10
_FILECOUNT_WARN = int(os.environ.get("DARTLAB_HF_FILECOUNT_WARN", "80000"))


def _resolveHfToken(token: str | None = None) -> str:
    """HF 토큰 해석 — 인자 > ``HF_TOKEN`` env > ``.env`` (DART 키와 동일 우선순위).

    Args:
        token: 명시 토큰(우선).

    Returns:
        해석된 토큰 문자열.

    Raises:
        ValueError: 어디서도 토큰을 못 찾으면.

    Example:
        >>> import os; os.environ["HF_TOKEN"] = "x"; _resolveHfToken()
        'x'
    """
    if token:
        return token
    envTok = os.environ.get("HF_TOKEN")
    if envTok:
        return envTok
    envPath = Path(".env")
    if envPath.exists():
        for raw in envPath.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("export "):  # `export HF_TOKEN=...` 형식 허용
                line = line[7:].strip()
            if line.startswith("HF_TOKEN="):
                # 인라인 주석(' #') 제거 + 따옴표/공백 정리. 빈 값이면 fall-through(명확한 에러).
                val = line.split("=", 1)[1].split(" #", 1)[0].strip().strip('"').strip("'").strip()
                if val:
                    return val
    raise ValueError("HF_TOKEN 필요 — 인자/env/.env 어디에도 없음")


def _categoryDir(category: str, dataDir: str | None = None) -> Path:
    from dartlab.core.dataConfig import DATA_RELEASES

    base = Path(dataDir or os.environ.get("DARTLAB_DATA_DIR") or os.path.join(os.getcwd(), "data"))
    return base / DATA_RELEASES[category]["dir"]


def _monitorFileCount(localDir: Path, category: str, repo: str) -> int:
    # 전 파일타입 카운트(parquet/arrow + 원본 zip/txt) — HF repo 파일수 한계는 타입 무관.
    n = sum(1 for p in localDir.rglob("*") if p.is_file())
    if n >= _FILECOUNT_WARN:
        print(
            f"[hfUpload] ⚠ 파일수 경고 — {category} {n:,}개 (repo={repo}, 임계 {_FILECOUNT_WARN:,}). "
            f"HF repo ~10만 권장한계 접근 → 전용 repo 분리(DATA_RELEASES['{category}']['repo']) 검토.",
            flush=True,
        )
    return n


def uploadCategoryToHf(
    category: str,
    *,
    changedFiles: list[str] | None = None,
    dataDir: str | None = None,
    token: str | None = None,
    fullUpload: bool = False,
) -> int:
    """category 의 parquet 을 HF 에 업로드 — 증분 우선, 없으면 전체 폴더.

    ``changedFiles`` 가 주어지면 그 상대경로만; None 이면 ``dist/changed_{category}.txt``
    매니페스트 확인(존재+빈목록=업로드 skip, 부재=전체 폴더 fallback). nested 대용량은
    ``upload_large_folder``. 원본 zip/txt 도 nested 카테고리로 업로드(가드 폐기).

    Args:
        category: DATA_RELEASES 카테고리명.
        changedFiles: 카테고리 dir 기준 변경 상대경로(우선). None=매니페스트/fallback.
        dataDir: 데이터 루트(기본 env/`./data`).
        token: HF 토큰(인자>env>.env).

    Returns:
        업로드한 파일 수(증분) 또는 -1(전체 폴더 모드, 카운트 미집계) 또는 0(skip).

    Raises:
        ValueError: 토큰 부재.

    Example:
        >>> uploadCategoryToHf("panel", changedFiles=[])  # 변경 0 → skip  # doctest: +SKIP
        0
    """
    from huggingface_hub import CommitOperationAdd, HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, repoFor

    token = _resolveHfToken(token)
    dirPath = DATA_RELEASES[category]["dir"]
    repo = repoFor(category)
    localDir = _categoryDir(category, dataDir)
    isNested = bool(DATA_RELEASES[category].get("nested"))
    api = HfApi(token=token)

    # 변경 목록 해석: 인자 > changed_{cat}.txt > 부재(None=전체 fallback).
    # 옛 전역 dist/changed.txt fallback 제거 — 카테고리 무관이라 다른 stage 의 목록을 잘못 읽어
    # 교차오염(엉뚱한 파일 업로드/0건). changed_{category}.txt 가 SSOT.
    if changedFiles is not None:
        rels: list[str] | None = list(changedFiles)
    elif changedPath(category).exists():
        rels = readChanged(category)
    else:
        rels = None

    if isNested:
        _monitorFileCount(localDir, category, repo)

    if rels is not None and len(rels) == 0:
        print(f"[hfUpload] {category} 변경 없음 → 업로드 skip", flush=True)
        return 0

    if rels is not None:
        files = [localDir / r for r in rels if (localDir / r).exists()]
        missing = [r for r in rels if not (localDir / r).exists()]
        if missing:
            # 매니페스트(changed_{cat}.txt)는 업로드 SSOT — 거기 적힌 파일이 로컬에 없으면 그 변경분이
            # *조용히* 누락된다(부분 업로드). raise 대신 loud 경고 후 존재분만 진행(1건 부재가 전체
            # 업로드를 막지 않게). 운영자는 경고로 매니페스트-디스크 불일치를 즉시 본다.
            shown = ", ".join(missing[:10]) + (" …" if len(missing) > 10 else "")
            print(
                f"[hfUpload] ⚠ {category} 매니페스트 {len(rels)}건 중 {len(missing)}건 로컬 부재 — 업로드 누락: {shown}",
                flush=True,
            )
        if not files:
            print(f"[hfUpload] {category} 변경목록 {len(rels)}건이나 로컬 파일 0 → skip", flush=True)
            return 0
        print(f"[hfUpload] {category} 증분 업로드: {len(files)}개", flush=True)
        batchSize = 300
        total = (len(files) + batchSize - 1) // batchSize
        for i in range(0, len(files), batchSize):
            batch = files[i : i + batchSize]
            ops = [
                CommitOperationAdd(
                    path_in_repo=(
                        f"{dirPath}/{f.relative_to(localDir).as_posix()}" if isNested else f"{dirPath}/{f.name}"
                    ),
                    path_or_fileobj=str(f),
                )
                for f in batch
            ]
            n = i // batchSize + 1
            retryHfCall(
                api.create_commit,
                repo_id=repo,
                repo_type="dataset",
                operations=ops,
                commit_message=f"sync {category}: {len(batch)} files ({n}/{total})",
            )
            print(f"[hfUpload] {category} batch {n}/{total} 완료", flush=True)
            if n < total:
                time.sleep(_BATCH_INTERVAL_SECONDS)
        return len(files)

    # 전체 폴더 fallback
    if isNested:
        base = Path(dataDir or os.environ.get("DARTLAB_DATA_DIR") or os.path.join(os.getcwd(), "data"))
        # 전 파일타입(parquet/arrow + 원본 zip/txt) — allow_patterns=[dir/**] 가 전부 업로드.
        nFiles = sum(1 for p in localDir.rglob("*") if p.is_file())
        if nFiles == 0:
            print(f"[hfUpload] {localDir} 업로드할 파일 없음", flush=True)
            return 0
        # 매니페스트 부재(rels None) + nested 전체 = 사고로 수만 파일 재업로드(429/비용) 위험.
        # 의도적 full 은 fullUpload=True 또는 DARTLAB_HF_ALLOW_FULL=1 로 명시해야 진행.
        if not fullUpload and os.environ.get("DARTLAB_HF_ALLOW_FULL") != "1":
            print(
                f"[hfUpload] ⚠ {category} 매니페스트 없음 + nested {nFiles}개 — 전체 재업로드 방지 skip "
                f"(의도면 fullUpload=True 또는 DARTLAB_HF_ALLOW_FULL=1)",
                flush=True,
            )
            return 0
        nWorkers = int(os.environ.get("HF_UPLOAD_WORKERS", "2"))
        print(f"[hfUpload] {category} 대용량 업로드: {nFiles}개 {dirPath}/** → {repo} (workers={nWorkers})", flush=True)
        # retryHfCall 로 감쌈 — upload_large_folder 내부 create_repo 가 429(1000req/5min) 맞으면
        # 전체 중단되던 것을 5분 윈도 백오프로 재시도(내부 워커 재개성은 별개로 보존).
        retryHfCall(
            api.upload_large_folder,
            repo_id=repo,
            repo_type="dataset",
            folder_path=str(base),
            allow_patterns=[f"{dirPath}/**"],
            num_workers=nWorkers,
        )
        return -1

    files = list(localDir.glob("*.parquet")) + list(localDir.glob("*.arrow"))
    if not files:
        print(f"[hfUpload] {localDir} 업로드할 파일 없음", flush=True)
        return 0
    print(f"[hfUpload] {category} 전체 업로드: {len(files)}개 → {repo}/{dirPath}/", flush=True)
    retryHfCall(
        api.upload_folder,
        repo_id=repo,
        repo_type="dataset",
        folder_path=str(localDir),
        path_in_repo=dirPath,
        commit_message=f"sync {category}: {len(files)} files",
    )
    return len(files)
