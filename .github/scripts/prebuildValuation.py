"""CI 용 valuation snapshot 프리빌드 + HF 업로드.

매일 장 마감 이후 (KST 04:00, UTC 19:00) GH Actions cron 으로 실행된다.
네이버 API 로 전종목 시세·밸류에이션 raw 데이터를 수집해 `dart/scan/valuation.parquet`
을 생성하고 HuggingFace 에 업로드한다. 실패 시 기존 parquet 은 그대로 유지된다.

흐름:
  1. `dartlab.scan.builders.kr.buildValuation()` 호출
  2. 생성된 parquet 검증 (0건 / 55% 미만 → 기존 유지)
  3. HF upload_file → `dart/scan/valuation.parquet`

환경변수:
  DARTLAB_DATA_DIR : 데이터 경로 (기본: ./data)
  HF_TOKEN         : HuggingFace write 토큰
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hfRetry import retryHfCall  # noqa: E402


def _build(dataDir: str) -> Path | None:
    """`buildValuation()` 실행. parquet 경로 반환 (실패면 None)."""
    from dartlab.scan.builders.kr import buildValuation

    return buildValuation(verbose=True)


def _upload(parquet: Path) -> None:
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("[valuation] HF_TOKEN 없음 → 업로드 스킵")
        return
    if not parquet.exists():
        print("[valuation] parquet 없음 → 업로드 스킵")
        return

    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    api = HfApi(token=token)
    dirPath = DATA_RELEASES["scan"]["dir"]
    sizeMb = parquet.stat().st_size / 1024 / 1024
    print(f"[valuation] HF 업로드: {parquet.name} ({sizeMb:.1f}MB) → {HF_REPO}/{dirPath}/")

    retryHfCall(
        api.upload_file,
        path_or_fileobj=str(parquet),
        path_in_repo=f"{dirPath}/{parquet.name}",
        repo_id=HF_REPO,
        repo_type="dataset",
        commit_message=f"valuation snapshot: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
    )
    print("[valuation] HF 업로드 완료")


def _writeSummary(parquet: Path | None, elapsed: float) -> None:
    summaryPath = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summaryPath:
        return
    with open(summaryPath, "a", encoding="utf-8") as f:
        f.write("## Valuation Snapshot\n\n")
        f.write("| 항목 | 값 |\n|------|----|\n")
        if parquet and parquet.exists():
            import polars as pl

            df = pl.read_parquet(str(parquet))
            sizeMb = parquet.stat().st_size / 1024 / 1024
            f.write(f"| 종목 수 | {df.height} |\n")
            f.write(f"| 파일 크기 | {sizeMb:.1f} MB |\n")
            if "snapshotAt" in df.columns and df.height > 0:
                f.write(f"| 수집 시각 | {df['snapshotAt'][0]} UTC |\n")
        else:
            f.write("| 결과 | 생성 실패 (기존 parquet 유지) |\n")
        f.write(f"| 소요 시간 | {elapsed:.0f}초 |\n")


def main() -> int:
    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]
    os.makedirs(dataDir, exist_ok=True)

    print(f"[valuation] dataDir={dataDir}")

    start = time.time()
    parquet = _build(dataDir)
    elapsed = time.time() - start

    if parquet is None:
        print(f"[valuation] 빌드 실패 또는 품질 게이트 탈락 ({elapsed:.0f}s) — HF 업로드 스킵")
        _writeSummary(None, elapsed)
        # 실패해도 exit 0 — 이전 parquet 이 HF 에 남아있으므로 서비스 영향 無
        return 0

    _upload(parquet)
    _writeSummary(parquet, elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
