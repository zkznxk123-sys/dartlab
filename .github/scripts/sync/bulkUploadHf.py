"""로컬 parquet을 HuggingFace에 배치 업로드 (초기 마이그레이션용).

사용법:
    python bulkUploadHf.py finance              # 미업로드만 (기존 skip)
    python bulkUploadHf.py docs                 # 미업로드만
    python bulkUploadHf.py docs --force         # 전체 재업로드 (schema 마이그레이션)
    python bulkUploadHf.py docs --since 86400   # 최근 N초 안 mtime 변경분만
"""

import argparse
import sys
import time
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

REPO = "eddmpython/dartlab-data"
BATCH_SIZE = 100
MAX_RETRIES = 3

CATEGORY_DIR = {
    "docs": "dart/docs",
    "finance": "dart/finance",
    "report": "dart/report",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category", nargs="?", default="finance", help="finance/report/docs")
    parser.add_argument("--force", action="store_true", help="전체 재업로드 (schema 마이그레이션)")
    parser.add_argument(
        "--since",
        type=float,
        default=0,
        help="최근 N초 안 mtime 변경분만 (--force 와 동시 사용 X)",
    )
    args = parser.parse_args()
    category = args.category
    # DART 원본 zip 비공개 강제 — original/ 카테고리는 HF 업로드 금지 (사용자 결정 2026-05-21).
    # 상세: CLAUDE.md "DART 원본 zip 비공개" 섹션 + operation.docsBuilderRefactor §7.
    if "original" in category.lower():
        raise ValueError(f"category='{category}' 거부 — data/dart/original/ 은 로컬 임시 보관 전용, HF 업로드 금지")
    dirPath = CATEGORY_DIR[category]
    localDir = Path(f"data/{dirPath}")

    token = None
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line.startswith("HF_TOKEN="):
            token = line.split("=", 1)[1].strip()
            break

    api = HfApi(token=token)

    # 이미 올라간 파일 확인
    try:
        existing = set()
        for f in api.list_repo_tree(REPO, path_in_repo=dirPath, repo_type="dataset", recursive=False):
            existing.add(f.rfilename.split("/")[-1])
        print(f"이미 업로드: {len(existing)}개")
    except Exception:
        existing = set()

    allFiles = sorted(localDir.glob("*.parquet"))
    if args.force:
        remaining = list(allFiles)
        print(f"--force: 전체 {len(remaining)}개 재업로드 (schema 마이그레이션 모드)")
    elif args.since > 0:
        cutoff = time.time() - args.since
        remaining = [f for f in allFiles if f.stat().st_mtime >= cutoff]
        print(f"--since {args.since}s: 최근 변경 {len(remaining)}개 / 전체 {len(allFiles)}개")
    else:
        remaining = [f for f in allFiles if f.name not in existing]
        print(f"미업로드: {len(remaining)}개 / 전체: {len(allFiles)}개")

    if not remaining:
        print("모두 업로드 완료")
        return

    total = len(remaining)
    totalBatches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total, BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        batchNum = i // BATCH_SIZE + 1
        print(f"[{batchNum}/{totalBatches}] {len(batch)}개 업로드 중...")

        operations = [CommitOperationAdd(path_in_repo=f"{dirPath}/{f.name}", path_or_fileobj=str(f)) for f in batch]

        for attempt in range(MAX_RETRIES):
            try:
                api.create_commit(
                    repo_id=REPO,
                    repo_type="dataset",
                    operations=operations,
                    commit_message=f"{category} {batchNum}/{totalBatches} ({len(batch)} files)",
                )
                print(f"  batch {batchNum} 완료")
                break
            except Exception as e:
                print(f"  attempt {attempt + 1} 실패: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(15)
                else:
                    print(f"  batch {batchNum} 최종 실패, 건너뜀")

    print(f"{category} 업로드 완료")


if __name__ == "__main__":
    main()
