"""수집된 parquet을 HuggingFace 또는 GitHub Releases에 업로드.

changed.txt가 있으면 변경된 파일만, 없으면 전체 폴더 업로드 (fallback).

사용법:
  python uploadData.py --target hf    # HuggingFace 업로드
  python uploadData.py --target gh    # GitHub Releases 업로드

환경변수:
  HF_TOKEN: HuggingFace write 토큰 (--target hf)
  GH_TOKEN: GitHub 토큰 (--target gh, Actions에서 자동 제공)
  SYNC_CATEGORY: finance / report / docs / sections / panel / edgarDocs
  DARTLAB_DATA_DIR: 데이터 경로 (기본: ./data)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHANGED_FILE = Path("dist/changed.txt")


def _dataDir(category: str) -> Path:
    """수집된 parquet 디렉토리."""
    from dartlab.core.dataConfig import DATA_RELEASES

    base = Path(os.environ.get("DARTLAB_DATA_DIR", os.path.join(os.getcwd(), "data")))
    return base / DATA_RELEASES[category]["dir"]


def _changedFiles(localDir: Path, category: str | None = None) -> list[Path] | None:
    """changed.txt에서 변경 파일 목록 로드. 없으면 None (전체 fallback).

    nested period-sharded category (sections / panel) 는 ``dist/changed_{category}.txt``
    우선 — 양식 ``{code}/{period}.parquet`` (+ panel 은 글로벌 ``_index.parquet``).
    일반 카테고리는 기존 ``dist/changed.txt``.
    """
    if category in ("sections", "panel"):
        nestedChangedFile = Path(f"dist/changed_{category}.txt")
        if nestedChangedFile.exists():
            names = [n.strip() for n in nestedChangedFile.read_text(encoding="utf-8").splitlines() if n.strip()]
            if not names:
                return []
            return [localDir / name for name in names if (localDir / name).exists()]
    if not CHANGED_FILE.exists():
        return None
    names = [n.strip() for n in CHANGED_FILE.read_text(encoding="utf-8").splitlines() if n.strip()]
    if not names:
        return []
    return [localDir / name for name in names if (localDir / name).exists()]


# HF 무료 플랜 commit 한도 128/hour. 공용 retry helper 사용 — 서버 권장
# 대기시간 ("retry this action in X minutes") 을 파싱해 실제 대기.
from _hfRetry import retryHfCall  # noqa: E402

_BATCH_INTERVAL_SECONDS = 10


def _uploadHf(category: str) -> None:
    """HuggingFace에 변경 파일만 업로드 (fallback: 전체 폴더)."""
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[uploadData] HF_TOKEN 환경변수가 필요합니다.")
        sys.exit(1)

    from huggingface_hub import CommitOperationAdd, HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    api = HfApi(token=token)
    dirPath = DATA_RELEASES[category]["dir"]
    localDir = _dataDir(category)

    changed = _changedFiles(localDir, category=category)
    isNested = bool(DATA_RELEASES[category].get("nested"))

    # changed.txt가 있고 변경 없음 → 스킵
    if changed is not None and len(changed) == 0:
        print("[uploadData] 변경 없음 → HuggingFace 업로드 스킵")
        return

    # changed.txt가 있고 변경 있음 → 개별 파일 업로드
    if changed is not None:
        print(f"[uploadData] HuggingFace 증분 업로드: {len(changed)}개 파일")
        # HF 128 commit/hr 한도 여유 — batch 당 300 파일 (1 commit). 예전 100 은
        # 파일 수 500 이면 commit 5회 — 다른 workflow 합치면 쉽게 한도 초과.
        batchSize = 300
        for i in range(0, len(changed), batchSize):
            batch = changed[i : i + batchSize]
            operations = [
                CommitOperationAdd(
                    # nested category (sections): localDir 기준 상대경로 보존 (예 "005930/2025.parquet").
                    # 일반 category: 파일명만 (top-level).
                    path_in_repo=f"{dirPath}/{f.relative_to(localDir).as_posix()}"
                    if isNested
                    else f"{dirPath}/{f.name}",
                    path_or_fileobj=str(f),
                )
                for f in batch
            ]
            batchNum = i // batchSize + 1
            totalBatches = (len(changed) + batchSize - 1) // batchSize
            retryHfCall(
                api.create_commit,
                repo_id=HF_REPO,
                repo_type="dataset",
                operations=operations,
                commit_message=f"sync {category}: {len(batch)} files ({batchNum}/{totalBatches})",
            )
            print(f"[uploadData] HF batch {batchNum}/{totalBatches} 완료")
            if batchNum < totalBatches:
                time.sleep(_BATCH_INTERVAL_SECONDS)
        print("[uploadData] HuggingFace 증분 업로드 완료")
        return

    # fallback: 전체 폴더 업로드. nested category 는 rglob (디렉터리 안 nested 파일 포함).
    if isNested:
        files = list(localDir.rglob("*.parquet")) + list(localDir.rglob("*.arrow"))
    else:
        files = list(localDir.glob("*.parquet")) + list(localDir.glob("*.arrow"))
    if not files:
        print(f"[uploadData] {localDir}에 업로드할 파일 없음")
        return

    print(f"[uploadData] HuggingFace 전체 업로드: {len(files)}개 파일 → {HF_REPO}/{dirPath}/")
    retryHfCall(
        api.upload_folder,
        repo_id=HF_REPO,
        repo_type="dataset",
        folder_path=str(localDir),
        path_in_repo=dirPath,
        commit_message=f"sync {category}: {len(files)} files",
    )
    print("[uploadData] HuggingFace 업로드 완료")


def _uploadGh(category: str) -> None:
    """[DEPRECATED 2026-04-08] GitHub Releases 업로드는 폐지됨. HF만 유지.

    data-finance/data-report/data-docs 태그는 정리됨.
    이 함수는 호환을 위해 남겨두지만 항상 no-op.
    """
    print(f"[uploadData] GitHub Releases 업로드는 폐지됨 (HF만 유지). category={category} → 스킵")
    return
    # 이하 dead code (참고용 보존)
    from dartlab.core.dataConfig import DATA_RELEASES  # noqa: F401

    conf = DATA_RELEASES[category]

    # HF-only 카테고리는 GitHub Release 스킵 (에셋 수 제한 등)
    hfOnlyCategories = {"edgarDocs", "edinetDocs", "edinet"}
    if category in hfOnlyCategories:
        print(f"[uploadData] {category}은 HF-only → GitHub Releases 스킵")
        return

    localDir = _dataDir(category)

    changed = _changedFiles(localDir)

    # changed.txt가 있고 변경 없음 → 스킵
    if changed is not None and len(changed) == 0:
        print("[uploadData] 변경 없음 → GitHub Releases 업로드 스킵")
        return

    # 대상 파일 결정
    files = changed if changed is not None else list(localDir.glob("*.parquet"))
    if not files:
        print(f"[uploadData] {localDir}에 업로드할 파일 없음")
        return

    label = "증분" if changed is not None else "전체"
    print(f"[uploadData] GitHub Releases {label} 업로드: {len(files)}개 파일")

    tag = conf.get("tag", f"data-{category}")
    print(f"[uploadData] GitHub Release {tag}: {len(files)}개 파일")
    _ghReleaseUpload(tag, files)

    print("[uploadData] GitHub Releases 업로드 완료")


def _ghReleaseUpload(tag: str, files: list[Path]) -> None:
    """gh CLI로 릴리즈에 파일 업로드. 릴리즈가 없으면 생성."""
    check = subprocess.run(
        ["gh", "release", "view", tag],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--title",
                f"Data: {tag}",
                "--notes",
                f"자동 데이터 동기화 ({tag})",
                "--latest=false",
            ],
            check=True,
        )

    # GitHub secondary rate limit (HTTP 403) 회피:
    # - 배치 20개 (50은 secondary rate limit 유발)
    # - 배치 사이 30초 sleep
    # - 배치 실패 시 60초 후 1회 재시도
    batchSize = 20
    sleepBetween = 30
    totalBatches = (len(files) + batchSize - 1) // batchSize
    for i in range(0, len(files), batchSize):
        batch = files[i : i + batchSize]
        batchNum = i // batchSize + 1
        cmd = ["gh", "release", "upload", tag, "--clobber"] + [str(f) for f in batch]
        try:
            subprocess.run(cmd, check=True)
            print(f"[uploadData] GH batch {batchNum}/{totalBatches} 완료 ({len(batch)}개)")
        except subprocess.CalledProcessError as e:
            print(f"[uploadData] GH batch {batchNum} 실패 → 60초 후 재시도: {e}")
            time.sleep(60)
            subprocess.run(cmd, check=True)
            print(f"[uploadData] GH batch {batchNum}/{totalBatches} 재시도 성공")
        if batchNum < totalBatches:
            time.sleep(sleepBetween)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=["hf", "gh"])
    args = parser.parse_args()

    category = os.environ.get("SYNC_CATEGORY", "finance")

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")

    if args.target == "hf":
        _uploadHf(category)
    else:
        _uploadGh(category)


if __name__ == "__main__":
    main()
