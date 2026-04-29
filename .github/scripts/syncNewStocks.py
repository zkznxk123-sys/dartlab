"""KindList 신규 종목 DART bootstrap.

일일 recent sync 는 최근 정기공시가 있는 종목만 잡는다. 이 스크립트는 KindList 를
기준으로 HF dataset 에 아직 없는 신규 종목 parquet 을 찾아 finance/report/docs 를
최소 범위로 수집한다.

환경변수:
  DART_API_KEYS: DART OpenAPI 키 (쉼표 구분)
  HF_TOKEN: HuggingFace 토큰 (파일 목록 조회 rate limit 완화)
  NEW_STOCK_CATEGORIES: finance,report,docs (기본)
  NEW_STOCK_LIMIT: 카테고리별 최대 수집 종목 수 (기본 50, 0이면 제한 없음)
  NEW_STOCK_MAX_WORKERS: DART API worker 수 제한 (선택)
  DARTLAB_DATA_DIR: 데이터 루트 (기본 ./data)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import polars as pl

VALID_CATEGORIES = {"finance", "report", "docs"}


def _fileHash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(65536))
        h.update(str(path.stat().st_size).encode())
    return h.hexdigest()


def _snapshotHashes(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    return {f.name: _fileHash(f) for f in directory.glob("*.parquet")}


def _parseCategories(raw: str) -> list[str]:
    categories = [c.strip() for c in raw.split(",") if c.strip()]
    invalid = [c for c in categories if c not in VALID_CATEGORIES]
    if invalid:
        raise SystemExit(f"[syncNewStocks] invalid NEW_STOCK_CATEGORIES: {invalid}")
    return categories or ["finance", "report", "docs"]


def _kindListCodes() -> list[str]:
    from dartlab.gather.listing import getKindList

    df = getKindList()
    if "시장구분" in df.columns:
        df = df.filter(pl.col("시장구분") != "코넥스")
    if "종목코드" not in df.columns:
        raise SystemExit("[syncNewStocks] KindList에 종목코드 컬럼이 없습니다.")
    return sorted({str(code).zfill(6) for code in df["종목코드"].to_list() if code})


def _remoteParquetCodes(categories: list[str]) -> dict[str, set[str]]:
    from huggingface_hub import HfApi

    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

    api = HfApi(token=os.environ.get("HF_TOKEN") or None)
    info = api.repo_info(repo_id=HF_REPO, repo_type="dataset", files_metadata=False)

    result = {cat: set() for cat in categories}
    prefixes = {cat: f"{DATA_RELEASES[cat]['dir']}/" for cat in categories}

    for sibling in info.siblings or []:
        name = sibling.rfilename
        if not name.endswith(".parquet"):
            continue
        for cat, prefix in prefixes.items():
            if name.startswith(prefix):
                result[cat].add(Path(name).stem.zfill(6))
                break
    return result


def _localParquetCodes(category: str, dataDir: Path) -> set[str]:
    from dartlab.core.dataConfig import DATA_RELEASES

    localDir = dataDir / DATA_RELEASES[category]["dir"]
    if not localDir.exists():
        return set()
    return {p.stem.zfill(6) for p in localDir.glob("*.parquet")}


def _changedFiles(category: str, dataDir: Path, before: dict[str, str]) -> tuple[list[str], list[str]]:
    from dartlab.core.dataConfig import DATA_RELEASES

    localDir = dataDir / DATA_RELEASES[category]["dir"]
    after = _snapshotHashes(localDir)
    newFiles = [name for name in after if name not in before]
    updatedFiles = [name for name in after if name in before and after[name] != before[name]]
    return sorted(newFiles), sorted(updatedFiles)


def _collectCategory(category: str, codes: list[str]) -> dict[str, dict[str, int]]:
    from dartlab.providers.dart.openapi.batch import batchCollect

    maxWorkersRaw = os.environ.get("NEW_STOCK_MAX_WORKERS", "").strip()
    maxWorkers = int(maxWorkersRaw) if maxWorkersRaw else None
    return batchCollect(
        codes,
        categories=[category],
        maxWorkers=maxWorkers,
        incremental=True,
        showProgress=False,
    )


def _writeSummary(summary: dict[str, Any]) -> None:
    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    (dist / "new_stock_sync_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stepSummary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not stepSummary:
        return
    with open(stepSummary, "a", encoding="utf-8") as f:
        f.write("## DART New Stocks Sync\n\n")
        f.write("| 카테고리 | HF 누락 | 수집 시도 | 신규 파일 | 업데이트 파일 | 행 수 |\n")
        f.write("|---|---:|---:|---:|---:|---:|\n")
        for cat, item in summary["categories"].items():
            f.write(
                f"| {cat} | {item['missingRemoteCount']} | {item['attemptedCount']} | "
                f"{item['newFileCount']} | {item['updatedFileCount']} | {item['rows']} |\n"
            )
        if summary.get("capped"):
            f.write("\n카테고리별 수집 제한에 걸린 항목이 있습니다. 다음 실행에서 이어서 처리됩니다.\n")


def main() -> None:
    if not os.environ.get("DART_API_KEYS"):
        print("[syncNewStocks] DART_API_KEYS 환경변수가 필요합니다.")
        sys.exit(1)

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = Path(os.environ["DARTLAB_DATA_DIR"]).resolve()
    dataDir.mkdir(parents=True, exist_ok=True)

    categories = _parseCategories(os.environ.get("NEW_STOCK_CATEGORIES", "finance,report,docs"))
    limit = int(os.environ.get("NEW_STOCK_LIMIT", "50"))

    print(f"[syncNewStocks] categories={categories} limit={limit if limit > 0 else 'unlimited'} dataDir={dataDir}")

    allCodes = _kindListCodes()
    remoteCodes = _remoteParquetCodes(categories)

    dist = Path("dist")
    dist.mkdir(exist_ok=True)

    summary: dict[str, Any] = {
        "kindListCount": len(allCodes),
        "categories": {},
        "capped": False,
    }

    started = time.time()
    for category in categories:
        from dartlab.core.dataConfig import DATA_RELEASES

        localDir = dataDir / DATA_RELEASES[category]["dir"]
        localDir.mkdir(parents=True, exist_ok=True)

        existingCodes = remoteCodes[category] | _localParquetCodes(category, dataDir)
        missing = [code for code in allCodes if code not in existingCodes]
        attempted = missing
        if limit > 0 and len(missing) > limit:
            attempted = missing[:limit]
            summary["capped"] = True

        changedPath = dist / f"changed_{category}.txt"
        before = _snapshotHashes(localDir)
        results: dict[str, dict[str, int]] = {}
        if attempted:
            print(f"[syncNewStocks] {category}: HF 누락 {len(missing)}개, 수집 {len(attempted)}개")
            results = _collectCategory(category, attempted)
        else:
            print(f"[syncNewStocks] {category}: 신규 누락 없음")

        newFiles, updatedFiles = _changedFiles(category, dataDir, before)
        changed = newFiles + updatedFiles
        changedPath.write_text("\n".join(changed), encoding="utf-8")

        rows = sum(item.get(category, 0) for item in results.values())
        summary["categories"][category] = {
            "missingRemoteCount": len(missing),
            "attemptedCount": len(attempted),
            "attemptedCodes": attempted,
            "newFileCount": len(newFiles),
            "updatedFileCount": len(updatedFiles),
            "changedFiles": changed,
            "rows": rows,
        }

    allChanged: list[str] = []
    for category in categories:
        changedFile = dist / f"changed_{category}.txt"
        allChanged.extend([line for line in changedFile.read_text(encoding="utf-8").splitlines() if line.strip()])
    (dist / "changed.txt").write_text("\n".join(allChanged), encoding="utf-8")

    summary["elapsedSeconds"] = round(time.time() - started, 1)
    _writeSummary(summary)
    print(f"[syncNewStocks] 완료: {json.dumps(summary, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
