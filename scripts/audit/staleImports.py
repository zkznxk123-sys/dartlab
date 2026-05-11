"""stale top-level import lint — `from dartlab import X` / `import dartlab as Y` 잔존 검출.

F6 (PEP 562 lazy facade) 의 종료 조건은 src/ 내부에서 top-level dartlab 모듈 경유
import 가 0 인 것. lazy facade 로 빠진 후 어떤 모듈이 `from dartlab import Company`
하면 facade `_CallableModule.__getattr__` 재진입 → 정적 chain 차단 효과가 무효화.

정공법: 서브패키지 직접 import. `from dartlab.company import Company`,
`from dartlab.config import ...`, `from dartlab.providers.dart import OpenDart` 등.

검사 대상:
    src/dartlab/ 내부 모든 .py (자기 자신인 src/dartlab/__init__.py 제외).
    skills/ 같은 *.md 는 무시 (실제 import 가 아님).

스킬·문서 안 예시 코드는 사용자용 — 정상. 본 lint 의 관심은 패키지 내부.

실행::

    uv run python -X utf8 scripts/audit/staleImports.py            # 보고
    uv run python -X utf8 scripts/audit/staleImports.py --strict   # 위반 ≥ 1 → exit 2

종료 코드:
    0 — 잔존 0 (또는 --strict 미지정)
    2 — 잔존 ≥ 1 + --strict
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "dartlab"

# 잡고 싶은 패턴:
#   from dartlab import Company
#   from dartlab import Company, config
#   from dartlab import (Company, config)
#   import dartlab as _dl
#   import dartlab
# 단, `from dartlab.xxx import ...` (서브패키지 직접) 는 정상.
_RE_FROM_TOP = re.compile(r"^\s*from\s+dartlab\s+import\s+(.+?)(?:\s*#.*)?$", re.MULTILINE)
_RE_IMPORT_TOP = re.compile(r"^\s*import\s+dartlab(?:\s+as\s+\w+)?(?:\s*#.*)?\s*$", re.MULTILINE)

# 면제 — facade 본체 + 의도된 entry 모듈.
_EXEMPT_FILES: tuple[str, ...] = (
    "src/dartlab/__init__.py",  # facade 본체
    "src/dartlab/_aiEntries.py",  # F6.1 ask/templates/saveTemplate 본체
    "src/dartlab/server/__init__.py",  # server 가 dartlab 전체를 노출하는 facade
    "src/dartlab/api.py",  # 공개 API 단축 모듈 (필요 시 별도 정리)
)


def _normPath(p: Path) -> str:
    return p.relative_to(_REPO_ROOT).as_posix()


def _isExempt(file: Path) -> bool:
    rel = _normPath(file)
    return rel in _EXEMPT_FILES


def _findStale(file: Path) -> list[tuple[int, str]]:
    """파일 안 stale top-level dartlab import 위치/스니펫 반환."""
    try:
        source = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out: list[tuple[int, str]] = []
    for m in _RE_FROM_TOP.finditer(source):
        # 줄 번호 계산 (offset → line).
        line = source.count("\n", 0, m.start()) + 1
        names = m.group(1).strip()
        out.append((line, f"from dartlab import {names}"))
    for m in _RE_IMPORT_TOP.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        snippet = source[m.start() : m.end()].strip()
        out.append((line, snippet))
    return out


def _scan() -> dict[str, list[tuple[int, str]]]:
    """src/dartlab/ 전수. {파일 상대경로: [(line, snippet), ...]}."""
    results: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for f in _SRC.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        if _isExempt(f):
            continue
        for line, snippet in _findStale(f):
            results[_normPath(f)].append((line, snippet))
    return dict(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="잔존 ≥ 1 → exit 2")
    parser.add_argument("--quiet", action="store_true", help="violations 만 출력")
    args = parser.parse_args()

    results = _scan()
    total = sum(len(v) for v in results.values())

    if not args.quiet:
        print("=" * 72)
        print("stale top-level dartlab import lint")
        print("=" * 72)

    if results:
        # 면제 외 위반 모듈 별로 표시.
        for relPath in sorted(results):
            print(f"\n{relPath}")
            for line, snippet in results[relPath]:
                print(f"  L{line}  {snippet}")
        if not args.quiet:
            print(f"\n총 잔존: {total} 건 ({len(results)} 파일)")
            print("→ 서브패키지 직접 import 로 변환. 예: `from dartlab.company import Company`.")
    elif not args.quiet:
        print("\n잔존 0 건 OK — F6 종료 조건 충족.")

    if args.strict and total > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
