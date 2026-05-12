"""CI용 scan 프리빌드 + HF 업로드.

수집 완료 후 실행되어 scan 프리빌드 데이터를 생성하고 HuggingFace에 업로드.

흐름:
  1. 로컬 data/dart/{finance,report,docs} 캐시 확인
  2. buildScan() 호출 → changes.parquet, finance.parquet, report/12개 apiType
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hfRetry import retryHfCall  # noqa: E402


def _checkDataReady(dataDir: str) -> dict[str, int]:
    """finance/report/docs 캐시 존재 여부 확인. 카테고리별 파일 수 반환."""
    from dartlab.core.dataConfig import DATA_RELEASES

    counts = {}
    for cat in ("finance", "report", "docs"):
        catDir = Path(dataDir) / DATA_RELEASES[cat]["dir"]
        n = len(list(catDir.glob("*.parquet"))) if catDir.exists() else 0
        counts[cat] = n
    return counts


def _buildScan(dataDir: str) -> dict[str, Path | list[Path] | None]:
    """scan 프리빌드 실행."""
    from dartlab.scan.builders.kr import buildScan

    return buildScan(sinceYear=2021, verbose=True)


def _buildDocsIndex(dataDir: str) -> Path | None:
    """docs 슬림 인덱스 빌드 (P3 — whimsical 흡수).

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
        print("[prebuild] finance.parquet 없음 → 검증 스킵")
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
    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]
    os.makedirs(dataDir, exist_ok=True)

    targets = os.environ.get("PREBUILD_TARGETS", "scan").split(",")
    print(f"[prebuild] targets={targets} dataDir={dataDir}")

    # 1단계: 데이터 캐시 확인
    counts = _checkDataReady(dataDir)
    print(f"[prebuild] 캐시: finance={counts['finance']} report={counts['report']} docs={counts['docs']}")

    if all(v == 0 for v in counts.values()):
        print("[prebuild] 데이터 캐시 없음 → 프리빌드 건너뜀")
        _writeSummary(counts, None, 0)
        return

    # 2단계: scan 프리빌드
    if "scan" in targets:
        start = time.time()
        results = _buildScan(dataDir)
        elapsed = time.time() - start
        print(f"[prebuild] scan 빌드 완료: {elapsed:.0f}초")

        # 2.5단계: docs 슬림 인덱스 (P3 — whimsical 흡수)
        if counts.get("docs", 0) > 0:
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
