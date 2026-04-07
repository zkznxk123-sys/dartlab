"""Sentinel — calc 함수 작성 패턴 AST lint.

회귀 차단:
- (K3) calc 함수가 select 결과의 row 를 `row["YYYYQN"]` 직접 literal 로 read 금지.
  Plan v4 Layer A 후 annual 컬럼 노출되므로 calc 가 분기 literal 사용은 함정.
  헬퍼(annualColsFromPeriods/getFlowValue) 경유 강제.

- (K2) calc 함수의 return dict literal 에서 `... or 0` 금지.
  None 결손과 진짜 0 구분 손실. 분모 가드는 코드 주석으로 표시.

대상 디렉토리: src/dartlab/analysis/, src/dartlab/credit/, src/dartlab/review/narrative.py
화이트리스트: tests/, _reference/, experiments/
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parent.parent / "src" / "dartlab"

_TARGET_DIRS = [
    _ROOT / "analysis" / "financial",
    _ROOT / "credit",
]
_TARGET_FILES = [
    _ROOT / "review" / "narrative.py",
]

_Q4_LITERAL_RE = re.compile(r"^[12]\d{3}Q[1-4]$")


def _collectPyFiles() -> list[Path]:
    files: list[Path] = []
    for d in _TARGET_DIRS:
        if d.exists():
            files.extend(p for p in d.rglob("*.py") if "_reference" not in p.parts and "experiments" not in p.parts)
    files.extend(f for f in _TARGET_FILES if f.exists())
    return files


def test_no_q4_literal_in_subscript():
    """`row["2025Q4"]` 또는 `data.get("2025Q4")` 같은 literal 사용 금지.

    Plan v4 Layer A 후 분기 컬럼 직접 literal read 는 함정. annualColsFromPeriods
    경유로 동적 컬럼명 사용 강제.
    """
    violations: list[str] = []
    for path in _collectPyFiles():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            # Subscript: row["2025Q4"]
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                if _Q4_LITERAL_RE.match(node.slice.value):
                    violations.append(f"{path.name}:{node.lineno} subscript {node.slice.value!r}")
            # Call: data.get("2025Q4") / row.get("2025Q4")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and _Q4_LITERAL_RE.match(node.args[0].value)
            ):
                violations.append(f"{path.name}:{node.lineno} get({node.args[0].value!r})")

    assert not violations, "calc 함수 분기 literal read 금지 (annual 컬럼 자동 노출):\n" + "\n".join(violations)


def test_no_or_zero_in_return_dict():
    """calc 함수의 return dict literal 에서 `or 0` 금지.

    None 결손과 진짜 0 구분 손실. 결과 dict 노출 위치만 검증.
    분모 가드용 `or 1`, `or 0.000001`, `or 1e-6` 등은 무관.
    화이트리스트: 변수 할당 라인 끝 주석 `# noqa: zero-guard`
    """
    violations: list[str] = []

    def _isOrZero(node: ast.expr) -> bool:
        """`<expr> or 0` 또는 `<expr> or 0.0` 인지 판별."""
        if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
            return False
        if len(node.values) < 2:
            return False
        last = node.values[-1]
        if isinstance(last, ast.Constant) and last.value in (0, 0.0):
            return True
        return False

    for path in _collectPyFiles():
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        srcLines = source.splitlines()

        for node in ast.walk(tree):
            # Return dict literal
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                for v in node.value.values:
                    if _isOrZero(v):
                        # 화이트리스트 주석 검사 (라인 끝 # noqa: zero-guard)
                        line = srcLines[v.lineno - 1] if v.lineno <= len(srcLines) else ""
                        if "noqa: zero-guard" not in line:
                            violations.append(f"{path.name}:{v.lineno} return dict 의 `or 0`")

    assert not violations, (
        "calc 함수 return dict 의 `or 0` 금지 (None 결손 보존):\n" + "\n".join(violations) +
        "\n\n분모 가드면 라인 끝에 `# noqa: zero-guard` 주석 추가."
    )
