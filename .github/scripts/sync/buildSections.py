"""sync stage 의 sections artifact 빌더 CLI entry.

plan snazzy-wibbling-origami PR-1d. docs.parquet 으로부터 *period-sharded sections
artifact* 를 빌드 + HF push 준비. 일일 sync 흐름에 통합:
    docs 수집 → 변경 종목 list → buildSections (본 entry) → uploadData

사용법:
    # 변경 종목만 (dist/changed.txt 또는 dist/changed_docs.txt 기반)
    python .github/scripts/sync/buildSections.py

    # 특정 종목 list
    python .github/scripts/sync/buildSections.py --codes 005930,000660

    # 전체 종목 재빌드 (1 회 batch — 약 종목당 18s)
    python .github/scripts/sync/buildSections.py --all

환경변수:
    DARTLAB_DATA_DIR: 데이터 저장 경로 (기본: ./data)
    DARTLAB_SECTIONS_NO_MIXED: 자동 set (sectionsBuilder 가 forceRaw context 로 제어)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _resolveChangedCodes() -> list[str]:
    """dist/changed_docs.txt 또는 dist/changed.txt 에서 변경된 docs 종목 추출."""
    candidates = [Path("dist/changed_docs.txt"), Path("dist/changed.txt")]
    for p in candidates:
        if not p.exists():
            continue
        names = [n.strip() for n in p.read_text(encoding="utf-8").splitlines() if n.strip()]
        # changed.txt 양식: "005930.parquet" — stem 만 추출
        codes = [Path(n).stem for n in names]
        # 6 자리 숫자 stockCode 만
        return [c for c in codes if c.isdigit() and len(c) == 6]
    return []


def _resolveAllCodes(dataDir: str) -> list[str]:
    """data/dart/docs/*.parquet 에서 모든 종목코드 list."""
    docsDir = Path(dataDir) / "dart" / "docs"
    if not docsDir.exists():
        return []
    return sorted(p.stem for p in docsDir.glob("*.parquet") if p.stem.isdigit() and len(p.stem) == 6)


def _writeChangedSections(codes: list[str]) -> None:
    """uploadData.py 가 sections category 업로드 시 참고할 changed list.

    파일 양식 — 종목별 sections 디렉터리의 모든 period 파일 경로 (HF path).
    예: ``005930/2025.parquet`` ``005930/2025Q3.parquet`` ...
    """
    from dartlab.providers.dart.docs.sections.sectionsStorage import sectionsDir

    out_lines: list[str] = []
    for code in codes:
        d = sectionsDir(code)
        if not d.exists():
            continue
        for p in sorted(d.glob("*.parquet")):
            out_lines.append(f"{code}/{p.name}")

    distDir = Path("dist")
    distDir.mkdir(exist_ok=True)
    target = distDir / "changed_sections.txt"
    target.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(f"[buildSections] dist/changed_sections.txt: {len(out_lines)} period files")


def main() -> int:
    parser = argparse.ArgumentParser(description="sections SSOT artifact 빌더")
    parser.add_argument("--codes", help="쉼표 구분 종목 코드 list (예: 005930,000660)")
    parser.add_argument("--all", action="store_true", help="data/dart/docs/ 의 모든 종목 빌드")
    parser.add_argument("--changed", action="store_true", help="dist/changed_docs.txt 또는 dist/changed.txt 기반")
    parser.add_argument(
        "--mixed-fallback", action="store_true", help="옛 mixed cache 사용 (forceRaw=False, 빠르지만 신 룰 미반영)"
    )
    args = parser.parse_args()

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.all:
        codes = _resolveAllCodes(dataDir)
    else:
        # default: changed 모드 (dist/changed*.txt)
        codes = _resolveChangedCodes()

    if not codes:
        print("[buildSections] 빌드 대상 0 종목 — 종료")
        _writeChangedSections([])
        return 0

    print(f"[buildSections] 대상 {len(codes)} 종목 — forceRaw={not args.mixed_fallback}")
    from dartlab.providers.dart.docs.sections.sectionsBuilder import buildSectionsArtifact

    forceRaw = not args.mixed_fallback
    successCount = 0
    failedCodes: list[str] = []
    t0 = time.perf_counter()
    for i, code in enumerate(codes, 1):
        tStart = time.perf_counter()
        try:
            result = buildSectionsArtifact(code, forceRaw=forceRaw)
            if result:
                successCount += 1
                rows = sum(result.values())
                print(
                    f"  [{i}/{len(codes)}] {code}: {len(result)} periods, {rows} rows ({time.perf_counter() - tStart:.1f}s)"
                )
            else:
                failedCodes.append(code)
                print(f"  [{i}/{len(codes)}] {code}: 빈 결과 — skip")
        except Exception as exc:
            failedCodes.append(code)
            print(f"  [{i}/{len(codes)}] {code}: 실패 ({exc!r})")

    elapsed = time.perf_counter() - t0
    print(f"[buildSections] 완료: 성공={successCount}/{len(codes)} 실패={len(failedCodes)} (총 {elapsed:.1f}s)")
    if failedCodes:
        print(f"[buildSections] 실패 종목: {','.join(failedCodes[:20])}{'...' if len(failedCodes) > 20 else ''}")

    _writeChangedSections([c for c in codes if c not in failedCodes])
    return 0 if successCount > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
