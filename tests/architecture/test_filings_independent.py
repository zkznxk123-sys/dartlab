"""filings 독립성 가드 — providers/scan/dataLoader import 0 강제.

룰 (plan snazzy-wibbling-origami "독립성 경계" SSOT):
- ``src/dartlab/filings/`` 는 옛 providers 와 무관한 독립 다시장 패키지.
- 의존 허용: ``dartlab.config`` + 서드파티 (polars/lxml/huggingface_hub).
- 의존 금지: ``dartlab.providers`` · ``dartlab.scan`` · ``dartlab.core.dataLoader`` ·
  ``dartlab.core.dataConfig``.
- → providers 삭제·core dataLoader 변경이 filings 를 깨뜨리지 못함 (providers 완전
  폐기 가능한 새 기반).

런타임 sys.modules 가 아니라 **정적 import 분석** — 부모 ``dartlab/__init__`` 의 eager
load (scan/dataLoader) 와 filings 자체 의존을 구분.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "dartlab"
FILINGS = ROOT / "filings"
FORBIDDEN = (
    "dartlab.providers",
    "dartlab.scan",
    "dartlab.core.dataLoader",
    "dartlab.core.dataConfig",
)


def _assertRealSourceRoot() -> None:
    assert FILINGS.exists(), f"filings source root not found: {FILINGS}"
    assert any(FILINGS.rglob("*.py")), f"filings has no Python files: {FILINGS}"


def test_filings_independent() -> None:
    """filings 자체 코드가 providers/scan/dataLoader 를 import 하지 않음."""
    _assertRealSourceRoot()
    violations: list[str] = []
    for pyFile in FILINGS.rglob("*.py"):
        try:
            tree = ast.parse(pyFile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for n in names:
                for forbidden in FORBIDDEN:
                    if n == forbidden or n.startswith(f"{forbidden}."):
                        rel = pyFile.relative_to(ROOT.parent.parent)
                        violations.append(f"{rel}:{node.lineno}: {n}")
    assert not violations, "filings 독립성 위반 (providers/scan/dataLoader import):\n" + "\n".join(violations)
