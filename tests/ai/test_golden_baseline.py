"""P0 골든 baseline — 휴리스틱 시대 ask() 출력 캡처/회귀.

골든 셋이 비어 있으면 skip. 실제 캡처는 별도 스크립트로:
    uv run python -X utf8 scripts/dev/captureGoldenBaseline.py

P1 에서 LLM 작업대로 갈아끼운 뒤 본 baseline 과 비교 — diff 가 의미 있는 회귀인지 확인.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_BASELINE_PATH = Path(__file__).parent / "golden" / "baseline.json"


def _loadBaseline() -> dict:
    return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_baseline_file_exists() -> None:
    assert _BASELINE_PATH.exists()


@pytest.mark.unit
def test_baseline_schema_valid() -> None:
    data = _loadBaseline()
    assert "scenarios" in data
    assert isinstance(data["scenarios"], list)


@pytest.mark.unit
def test_baseline_scenarios_have_question_and_refs() -> None:
    data = _loadBaseline()
    if not data["scenarios"]:
        pytest.skip("baseline empty — capture pending (P0 후반)")
    for sc in data["scenarios"]:
        assert "question" in sc
        assert "expected" in sc
        assert "refs" in sc["expected"]
