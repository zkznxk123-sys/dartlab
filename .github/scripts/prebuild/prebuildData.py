"""CI용 scan 프리빌드 + HF 업로드.

수집 완료 후 실행되어 scan 프리빌드 데이터를 생성하고 HuggingFace에 업로드.

흐름:
  1. INPUT_CATEGORIES(finance/report/panel) 를 HF dataset 에서 seed (idempotent)
  2. buildScan() → changes/finance/report(12 apiType)/sharesOutstanding + docsIndex
     (changes/sharesOutstanding/docsIndex 는 panel 을 읽는다 — 회사 enum = 로컬 panel dir glob)
  3. HF upload_folder → dart/scan/

환경변수:
  DARTLAB_DATA_DIR: 데이터 경로 (기본: ./data)
  HF_TOKEN: HuggingFace write 토큰
  PREBUILD_TARGETS: scan (기본, 쉼표 구분 확장 가능)
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _hfRetry import retryHfCall  # noqa: E402

# scan 프리빌드가 읽는 입력 카테고리 SSOT — buildScan 하위 빌더의 원천.
#   finance/report → 재무·보고서 빌더, panel → changes/sharesOutstanding/docsIndex 빌더.
# seed·캐시확인 모두 이 한 곳을 참조한다 (워크플로 YAML 에 목록 중복 금지).
INPUT_CATEGORIES: tuple[str, ...] = ("finance", "report", "panel")


def _seedInputs(dataDir: str) -> None:
    """INPUT_CATEGORIES 를 HF dataset 에서 idempotent seed.

    offlineGuard 가 HuggingFace host 는 허용한다 (prebuild input 다운로드는 필수). panel 은
    회사 enum 이 로컬 dir glob 이라 artifact 가 로컬에 있어야 빌더가 종목을 발견한다.
    """
    from dartlab.pipeline.seed import seedCategoriesFromHf

    summary = seedCategoriesFromHf(list(INPUT_CATEGORIES), dataDir=dataDir)
    for cat, (total, new, mb) in summary.items():
        print(f"[prebuild] seed {cat}: 로컬 {total}개 (신규 {new} / {mb:.1f}MB)")


def _checkDataReady(dataDir: str) -> dict[str, int]:
    """INPUT_CATEGORIES 입력 캐시 존재 여부 확인. 카테고리별 파일 수 반환."""
    from dartlab.core.dataConfig import DATA_RELEASES

    counts = {}
    for cat in INPUT_CATEGORIES:
        catDir = Path(dataDir) / DATA_RELEASES[cat]["dir"]
        n = len(list(catDir.glob("*.parquet"))) if catDir.exists() else 0
        counts[cat] = n
    return counts


def _buildScan(dataDir: str) -> dict[str, Path | list[Path] | None]:
    """scan 프리빌드 실행."""
    from dartlab.scan.builders.kr import buildScan

    return buildScan(sinceYear=2021, verbose=True)


def _buildDocsIndex(dataDir: str) -> Path | None:
    """docsIndex 슬림 인덱스 빌드 — panel 섹션 메타에서 생성.

    Args:
        dataDir: 데이터 디렉토리.

    Returns:
        산출 parquet 경로 또는 None (실패 시).

    Raises:
        없음 (실패는 silent → summary 에 표기).

    Example:
        >>> path = _buildDocsIndex("./data")
        >>> path
        PosixPath('data/dart/scan/docsIndex.parquet')
    """
    try:
        from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

        return buildDocsIndex(sinceYear=2016, batchSize=100, verbose=True)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[prebuild] docsIndex 빌드 실패 (스킵): {exc}")
        return None


def _uploadScan(dataDir: str) -> None:
    """scan 결과를 HuggingFace에 업로드."""
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[prebuild] HF_TOKEN 없음 → 업로드 스킵")
        return

    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    scanDir = Path(dataDir) / DATA_RELEASES["scan"]["dir"]
    if not scanDir.exists():
        print("[prebuild] scan 디렉토리 없음 → 업로드 스킵")
        return

    parquets = list(scanDir.rglob("*.parquet"))
    if not parquets:
        print("[prebuild] scan parquet 없음 → 업로드 스킵")
        return

    api = HfApi(token=token)
    dirPath = DATA_RELEASES["scan"]["dir"]

    print(f"[prebuild] HF 업로드: {len(parquets)}개 파일 → {HF_REPO}/{dirPath}/")
    retryHfCall(
        api.upload_folder,
        repo_id=HF_REPO,
        repo_type="dataset",
        folder_path=str(scanDir),
        path_in_repo=dirPath,
        commit_message=f"prebuild scan: {len(parquets)} files",
    )
    print("[prebuild] HF 업로드 완료")


def _validateFinanceParquet(dataDir: str, sourceFileCount: int) -> None:
    """프리빌드 finance.parquet 품질 검증.

    원본 finance 파일 수 대비 프리빌드 종목 수가 50% 미만이면 에러로 빌드 실패 처리.
    """
    from dartlab.core.dataConfig import DATA_RELEASES

    scanDir = Path(dataDir) / DATA_RELEASES["scan"]["dir"]
    fp = scanDir / "finance.parquet"
    if not fp.exists():
        # 원본 finance 가 있었는데 프리빌드 산출이 없으면 = seed/빌드 실패(부분 scan 을 HF 에 올릴 위험).
        # 검증 스킵이 그 실패를 은폐하지 않게 fail-fast. 원본도 0 이면 정상(빌드 대상 없음) → 스킵.
        if sourceFileCount > 0:
            print(
                f"[prebuild] ❌ 원본 finance {sourceFileCount}종목인데 프리빌드 finance.parquet 미생성 — seed/빌드 실패"
            )
            sys.exit(1)
        print("[prebuild] finance.parquet 없음 (원본도 0) → 검증 스킵")
        return

    import polars as pl

    df = pl.read_parquet(str(fp))
    scCol = "stockCode" if "stockCode" in df.columns else "stock_code"
    prebuildStocks = df.select(scCol).unique().height
    ratio = prebuildStocks / sourceFileCount if sourceFileCount > 0 else 0

    print(f"[prebuild] 품질: 원본 {sourceFileCount}종목, 프리빌드 {prebuildStocks}종목 ({ratio:.0%})")

    if ratio < 0.5:
        print(f"[prebuild] ❌ 커버리지 {ratio:.0%} < 50% — 캐시가 stale한 것으로 판단")
        sys.exit(1)


def main():
    # prebuild = offline only. 외부 API 호출은 sync 단계 책임 — 가드로 강제.
    # HF dataset 다운로드는 default allow.
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]
    os.makedirs(dataDir, exist_ok=True)

    targets = os.environ.get("PREBUILD_TARGETS", "scan").split(",")
    print(f"[prebuild] targets={targets} dataDir={dataDir}")

    # 1단계: 입력 seed (HF) + 로컬 캐시 확인
    _seedInputs(dataDir)
    counts = _checkDataReady(dataDir)
    print("[prebuild] 캐시: " + " ".join(f"{k}={v}" for k, v in counts.items()))

    if all(v == 0 for v in counts.values()):
        print("[prebuild] 데이터 캐시 없음 → 프리빌드 건너뜀")
        _writeSummary(counts, None, 0)
        return

    # 2단계: scan 프리빌드 — 외부 API 호출 0. corp_profile 은 sync/meta 단계 (kindlist.yml)
    # 가 책임지고 HF dataset 에 push, 여기서는 로컬 parquet 만 읽는다.
    if "scan" in targets:
        start = time.time()
        results = _buildScan(dataDir)
        elapsed = time.time() - start
        print(f"[prebuild] scan 빌드 완료: {elapsed:.0f}초")

        # 2.5단계: docsIndex 슬림 인덱스 (panel 섹션에서 빌드)
        if counts.get("panel", 0) > 0:
            results["docsIndex"] = _buildDocsIndex(dataDir)

        # 2.6단계: 데이터 품질 검증
        _validateFinanceParquet(dataDir, counts["finance"])

        # 3단계: HF 업로드
        _uploadScan(dataDir)
        _writeSummary(counts, results, elapsed)
    else:
        print("[prebuild] scan이 targets에 없음 → 스킵")
        _writeSummary(counts, None, 0)


def _writeSummary(
    counts: dict[str, int],
    results: dict | None,
    elapsed: float,
) -> None:
    """GitHub Actions step summary 작성."""
    summaryPath = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summaryPath:
        return

    dataDir = os.environ.get("DARTLAB_DATA_DIR", "./data")

    with open(summaryPath, "a", encoding="utf-8") as f:
        f.write("## Scan Prebuild\n\n")
        f.write("| 항목 | 값 |\n|------|----|\n")
        for cat, n in counts.items():
            f.write(f"| {cat} 캐시 | {n}개 |\n")
        f.write(f"| 소요 시간 | {elapsed:.0f}초 |\n")

        if results:
            from dartlab.core.dataConfig import DATA_RELEASES

            scanDir = Path(dataDir) / DATA_RELEASES["scan"]["dir"]
            if scanDir.exists():
                totalMb = sum(p.stat().st_size for p in scanDir.rglob("*.parquet")) / 1024 / 1024
                fileCount = len(list(scanDir.rglob("*.parquet")))
                f.write(f"| scan 파일 | {fileCount}개 |\n")
                f.write(f"| scan 크기 | {totalMb:.1f}MB |\n")


if __name__ == "__main__":
    main()
