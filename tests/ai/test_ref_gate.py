"""회귀 가드 — GATE 가 ref 없는 숫자/날짜 답을 차단한다."""

from __future__ import annotations

import pytest

from dartlab.ai.workbench.gate import runGate
from dartlab.ai.workbench.state import WorkbenchState


@pytest.mark.unit
def test_gate_blocks_numbers_without_value_refs() -> None:
    state = WorkbenchState(question="test")
    state.answerText = "삼성전자 매출은 300조원이고 영업이익은 50조원이다."
    state.refs = []  # ref 0
    list(runGate(state))
    assert state.gateBlocked is True
    assert "unsupported_numeric_claim" in state.gateIssues


@pytest.mark.unit
def test_gate_passes_when_value_refs_present() -> None:
    from dartlab.ai.contracts import Ref

    state = WorkbenchState(question="test")
    state.answerText = "매출 300조원"
    state.refs = [Ref(id="value:revenue", kind="valueRef", title="revenue", source="run_python", payload={})]
    list(runGate(state))
    assert state.gateBlocked is False


@pytest.mark.unit
def test_gate_passes_when_no_numbers_or_dates() -> None:
    state = WorkbenchState(question="test")
    state.answerText = "분석을 위해 추가 정보가 필요합니다."
    state.refs = []
    list(runGate(state))
    assert state.gateBlocked is False


@pytest.mark.unit
def test_gate_emits_gate_result_event() -> None:
    state = WorkbenchState(question="test")
    state.answerText = "100원"
    events = list(runGate(state))
    kinds = [e.kind for e in events]
    assert "pass_enter" in kinds
    assert "gate_result" in kinds
    assert "pass_exit" in kinds
