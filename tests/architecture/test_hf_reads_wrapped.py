"""HF read 호출은 전부 core.hfRetry.retryHfCall 경유 — rate-limit(429) 회귀 가드.

산재했던 unwrapped ``snapshot_download`` / ``hf_hub_download`` (각자 다른/없는 retry)이
HF 429 반복 실패의 한 축이었다. 이제 모든 HF read 는 단일 retry SSOT(``retryHfCall``)로
수렴한다 — 즉 ``retryHfCall(snapshot_download, ...)`` 처럼 *콜러블 인자*로 넘겨야 하며,
src 안에 이 두 함수를 *직접 호출*(Call)하는 노드가 0 이어야 한다.

새 HF read 를 unwrapped 로 추가하면 본 테스트가 PR 단계에서 차단한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"

# retryHfCall 로 감싸야 하는 HF read 함수 (직접 Call 금지 — 콜러블 인자로만 허용).
_GUARDED = {"snapshot_download", "hf_hub_download"}


def _srcFiles() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _directCalls(tree: ast.Module) -> list[str]:
    """guarded 함수의 *직접 호출*(Call) 노드만 수집. retryHfCall 인자(Name)는 제외."""
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
        if name in _GUARDED:
            hits.append(f"{name}@L{node.lineno}")
    return hits


def test_no_unwrapped_hf_reads() -> None:
    """src 전체에서 snapshot_download/hf_hub_download 직접 호출 0 (retryHfCall 경유 강제)."""
    violations: dict[str, list[str]] = {}
    for path in _srcFiles():
        hits = _directCalls(ast.parse(path.read_text(encoding="utf-8")))
        if hits:
            violations[str(path.relative_to(ROOT))] = hits

    assert not violations, (
        "unwrapped HF read 발견 — retryHfCall(core.hfRetry) 로 감싸시오 "
        f"(예: retryHfCall(snapshot_download, ...)). 위반: {violations}"
    )
