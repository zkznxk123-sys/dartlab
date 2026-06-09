"""ai/tools 재무 추출 단일 SSOT census — facade 추출은 companyMetrics.py 한 곳만.

손코딩 도구가 라이브러리 verb/단일 헬퍼를 재구현하지 않게 강제 (MCP 도구 thin 원칙,
runtime.mcp "도구 설계 원칙" SSOT). 새 도구가 finance 파사드 추출 `x.panel("IS"/"BS"/…)` 를
직접 부르면 fail — `ai/tools/companyMetrics.companyMetrics` 재사용을 강제한다.

AST 기반(실제 Call 노드만) — docstring/주석 안의 예시 문자열은 무시한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_TOOLS_DIR = Path(__file__).resolve().parents[2] / "src" / "dartlab" / "ai" / "tools"
_SSOT = "companyMetrics.py"  # 유일 허용 추출 지점
_FACADE_TOPICS = {"IS", "BS", "CF", "CIS", "SCE"}  # 대문자 = finance 파사드


def _facadeExtractionLines(tree: ast.AST) -> list[int]:
    """`<obj>.panel("IS"|"BS"|…)` 형태 실제 호출(Call) 라인 — 문자열 리터럴 인자만."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "panel" or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value in _FACADE_TOPICS:
            lines.append(node.lineno)
    return lines


def test_finance_facade_extraction_single_point() -> None:
    """ai/tools 에서 finance 파사드 추출은 companyMetrics.py 한 곳만."""
    offenders: list[str] = []
    for path in sorted(_TOOLS_DIR.glob("*.py")):
        if path.name == _SSOT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line in _facadeExtractionLines(tree):
            offenders.append(f"{path.name}:{line}")
    assert not offenders, (
        '재무 facade 추출 `panel("IS"/"BS"/…)` 은 companyMetrics.py 한 곳만 허용 — '
        "새 도구는 companyMetrics.companyMetrics 재사용:\n  " + "\n  ".join(offenders)
    )
