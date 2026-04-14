"""Search content index delta 증분 빌드 + HF 업로드.

매일 실행:
1. 최근 N일 allFilings 수집 (collectMeta + fillContent)
2. content delta 세그먼트 빌드 (rebuildContentDelta)
3. HF `eddmpython/dartlab-data` 에 `dart/contentIndex/delta.*` 업로드

main 풀리빌드는 별도 워크플로우 (월 1회).

환경:
- DART_API_KEYS: OpenDART API 키 (쉼표 구분)
- HF_TOKEN: HuggingFace 업로드용
- LOOKBACK_DAYS: 증분 대상 일수 (기본 30)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def main() -> int:
    lookback = int(os.environ.get("LOOKBACK_DAYS", "30"))
    hfToken = os.environ.get("HF_TOKEN", "")

    today = datetime.now()
    startDate = (today - timedelta(days=lookback)).strftime("%Y%m%d")
    endDate = today.strftime("%Y%m%d")

    print(f"[delta] 기간: {startDate} ~ {endDate} ({lookback}일)")

    # Phase 1: collectMeta
    print("[delta] Phase 1: collectMeta")
    from dartlab.core.search import collectMeta, fillContent, rebuildContentDelta

    t0 = time.perf_counter()
    nMeta = collectMeta(startDate, endDate)
    print(f"  수집된 메타: {nMeta:,} 건, {time.perf_counter() - t0:.0f}초")

    # Phase 2: fillContent
    print("[delta] Phase 2: fillContent")
    t0 = time.perf_counter()
    fillContent()
    print(f"  content 채우기 완료, {time.perf_counter() - t0:.0f}초")

    # Phase 3: delta 인덱스 빌드
    print("[delta] Phase 3: content delta 세그먼트 빌드")
    t0 = time.perf_counter()
    nDocs = rebuildContentDelta(daysBack=lookback)
    print(f"  delta {nDocs:,} 문서, {time.perf_counter() - t0:.0f}초")

    if nDocs == 0:
        print("[delta] 빌드된 문서 없음 — 업로드 스킵")
        return 0

    # Phase 4: HF 업로드
    if not hfToken:
        print("[delta] HF_TOKEN 없음 — 업로드 스킵 (로컬 빌드만)")
        return 0

    print("[delta] Phase 4: HF 업로드")
    from huggingface_hub import HfApi

    from dartlab.core.search.fieldIndex import _contentIndexDir

    outDir = _contentIndexDir()
    files = ["delta.npz", "delta_stems.json", "delta_meta.parquet", "delta_info.json"]
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

    print("[delta] 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
