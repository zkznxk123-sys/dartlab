"""Over-split 폴더 인벤토리 — 과분할 통합 룰 (operation.code 룰 1).

≤150 LoC sub-folder + sub-folder 가진 경우 = parent 단일 .py 흡수 후보.
providers 의 `commit 06f8be355` "over_split 5→0" 패턴.

실행:
    uv run python -X utf8 scripts/audit/overSplitInventory.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"


def main() -> int:
    rows: list[tuple[str, int, int, int, list[str]]] = []
    for d in ROOT.rglob("*"):
        if not d.is_dir() or "__pycache__" in d.parts:
            continue
        directFiles = [p for p in d.glob("*.py") if not p.name.startswith("_generated")]
        if not directFiles:
            continue
        directLoc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in directFiles)
        subFolders = [s for s in d.iterdir() if s.is_dir() and "__pycache__" not in s.parts]
        if directLoc <= 150 and not subFolders:
            # leaf folder with <=150 LoC = over-split candidate
            rel = d.relative_to(ROOT).as_posix()
            names = [p.name for p in directFiles]
            rows.append((rel, directLoc, len(directFiles), 0, names))
        elif directLoc <= 100 and subFolders:
            # intermediate folder with thin parent but with subfolders
            rel = d.relative_to(ROOT).as_posix()
            names = [p.name for p in directFiles]
            rows.append((rel, directLoc, len(directFiles), len(subFolders), names))

    print(f"Total candidates: {len(rows)}")
    print()
    print("Leaf over-split (no subfolders, <=150 LoC):")
    leaves = [r for r in rows if r[3] == 0]
    for path, loc, fc, _, names in sorted(leaves, key=lambda x: x[1])[:30]:
        print(f"  {loc:>4} LoC · {fc} files  {path}")
        print(f"         {names}")
    print()
    print("Intermediate thin parents (have subfolders, <=100 LoC):")
    intermediates = [r for r in rows if r[3] > 0]
    for path, loc, fc, sf, names in sorted(intermediates, key=lambda x: x[1])[:30]:
        print(f"  {loc:>4} LoC · {fc} files · {sf} subs  {path}")
        print(f"         {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
