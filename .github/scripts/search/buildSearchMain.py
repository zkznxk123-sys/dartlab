"""Search content index main 풀리빌드 + HF 업로드.

월 1회 실행 (또는 수동):
1. 전체 allFilings + panel → main 세그먼트 풀리빌드 (rebuildContent)
2. HF staging 업로드 후 `dart/contentIndex/manifest.json` current pointer publish
3. delta 비움 (main에 흡수되었으므로)

환경:
- HF_TOKEN: HuggingFace 업로드용
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _catalogInputsFromEnv() -> tuple[str | None, list[str], list[str]]:
    manifestPaths = [p for p in os.environ.get("DARTLAB_SEARCH_SOURCE_MANIFESTS", "").split(os.pathsep) if p]
    expectedSources = [p.strip() for p in os.environ.get("DARTLAB_SEARCH_EXPECTED_SOURCES", "").split(",") if p.strip()]
    return os.environ.get("DARTLAB_SEARCH_CURRENT_CATALOG") or None, manifestPaths, expectedSources


def _buildRouterArtifact(tier: str = "full") -> int:
    """events.json 시드 → 결정론 라우터 router.json 을 인덱스 디렉터리에 도출 (scope=auto 확장축).

    빌드는 코퍼스 무관(시드만 입력)·수 ms·bounded(~수 KB). 반환 = 이벤트 수 (0 = 퇴행).
    """
    import json

    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.router import buildRouterModel

    eventsPath = Path(__file__).resolve().parent / "questionSet" / "events.json"
    events = json.loads(eventsPath.read_text(encoding="utf-8"))["events"]
    model = buildRouterModel(events)
    outDir = _contentIndexDir() if tier == "full" else _contentIndexDir(tier)
    (outDir / "router.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return len(model["events"])


def main() -> int:
    hfToken = os.environ.get("HF_TOKEN", "")
    mainMode = os.environ.get("DARTLAB_SEARCH_MAIN_MODE", "auto").strip().lower() or "auto"
    if mainMode not in {"auto", "catalog", "legacy"}:
        print(f"[main] invalid DARTLAB_SEARCH_MAIN_MODE={mainMode!r}")
        return 2

    nDocs = _buildMainFromCatalog(mainMode)
    if nDocs is None:
        print("[main] content 인덱스 풀리빌드 시작 (allFilings + DART panel + EDGAR panel + 뉴스)")
        from dartlab.providers.dart.search import rebuildContent

        t0 = time.perf_counter()
        nDocs = rebuildContent(includePanel=True, includeEdgarPanel=True, includeNews=True, showProgress=True)
        elapsed = time.perf_counter() - t0
        print(f"[main] {nDocs:,} 문서, {elapsed / 60:.1f}분")
    elif nDocs < 0:
        return abs(nDocs)

    # 통합검색(R*) artifact — 결정론 라우터 (질의→이벤트 canon 확장. 큐레이션 동의어는 코드 내장)
    nEvents = _buildRouterArtifact()
    print(f"[main] router.json {nEvents} 이벤트")

    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.fieldIndexRebuild import writeIndexManifest

    outDir = _contentIndexDir()
    writeIndexManifest(outDir, tier="full", buildCommand="buildSearchMain")

    if nDocs == 0:
        print("[main] 빌드된 문서 없음")
        return 1

    # 퇴행 가드 — HF pull 이 429 등으로 조용히 빈 데이터를 반환하면 nDocs/router 가 0 이 된다.
    # 이 상태로 업로드하면 프로덕션 인덱스를 빈 산출물로 *덮어쓰는 퇴행*. 업로드 중단.
    # 임계 350k 산정(2026-06-10 풀셋 실측 422,558 = panel 98k + EDGAR 56k + allFilings 165k + 뉴스 103k):
    # panel 누락(→324k)·allFilings 누락(→258k)·뉴스 누락(→319k)을 총량으로 차단. EDGAR/개별 소스
    # 누락은 워크플로 pull 검증(af/pn/ep>0)이 1차 차단. 옛 500k 는 은퇴한 docs 섹션-행(200만) 기준 유산.
    minDocs = int(os.environ.get("DARTLAB_SEARCH_MIN_DOCS", "350000"))
    if nEvents == 0 or nDocs < minDocs:
        print(
            f"[main] ✗ 퇴행 가드 발동 — router {nEvents} 이벤트 / {nDocs:,} 문서(< {minDocs:,}). "
            f"allFilings/panel pull 누락 의심 → 업로드 중단(프로덕션 보호)."
        )
        return 1

    if not hfToken:
        print("[main] HF_TOKEN 없음 — 업로드 스킵")
        return 0

    print("[main] HF staging 업로드 후 current manifest pointer publish (full = flat)")
    from dartlab.providers.dart.search.publishIndex import publishContentIndexFiles

    files = [
        "main.npz",
        "main_stems.json",
        "main_meta.parquet",
        "main_info.json",
        "router.json",
        "source_manifest_set.json",
        "manifest.json",
    ]
    summary = publishContentIndexFiles(
        token=hfToken,
        indexDir=outDir,
        files=files,
        tier="full",
        promoteCurrent=_promoteCurrent(),
        obsoleteCurrentFiles=[
            "delta.npz",
            "delta_stems.json",
            "delta_meta.parquet",
            "delta_info.json",
        ],
    )
    _printPublishSummary(summary)
    _writeCandidateEnv(summary)

    # ── lite tier — pip 사용자 기본 경량 배포(최근 N개월). full(flat)과 별 디렉터리라 공존. ──
    # full 업로드를 막지 않는 best-effort: lite 빌드/업로드 실패해도 full 은 이미 배포됨.
    _buildAndUploadLite(hfToken)

    print("[main] 완료")
    return 0


def _buildMainFromCatalog(mainMode: str) -> int | None:
    if mainMode == "legacy":
        return None
    currentCatalog, manifestPaths, expectedSources = _catalogInputsFromEnv()
    if not currentCatalog:
        if mainMode == "catalog":
            print("[main] catalog mode requires DARTLAB_SEARCH_CURRENT_CATALOG")
            return -2
        print("[main] catalog inputs 없음 — legacy raw main rebuild path 사용")
        return None
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.fieldIndexRebuild import rebuildMainFromCatalog
    from dartlab.providers.dart.search.pipeline import _loadCatalog, runCatalogDeltaDryRun

    result = runCatalogDeltaDryRun(
        previousCatalogPath=None,
        currentCatalogPath=currentCatalog,
        sourceManifestPaths=manifestPaths,
        expectedSources=expectedSources,
    )
    if not result.get("valid"):
        print(f"[main] catalog main input invalid: {result.get('errors')}")
        return -1
    t0 = time.perf_counter()
    catalog = _loadCatalog(currentCatalog)
    nDocs = rebuildMainFromCatalog(catalog, tier="full", showProgress=True)
    outDir = _contentIndexDir()
    import shutil

    shutil.copyfile(currentCatalog, outDir / "catalog_snapshot.parquet")
    _copySourceManifestSet(outDir)
    elapsed = time.perf_counter() - t0
    print(f"[main] catalog snapshot compaction {nDocs:,} 문서, {elapsed / 60:.1f}분")
    return nDocs


def _buildAndUploadLite(hfToken: str) -> None:
    """lite tier 빌드(최근 N개월 sinceDate 축소) + HF dart/contentIndex/lite/ 업로드.

    환경 ``DARTLAB_LITE_MONTHS`` (기본 18) 만큼 최근 공시만 색인 → 사용자 첫 다운로드 경량.
    퇴행 가드 — lite nDocs 가 너무 적으면(< DARTLAB_LITE_MIN_DOCS) 업로드 skip. full 배포엔 무영향.
    """
    from datetime import datetime, timedelta

    months = int(os.environ.get("DARTLAB_LITE_MONTHS", "18"))
    sinceDate = (datetime.now() - timedelta(days=int(months * 30.5))).strftime("%Y%m%d")
    print(f"[lite] tier 빌드 시작 — sinceDate={sinceDate} (최근 {months}개월)")

    from dartlab.providers.dart.search.fieldIndex import clearCache
    from dartlab.providers.dart.search.fieldIndexRebuild import pushContentIndex, rebuildMain, writeIndexManifest

    clearCache()
    currentCatalog, _, _ = _catalogInputsFromEnv()
    if currentCatalog:
        nLite = _buildLiteFromCatalog(currentCatalog, sinceDate)
    else:
        nLite = rebuildMain(
            includePanel=True,
            includeEdgarPanel=True,
            includeNews=True,
            tier="lite",
            sinceDate=sinceDate,
            showProgress=True,
        )
    _buildRouterArtifact(tier="lite")  # 라우터는 코퍼스 무관 — lite 디렉터리에 동거

    # 산출물 실측 크기 — '사용자 첫 다운로드 경량' 가치제안을 숫자로 검증(가정 금지).
    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir

    liteDir = _contentIndexDir("lite")
    _copySourceManifestSet(liteDir)
    liteBytes = sum(p.stat().st_size for p in liteDir.glob("*") if p.is_file())
    liteMb = liteBytes / 1024 / 1024
    print(f"[lite] 산출물 {liteMb:.1f} MB ({nLite:,} 문서)")
    maxMb = float(os.environ.get("DARTLAB_LITE_MAX_MB", "300"))
    if liteMb > maxMb:
        print(
            f"[lite] ⚠ 크기 경고 — {liteMb:.0f} MB > {maxMb:.0f} MB. lite 의 '경량' 가치가 약화 — "
            f"DARTLAB_LITE_MONTHS 축소 또는 종목 whitelist(시총 상위) 도입 검토."
        )

    minLite = int(os.environ.get("DARTLAB_LITE_MIN_DOCS", "50000"))
    if nLite < minLite:
        print(f"[lite] ✗ nDocs {nLite:,} < {minLite:,} — lite 업로드 skip (full 은 이미 배포됨)")
        return
    writeIndexManifest(liteDir, tier="lite", buildCommand="buildSearchMain.lite")
    print(f"[lite] {nLite:,} 문서 / {liteMb:.1f} MB → HF dart/contentIndex/lite/ 업로드")
    summary = pushContentIndex(hfToken, tier="lite", promoteCurrent=_promoteCurrent())
    _printPublishSummary(summary)
    _writeCandidateEnv(summary)
    print("[lite] 완료")


def _buildLiteFromCatalog(currentCatalog: str, sinceDate: str) -> int:
    import polars as pl

    from dartlab.providers.dart.search.fieldIndex import _contentIndexDir
    from dartlab.providers.dart.search.fieldIndexRebuild import rebuildMainFromCatalog
    from dartlab.providers.dart.search.pipeline import _loadCatalog

    catalog = _loadCatalog(currentCatalog)
    liteCatalog = _filterLiteCatalogRows(catalog, sinceDate)
    print(f"[lite] catalog mode — {catalog.height:,} rows -> {liteCatalog.height:,} rows")
    nLite = rebuildMainFromCatalog(liteCatalog, tier="lite", showProgress=True)
    liteDir = _contentIndexDir("lite")
    if isinstance(liteCatalog, pl.DataFrame):
        liteCatalog.write_parquet(liteDir / "catalog_snapshot.parquet")
    return nLite


def _filterLiteCatalogRows(catalogRows, sinceDate: str):
    import polars as pl

    if catalogRows.is_empty() or "date" not in catalogRows.columns:
        return catalogRows
    return (
        catalogRows.with_columns(
            pl.col("date").cast(pl.Utf8).str.replace_all("-", "").fill_null("").alias("__liteDate")
        )
        .filter(pl.col("__liteDate") >= sinceDate)
        .drop("__liteDate")
    )


def _copySourceManifestSet(outDir: Path) -> None:
    src = os.environ.get("DARTLAB_SEARCH_SOURCE_MANIFEST_SET", "").strip()
    if not src:
        return
    path = Path(src)
    if path.exists():
        import shutil

        shutil.copyfile(path, outDir / "source_manifest_set.json")


def _promoteCurrent() -> bool:
    raw = os.environ.get("DARTLAB_SEARCH_PROMOTE_CURRENT", "1")
    return raw.strip().lower() not in {"0", "false", "no", "n"}


def _printPublishSummary(summary: dict) -> None:
    action = "promote" if summary.get("promoted", True) else "stage"
    print(
        f"  [{action}] {summary.get('candidateManifestPath', '')} "
        f"-> {summary['currentPrefix']} {summary['publishMode']} ({len(summary['uploaded'])} uploads)"
    )


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
