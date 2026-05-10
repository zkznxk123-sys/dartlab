"""var-snake 위반 일괄 자동 rename (F5 강행).

lint_camelcase_ast 의 [naming/var-snake] 위반 (module-level 변수) 을 camelCase 로 변환.
변수 정의 + 사용 사이트 (같은 파일 내) 동시 변경. 호출자 (다른 파일) 는 별도 grep+sed.

실행:
    uv run python -X utf8 scripts/dev/renameModuleVars.py

종료 코드:
    0 — 적용 OK
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _runLint() -> str:
    cmd = [
        sys.executable,
        "-X",
        "utf8",
        "scripts/dev/lint_camelcase_ast.py",
        "--all",
        "--strict",
        "--no-shim",
        "--no-baseline",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    return res.stdout


_RE_VIOLATION = re.compile(
    r"-\s+(?P<path>[^:]+):(?P<line>\d+)\s+\[naming/var-snake\]\s+모듈 변수\s+'(?P<name>[^']+)'.*?'(?P<new>[^']+)'"
)


def _parseLint(text: str) -> list[tuple[Path, str, str]]:
    """lint 출력 → (path, oldName, newName) 리스트."""
    out: list[tuple[Path, str, str]] = []
    for m in _RE_VIOLATION.finditer(text):
        out.append((Path(m["path"]), m["name"], m["new"]))
    return out


def _renameInFile(path: Path, mappings: list[tuple[str, str]]) -> bool:
    """파일 내에서 oldName → newName 일괄 치환 (whole-word). bool 변경 여부."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    orig = text
    for old, new in mappings:
        # whole word — \b\bold\b 형태. _ 시작 변수도 대응.
        # \b 는 word boundary — _ 는 word char 라 _xxx 의 _ 앞에 \b 있음.
        # `_xxx_yyy` 검색 시 다른 longer match 와 충돌 없도록 longer first 정렬.
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])"
        text = re.sub(pattern, new, text)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    text = _runLint()
    violations = _parseLint(text)
    if not violations:
        print("var-snake 위반 없음.")
        return 0

    # 정의 파일 별로 (oldName, newName) 모음
    byPath: dict[Path, list[tuple[str, str]]] = {}
    for path, oldName, newName in violations:
        byPath.setdefault(path, []).append((oldName, newName))

    # 모든 (oldName, newName) global 합집합 — 호출자도 일괄 변환
    allMappings = list({(o, n) for items in byPath.values() for o, n in items})
    # longer first (substring 충돌 방지)
    allMappings.sort(key=lambda t: -len(t[0]))

    changed = 0
    # 모든 .py 파일 (src/dartlab + tests)
    targets = list((ROOT / "src" / "dartlab").rglob("*.py")) + list((ROOT / "tests").rglob("*.py"))
    for fp in targets:
        if "__pycache__" in fp.parts:
            continue
        if _renameInFile(fp, allMappings):
            changed += 1

    print(f"rename 적용: {changed} 파일 (총 매핑 {len(allMappings)} 개).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
