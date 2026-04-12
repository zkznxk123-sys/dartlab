"""Search content index main 풀리빌드 + HF 업로드.

월 1회 실행 (또는 수동):
1. 전체 docs + allFilings → main 세그먼트 풀리빌드 (rebuildContent)
2. HF `eddmpython/dartlab-data` 에 `dart/contentIndex/main.*` 업로드
3. delta 비움 (main에 흡수되었으므로)

환경:
- HF_TOKEN: HuggingFace 업로드용
"""

from __future__ import annotations

import os
import sys
import time


def main() -> int:
    hfToken = os.environ.get("HF_TOKEN", "")

    print("[main] content 인덱스 풀리빌드 시작")
    from dartlab.core.search import rebuildContent

    t0 = time.perf_counter()
    nDocs = rebuildContent(showProgress=True)
    elapsed = time.perf_counter() - t0
    print(f"[main] {nDocs:,} 문서, {elapsed/60:.1f}분")

    if nDocs == 0:
        print("[main] 빌드된 문서 없음")
        return 1

    if not hfToken:
        print("[main] HF_TOKEN 없음 — 업로드 스킵")
        return 0

    print("[main] HF 업로드")
    from huggingface_hub import HfApi

    from dartlab.core.search.fieldIndex import _contentIndexDir

    outDir = _contentIndexDir()
    files = ["main.npz", "main_stems.json", "main_meta.parquet", "main_info.json"]
    api = HfApi(token=hfToken)

    for f in files:
        src = outDir / f
        if not src.exists():
            print(f"  [skip] {f} 없음")
            continue
        dstPath = f"dart/contentIndex/{f}"
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=dstPath,
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
        )
        print(f"  [ok] {dstPath} ({src.stat().st_size / 1024 / 1024:.1f} MB)")

    # delta는 main에 흡수되었으므로 제거 (로컬). HF에서도 delete 시도.
    try:
        api.delete_file(path_in_repo="dart/contentIndex/delta.npz",
                        repo_id="eddmpython/dartlab-data", repo_type="dataset")
    except Exception:
        pass

    print("[main] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
