"""parquet → Arrow IPC mirror 빌더.

Phase A 처방 — DATA_RELEASES 의 ``ipcMirror=True`` 카테고리에 대해
parquet 옆에 동일 데이터의 ``.arrow`` IPC 파일을 만든다. Phase D 의
``pl.read_ipc(memory_map=True)`` 진입점이 사용 — mmap 으로 OS page cache
가 캐시 역할 담당, application-level cache 부담 제거.

흐름:
  1. 환경변수 ``SYNC_CATEGORY`` (또는 ``--category``) 로 대상 카테고리 식별.
  2. ``DARTLAB_DATA_DIR`` (기본 ``./data``) 안 ``DATA_RELEASES[cat]["dir"]/*.parquet`` 스캔.
  3. 각 parquet 을 ``pl.read_parquet`` → ``df.write_ipc`` 로 ``.arrow`` 생성.
  4. mtime 비교 — parquet 이 더 새 것일 때만 재빌드 (idempotent).

IPC 포맷: zstd 압축. mmap 자체에 의한 demand-paging 효과는 OS 가 처리.

환경변수:
  SYNC_CATEGORY: finance / report (필수)
  DARTLAB_DATA_DIR: 데이터 저장 경로 (기본: ./data)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import polars as pl


def _shouldRebuild(parquetPath: Path, ipcPath: Path) -> bool:
    """parquet 이 더 새것이거나 ipc 부재면 재빌드."""
    if not ipcPath.exists():
        return True
    return parquetPath.stat().st_mtime > ipcPath.stat().st_mtime


def _changedParquets(category: str, parquetDir: Path) -> list[Path] | None:
    """``dist/changed_{cat}.txt`` 가 있으면 해당 parquet 만 변환 대상. 없으면 전체."""
    distDir = Path("dist")
    changedPath = distDir / f"changed_{category}.txt"
    if not changedPath.exists():
        return None
    names = [n.strip() for n in changedPath.read_text(encoding="utf-8").splitlines() if n.strip()]
    return [parquetDir / n for n in names if (parquetDir / n).exists() and n.endswith(".parquet")]


def _appendChangedArrow(category: str, arrowNames: list[str]) -> None:
    """변환된 ``.arrow`` 이름을 *기존* changed.txt 양쪽에 append.

    sync 단계가 changed.txt 의 owner — buildMirror 는 보조로 .arrow 만 추가.
    changed.txt 부재 시 buildMirror 가 새로 만들지 않는다 (단발 호출 환경에서
    의도치 않은 부작용 회피).
    """
    if not arrowNames:
        return
    distDir = Path("dist")
    if not distDir.exists():
        return
    for fname in (f"changed_{category}.txt", "changed.txt"):
        p = distDir / fname
        if not p.exists():
            continue
        existing = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        merged = existing + [n for n in arrowNames if n not in existing]
        p.write_text("\n".join(merged) + "\n", encoding="utf-8")


def buildMirror(category: str, dataDir: Path) -> int:
    """단일 카테고리의 parquet 디렉토리 → IPC mirror 생성. 변환된 파일 수 반환.

    ``dist/changed_{cat}.txt`` 존재 시 그 parquet 만 변환 (incremental). 없으면 전체
    디렉토리 mtime 검사 (full sweep).
    """
    from dartlab.core.dataConfig import DATA_RELEASES

    if category not in DATA_RELEASES:
        print(f"[buildIpcMirror] 알 수 없는 카테고리: {category}", file=sys.stderr)
        return 0

    spec = DATA_RELEASES[category]
    if not spec.get("ipcMirror"):
        print(f"[buildIpcMirror] {category} 는 ipcMirror=False — skip")
        return 0

    parquetDir = dataDir / spec["dir"]
    if not parquetDir.exists():
        print(f"[buildIpcMirror] {parquetDir} 부재 — skip")
        return 0

    changed = _changedParquets(category, parquetDir)
    targets = changed if changed is not None else sorted(parquetDir.glob("*.parquet"))

    converted = 0
    skipped = 0
    failed = 0
    convertedArrowNames: list[str] = []

    for parquet in targets:
        ipcPath = parquet.with_suffix(".arrow")
        if changed is None and not _shouldRebuild(parquet, ipcPath):
            skipped += 1
            continue

        try:
            df = pl.read_parquet(parquet)
            tmpIpc = ipcPath.with_name(f"{ipcPath.name}.tmp")
            df.write_ipc(tmpIpc, compression="zstd")
            tmpIpc.replace(ipcPath)
            converted += 1
            convertedArrowNames.append(ipcPath.name)
        except (pl.exceptions.ComputeError, OSError) as e:
            print(f"[buildIpcMirror] {parquet.name} 실패: {e}", file=sys.stderr)
            failed += 1

    _appendChangedArrow(category, convertedArrowNames)
    print(f"[buildIpcMirror] {category}: {converted} 변환 / {skipped} skip / {failed} 실패")
    return converted


def main() -> int:
    raw = os.environ.get("SYNC_CATEGORY") or os.environ.get("SYNC_CATEGORIES")
    if not raw:
        if len(sys.argv) > 1:
            raw = sys.argv[1]
        else:
            print("SYNC_CATEGORY 환경변수 또는 인자가 필요합니다.", file=sys.stderr)
            return 1

    categories = [c.strip() for c in raw.split(",") if c.strip()]
    if not categories:
        return 1

    dataDir = Path(os.environ.get("DARTLAB_DATA_DIR", "./data"))
    dataDir.mkdir(parents=True, exist_ok=True)

    total = 0
    for cat in categories:
        total += buildMirror(cat, dataDir)
    print(f"[buildIpcMirror] 총 {total} 변환")
    return 0


if __name__ == "__main__":
    sys.exit(main())
