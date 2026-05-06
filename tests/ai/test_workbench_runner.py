"""buildContextSummary — ref payload 핵심 필드 LLM 컨텍스트 노출 검증."""

from __future__ import annotations

import pytest

from dartlab.ai.contracts import Ref
from dartlab.ai.workbench.runner import buildContextSummary
from dartlab.ai.workbench.state import WorkbenchState


def _make_state(refs: list[Ref]) -> WorkbenchState:
    state = WorkbenchState(question="삼성전자 BS 자산총계")
    state.refs.extend(refs)
    return state


@pytest.mark.unit
def test_buildContextSummary_노출_valueRef_payload() -> None:
    """valueRef.payload 의 한국어 item + 값 + period 가 출력 텍스트에 포함되어야 함."""
    state = _make_state(
        [
            Ref(
                id="value:005930:BS:2025Q4:total_assets",
                kind="valueRef",
                title="자산총계 2025Q4",
                source="table:005930:BS:2025Q4",
                payload={
                    "snakeId": "total_assets",
                    "item": "자산총계",
                    "period": "2025Q4",
                    "value": 514531000000,
                    "formatted": "514조 5,310억",
                },
            )
        ]
    )

    summary = buildContextSummary(state)

    assert "자산총계" in summary
    assert "514조 5,310억" in summary
    assert "2025Q4" in summary
    assert "valueRef" in summary


@pytest.mark.unit
def test_buildContextSummary_kind별_분류() -> None:
    """valueRef·tableRef·dateRef 가 각각 별도 섹션으로 분류·카운트 표시되어야 함."""
    refs = [
        Ref(
            id="t1",
            kind="tableRef",
            title="BS",
            source="",
            payload={"label": "재무상태표", "latestPeriod": "2025Q4", "rowCount": 95},
        ),
        Ref(
            id="v1",
            kind="valueRef",
            title="자산총계",
            source="t1",
            payload={"item": "자산총계", "period": "2025Q4", "value": 1, "formatted": "1원"},
        ),
        Ref(
            id="v2",
            kind="valueRef",
            title="부채총계",
            source="t1",
            payload={"item": "부채총계", "period": "2025Q4", "value": 2, "formatted": "2원"},
        ),
        Ref(
            id="v3",
            kind="valueRef",
            title="자본총계",
            source="t1",
            payload={"item": "자본총계", "period": "2025Q4", "value": 3, "formatted": "3원"},
        ),
        Ref(id="d1", kind="dateRef", title="기준시점", source="t1", payload={"period": "2025Q4"}),
    ]

    summary = buildContextSummary(_make_state(refs))

    assert "## valueRef (3개" in summary
    assert "## tableRef (1개" in summary
    assert "## dateRef (1개" in summary
    assert "재무상태표" in summary
    assert "자본총계" in summary


@pytest.mark.unit
def test_buildContextSummary_token_cap() -> None:
    """valueRef 50 개 추가 시 최근 20 개만 노출 (max_count cap)."""
    refs = [
        Ref(
            id=f"value:test:{i}",
            kind="valueRef",
            title=f"item_{i}",
            source="t1",
            payload={"item": f"항목{i}", "period": "2025Q4", "value": i, "formatted": f"{i}원"},
        )
        for i in range(50)
    ]

    summary = buildContextSummary(_make_state(refs))

    assert "## valueRef (50개, 최근 20개 노출)" in summary
    # 마지막 20 개 (30~49) 만 노출 — 첫 항목 (0~29) 은 제외
    assert "항목49" in summary
    assert "항목30" in summary
    assert "항목29" not in summary
    assert "항목0 " not in summary  # 공백 포함해 부분일치 방지
