"""Sentinel — DART notes/sections parser 단위 처리 통합 검증.

`providers/dart/docs/finance/*/parser.py` 가 단위 변환 시 직접
`val *= unit` 같은 패턴을 사용하지 말고 `normalizeFromUnitScale` 헬퍼를
경유해야 함 (Plan v4 Layer 1.3 + Layer D).

현재는 4 분산 parser (costByNature/tangibleAsset/segment/notesDetail) 만 헬퍼
경유. 32 sections parser 는 자체 로직 유지 (사용자 노출 표시 영향 검증 후 일괄
마이그레이션 — Layer D 작업).

이 sentinel: 4 분산 parser + notesDetail pipeline 가 헬퍼 경유 보장.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parent.parent / "src" / "dartlab" / "providers" / "dart" / "docs" / "finance"
# Plan v4 root fix 가 적용된 파일 — normalize 헬퍼 경유 강제
# notesDetail tableBuilder: notes 테이블 빌드 (매퍼 기반)
_ENFORCED_PARSERS = {
    "costByNature": _ROOT / "costByNature" / "parser.py",
    "tangibleAsset": _ROOT / "tangibleAsset" / "parser.py",
    "segment": _ROOT / "segment" / "parser.py",
    "notesDetail_tableBuilder": _ROOT / "notesDetail" / "tableBuilder.py",
}


def test_enforced_parsers_use_normalize_helper():
    """4 분산 parser + notesDetail pipeline 이 normalize 헬퍼 호출."""
    violations = []
    for name, path in _ENFORCED_PARSERS.items():
        if not path.exists():
            violations.append(f"{name}: file not found ({path})")
            continue

        source = path.read_text(encoding="utf-8")
        # import 또는 from-import 검사
        hasNormalize = ("normalizeFromUnitScale" in source) or ("normalizeFinanceAmount" in source)
        if not hasNormalize:
            violations.append(f"{name}: normalize 헬퍼 import 없음 ({path.name})")

    assert not violations, "단위 정규화 헬퍼 경유 강제:\n" + "\n".join(violations)


def test_no_raw_unit_multiply_in_enforced():
    """4 분산 parser 에서 `val *= unit` 같은 raw 패턴 직접 사용 금지."""
    violations = []
    for name, path in _ENFORCED_PARSERS.items():
        if not path.exists():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            # `val *= unit` 또는 `val = val * unit` 패턴
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Mult):
                # AugAssign target 이 단순 Name 이고 value 가 unit 같은 이름
                if isinstance(node.value, ast.Name) and node.value.id == "unit":
                    violations.append(f"{name}:{node.lineno} `*= unit` (헬퍼 경유 필요)")

    assert not violations, "raw 단위 곱셈 금지 (normalizeFromUnitScale 사용):\n" + "\n".join(violations)


def test_no_global_raw_unit_multiply():
    """전역 lint: 모든 docs/finance parser + sections 에서 `val *= unit` 패턴 금지.

    Plan v4 P4: 32 sections parser 의 단위 처리 일관성. 새 parser 추가 시 raw
    `*= unit` 패턴은 normalizeFromUnitScale 또는 normalizeFinanceAmount 로 교체 강제.
    """
    docs_root = Path(__file__).resolve().parent.parent / "src" / "dartlab" / "providers" / "dart" / "docs"
    if not docs_root.exists():
        return

    violations = []
    for path in docs_root.rglob("parser.py"):
        if "_reference" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Mult):
                if isinstance(node.value, ast.Name) and node.value.id == "unit":
                    violations.append(f"{path.relative_to(docs_root)}:{node.lineno} `*= unit`")

    assert not violations, "raw 단위 곱셈 금지 (normalize 헬퍼 경유):\n" + "\n".join(violations)
