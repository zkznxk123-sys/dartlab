"""content 인덱스 main 풀리빌드 실행 스크립트.

로컬 실행용. 전체 docs + allFilings 로드 → main 세그먼트 빌드 → (옵션) HF 업로드.

실행:
    uv run python -X utf8 scripts/dev/rebuildContentMain.py
"""

from __future__ import annotations

import os
import sys
import time


def main() -> int:
    print(f"[start] {time.strftime('%H:%M:%S')}")
    from dartlab.core.search import rebuildContent
    from dartlab.core.search.fieldIndex import pushContentIndex

    t0 = time.perf_counter()
    nDocs = rebuildContent(showProgress=True)
    elapsed = time.perf_counter() - t0
    print(f"[main] {nDocs:,}문서, {elapsed/60:.1f}분")

    token = os.environ.get("HF_TOKEN")
    if token:
        print("[HF] 업로드 시작")
        pushContentIndex(token=token)
        print("[HF] 업로드 완료")
    else:
        print("[HF] HF_TOKEN 없음 — 로컬 저장만")

    print(f"[end] {time.strftime('%H:%M:%S')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
