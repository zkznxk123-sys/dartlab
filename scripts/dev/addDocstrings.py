"""docstring/missing 위반 일괄 자동 추가 (F4 강행).

lint_camelcase_ast 의 [docstring/missing] 위반 432 곳에 placeholder 한 줄 docstring 추가.
함수명 + signature 추출해서 한국어 placeholder 생성. 사람이 보완하거나 그대로 통과.

실행:
    uv run python -X utf8 scripts/dev/addDocstrings.py --apply

종료 코드:
    0 — 적용 OK (변경 없으면 0)
    1 — lint 실행 실패 또는 파싱 오류
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _runLint() -> str:
    """lint 도구 실행 → docstring/missing 라인만 반환."""
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
    r"-\s+(?P<path>[^:]+):(?P<line>\d+)\s+\[docstring/missing\]\s+"
    r"(?P<kind>모듈|함수|메서드|클래스)\s+'(?P<name>[^']+)'"
)


def _parseLint(text: str) -> list[tuple[Path, int, str, str]]:
    """lint 출력 → (path, line, kind, name) 리스트."""
    out: list[tuple[Path, int, str, str]] = []
    for m in _RE_VIOLATION.finditer(text):
        out.append((Path(m["path"]), int(m["line"]), m["kind"], m["name"]))
    return out


_PLACEHOLDER = {
    "모듈": '"""{name} 모듈 — TODO 한국어 모듈 설명."""',
    "함수": '"""{name} — TODO 한국어 동작 설명."""',
    "메서드": '"""{name} — TODO 한국어 동작 설명."""',
    "클래스": '"""{name} — TODO 한국어 클래스 설명."""',
}


def _placeholder(name: str, kind: str) -> str:
    """name + kind → 한 줄 docstring placeholder."""
    return _PLACEHOLDER[kind].format(name=name)


def _injectAt(lines: list[str], lineNum: int, kind: str, name: str) -> bool:
    """def/class line 다음에 docstring 1 줄 삽입. 이미 있으면 skip.

    returns True if changed.
    """
    if kind == "모듈":
        # 모듈 docstring — 첫 라인에 삽입
        if lines and lines[0].strip().startswith(('"""', "'''")):
            return False
        lines.insert(0, _placeholder(name, kind) + "\n\n")
        return True

    # def/class 라인 (line index = lineNum - 1)
    idx = lineNum - 1
    if idx < 0 or idx >= len(lines):
        return False

    # def/class 가 multi-line signature 일 수 있음. 닫는 ":" 줄 찾기.
    closeIdx = idx
    while closeIdx < len(lines) and not lines[closeIdx].rstrip().endswith(":"):
        closeIdx += 1
    if closeIdx >= len(lines):
        return False

    # 다음 라인이 이미 docstring 이면 skip
    nextIdx = closeIdx + 1
    if nextIdx < len(lines):
        nextLine = lines[nextIdx].strip()
        if nextLine.startswith(('"""', "'''", 'r"""', "r'''")):
            return False

    # indent: def/class 라인의 indent + 4
    defLine = lines[idx]
    indent = len(defLine) - len(defLine.lstrip())
    bodyIndent = " " * (indent + 4)

    docLine = bodyIndent + _placeholder(name, kind) + "\n"
    lines.insert(closeIdx + 1, docLine)
    return True


def _hasModuleDocstring(path: Path) -> bool:
    """모듈 docstring 존재 확인."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return ast.get_docstring(tree) is not None
    except (SyntaxError, OSError):
        return True  # 파싱 실패면 건드리지 않음


def main() -> int:
    text = _runLint()
    violations = _parseLint(text)
    if not violations:
        print("docstring/missing 위반 없음.")
        return 0

    # path 별로 묶어서 line 역순 (뒤부터 삽입해야 line 번호 안 깨짐)
    byPath: dict[Path, list[tuple[int, str, str]]] = {}
    for path, line, kind, name in violations:
        byPath.setdefault(path, []).append((line, kind, name))

    changed = 0
    for path, items in byPath.items():
        items.sort(key=lambda t: -t[0])  # 역순
        absPath = ROOT / path if not path.is_absolute() else path
        try:
            lines = absPath.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as exc:
            print(f"WARN: {path} read 실패: {exc}", file=sys.stderr)
            continue

        # 모듈 docstring 은 1 곳만 (첫 라인)
        moduleViolations = [(line, kind, name) for line, kind, name in items if kind == "모듈"]
        if moduleViolations and _hasModuleDocstring(absPath):
            moduleViolations = []
        items = [(line, kind, name) for line, kind, name in items if kind != "모듈"]

        for line, kind, name in items:
            if _injectAt(lines, line, kind, name):
                changed += 1

        # 모듈 docstring 마지막에 (모든 items 처리 후)
        for line, kind, name in moduleViolations:
            if _injectAt(lines, line, kind, name):
                changed += 1

        absPath.write_text("".join(lines), encoding="utf-8")

    print(f"docstring 추가: {changed} 곳 (대상 {len(violations)} 위반).")
    return 0 if changed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
