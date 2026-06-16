"""Search content index delta 증분 빌드 + HF 업로드.

매일 실행:
1. 최근 N일 allFilings 수집 (collectMeta + fillContent)
2. allFilings parquet HF 업로드 (lookback 기간 — 신규/정정/error retry 모두 반영)
3. content delta 세그먼트 빌드 (rebuildContentDelta)
4. HF staging 업로드 후 `dart/contentIndex/manifest.json` current pointer publish

main 풀리빌드는 별도 워크플로우 (월 1회).

환경:
- DART_API_KEYS: OpenDART API 키 (쉼표 구분)
- HF_TOKEN: HuggingFace 업로드용
- LOOKBACK_DAYS: 증분 대상 일수 (기본 30)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _catalogInputsFromEnv() -> tuple[str | None, str, list[str], list[str]]:
    manifestPaths = [p for p in os.environ.get("DARTLAB_SEARCH_SOURCE_MANIFESTS", "").split(os.pathsep) if p]
    expectedSources = [p.strip() for p in os.environ.get("DARTLAB_SEARCH_EXPECTED_SOURCES", "").split(",") if p.strip()]
    return (
        os.environ.get("DARTLAB_SEARCH_PREVIOUS_CATALOG") or None,
        os.environ["DARTLAB_SEARCH_CURRENT_CATALOG"],
        manifestPaths,
        expectedSources,
    )


def _uploadDeltaFiles(hfToken: str) -> None:
    print("[delta] Phase 4: HF staging 업로드 후 current manifest pointer publish")
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    outDir = _contentIndexDir()
    files = [
        "delta.npz",
        "delta_stems.json",
        "delta_meta.parquet",
        "delta_info.json",
        "manifest.json",
        "catalog_snapshot.parquet",
        "source_manifest_set.json",
    ]
    previousManifest = outDir / "previous_manifest.json"
    summary = publishContentIndexFiles(
        token=hfToken,
        indexDir=outDir,
        files=files,
        tier="full",
        previousManifestPath=previousManifest if previousManifest.exists() else None,
        promoteCurrent=_promoteCurrent(),
    )
    action = "promote" if summary.get("promoted", True) else "stage"
    print(
        f"  [{action}] {summary.get('candidateManifestPath', '')} "
        f"-> {summary['currentPrefix']} {summary['publishMode']} ({len(summary['uploaded'])} uploads)"
    )
    _writeCandidateEnv(summary)


def main() -> int:
    lookback = int(os.environ.get("LOOKBACK_DAYS", "30"))
    hfToken = os.environ.get("HF_TOKEN", "")
    deltaMode = os.environ.get("DARTLAB_SEARCH_DELTA_MODE", "auto").strip().lower() or "auto"

    if deltaMode not in {"auto", "catalog", "legacy"}:
        print(f"[delta] invalid DARTLAB_SEARCH_DELTA_MODE={deltaMode!r}")
        return 2

    if os.environ.get("DARTLAB_SEARCH_DELTA_DRY_RUN", "").strip() in {"1", "true", "True"}:
        from dartlab.providers.dart.search.pipeline import runCatalogDeltaDryRun

        previousCatalog, currentCatalog, manifestPaths, expectedSources = _catalogInputsFromEnv()
        result = runCatalogDeltaDryRun(
            previousCatalogPath=previousCatalog,
            currentCatalogPath=currentCatalog,
            sourceManifestPaths=manifestPaths,
            reportPath=os.environ.get("DARTLAB_SEARCH_DELTA_REPORT") or None,
            expectedSources=expectedSources,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("valid") else 1

    hasCatalogInputs = bool(os.environ.get("DARTLAB_SEARCH_CURRENT_CATALOG"))
    useCatalogDelta = (
        deltaMode == "catalog"
        or os.environ.get("DARTLAB_SEARCH_DELTA_FROM_CATALOG", "").strip() in {"1", "true", "True"}
        or (deltaMode == "auto" and hasCatalogInputs)
    )
    if useCatalogDelta:
        if not hasCatalogInputs:
            print("[delta] catalog mode requires DARTLAB_SEARCH_CURRENT_CATALOG")
            return 2
        previousCatalog, currentCatalog, manifestPaths, expectedSources = _catalogInputsFromEnv()
        from dartlab.providers.dart.search.pipeline import exportDeltaRowsForContentIndex, runCatalogDeltaDryRun

        result = runCatalogDeltaDryRun(
            previousCatalogPath=previousCatalog,
            currentCatalogPath=currentCatalog,
            sourceManifestPaths=manifestPaths,
            reportPath=os.environ.get("DARTLAB_SEARCH_DELTA_REPORT") or None,
            expectedSources=expectedSources,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if not result.get("valid"):
            return 1
        from dartlab.providers.dart.search.pipeline import _loadCatalog

        rows = exportDeltaRowsForContentIndex(_loadCatalog(previousCatalog), _loadCatalog(currentCatalog))
        if rows.height == 0:
            print("[delta] catalog changed-set 없음 — 업로드 스킵")
            return 0
        from dartlab.providers.dart.search.fieldIndex import (
            _contentIndexDir,
            buildContentSegment,
            clearCache,
            saveSegment,
        )
        from dartlab.providers.dart.search.fieldIndexRebuild import writeIndexManifest

        idx, meta = buildContentSegment(rows.to_dicts(), showProgress=True)
        outDir = _contentIndexDir()
        saveSegment(idx, meta, "delta", outDir=outDir)
        shutil.copyfile(currentCatalog, outDir / "catalog_snapshot.parquet")
        _copySourceManifestSet(outDir)
        writeIndexManifest(outDir, tier="full", buildCommand="buildSearchDelta.catalog")
        clearCache()
        print(f"[delta] catalog changed-set {idx['nDocs']:,} 문서")
        if not hfToken:
            print("[delta] HF_TOKEN 없음 — 업로드 스킵 (로컬 빌드만)")
            return 0
        _uploadDeltaFiles(hfToken)
        print("[delta] 완료")
        return 0

    if deltaMode == "auto":
        print("[delta] catalog inputs 없음 — legacy allFilings delta path 사용")

    today = datetime.now()
    startDate = (today - timedelta(days=lookback)).strftime("%Y%m%d")
    endDate = today.strftime("%Y%m%d")

    print(f"[delta] 기간: {startDate} ~ {endDate} ({lookback}일)")

    # Phase 1: collectMeta
    print("[delta] Phase 1: collectMeta")
    from dartlab.providers.dart.search import collectMeta, fillContent, rebuildContentDelta

    t0 = time.perf_counter()
    nMeta = collectMeta(startDate, endDate)
    print(f"  수집된 메타: {nMeta:,} 건, {time.perf_counter() - t0:.0f}초")

    # Phase 2: fillContent
    print("[delta] Phase 2: fillContent")
    t0 = time.perf_counter()
    fillContent()
    print(f"  content 채우기 완료, {time.perf_counter() - t0:.0f}초")

    # Phase 2.5 제거 — allFilings parquet HF 업로드 단일 소유자 = `dartlab.pipeline allFilings`
    # (Job 2, originalSync.yml). 본 워크플로는 검색 delta 인덱스용 content 만 로컬 수집(Phase 1/2)
    # 하고 HF push 는 하지 않는다. 옛 이중 push(여기 30일 + Job 2 7일 → 같은 dart/allFilings 경로)
    # 가 동시각 commit 충돌(412)·중복 업로드를 유발했음 — 단일 소유로 일원화.

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

    _uploadDeltaFiles(hfToken)

    print("[delta] 완료")
    return 0


def _copySourceManifestSet(outDir: Path) -> None:
    src = os.environ.get("DARTLAB_SEARCH_SOURCE_MANIFEST_SET", "").strip()
    if not src:
        return
    path = Path(src)
    if path.exists():
        shutil.copyfile(path, outDir / "source_manifest_set.json")


def _promoteCurrent() -> bool:
    raw = os.environ.get("DARTLAB_SEARCH_PROMOTE_CURRENT", "1")
    return raw.strip().lower() not in {"0", "false", "no", "n"}


def _writeCandidateEnv(summary: dict) -> None:
    envFile = os.environ.get("GITHUB_ENV", "").strip()
    candidate = str(summary.get("candidateManifestPath") or "").strip()
    tier = str(summary.get("tier") or "full").strip().upper()
    if not envFile or not candidate:
        return
    key = f"DARTLAB_SEARCH_{tier}_CANDIDATE_MANIFEST"
    with Path(envFile).open("a", encoding="utf-8") as f:
        f.write(f"{key}={candidate}\n")


if __name__ == "__main__":
    sys.exit(main())
