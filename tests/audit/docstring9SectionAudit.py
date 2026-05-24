"""9 섹션 docstring 통과 측정 audit (T10-4 측정 도구).

dartlab 의 public API + 신규 모듈 함수 의 docstring 이 9 섹션 표준 (Capabilities
/ Args / Returns / Example / Guide / SeeAlso / Requires / AIContext + 자유 1 섹션)
중 *최소 5 섹션* 충족 여부 측정.

baseline: tests/audit/_baselines/docstring9Section.json

실행::

    uv run python -X utf8 tests/audit/docstring9SectionAudit.py
    uv run python -X utf8 tests/audit/docstring9SectionAudit.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "src" / "dartlab"
BASELINE_FILE = REPO_ROOT / "tests" / "audit" / "_baselines" / "docstring9Section.json"

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Capabilities",
    "Args",
    "Returns",
    "Example",
    "Guide",
    "SeeAlso",
    "Requires",
    "AIContext",
    "Raises",  # 또는 LLM Specifications
)
_MIN_SECTIONS = 5  # 9 섹션 중 최소 5 충족


def _checkDocstring(doc: str) -> int:
    """docstring 안 섹션 카운트."""
    if not doc:
        return 0
    return sum(1 for s in _REQUIRED_SECTIONS if f"{s}:" in doc or f"\n{s}\n" in doc or f"{s}::" in doc)


def auditFile(filePath: Path) -> list[dict]:
    """파일 안 public 함수/class 의 docstring 섹션 검사."""
    try:
        tree = ast.parse(filePath.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        doc = ast.get_docstring(node) or ""
        sections = _checkDocstring(doc)
        out.append(
            {
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "sections": sections,
                "passes": sections >= _MIN_SECTIONS,
            }
        )
    return out


def auditAll() -> dict:
    """src/dartlab 전체 public 함수/class 의 docstring 섹션 통과율."""
    results: list[dict] = []
    for pyFile in SRC.rglob("*.py"):
        if "__pycache__" in pyFile.parts:
            continue
        rel = str(pyFile.relative_to(REPO_ROOT)).replace("\\", "/")
        for item in auditFile(pyFile):
            item["file"] = rel
            results.append(item)

    total = len(results)
    passed = sum(1 for r in results if r["passes"])
    passRate = round((passed / total * 100) if total > 0 else 0, 2)
    return {
        "total": total,
        "passed": passed,
        "passRate": passRate,
        "byFile": {},  # 향후 파일별 통과율
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="9 섹션 docstring audit (T10-4)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="passRate < 80 시 exit 2")
    args = parser.parse_args()

    result = auditAll()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"[docstring9] public 함수/class {result['total']:,} 중 {result['passed']:,} 통과 ({result['passRate']:.2f} percent)"
        )

    if args.strict and result["passRate"] < 80:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
