from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


class _FakeCompany:
    stockCode = "005930"
    corpName = "삼성전자"

    def show(self, statement: str):
        assert statement == "BS"
        return pl.DataFrame(
            {
                "snakeId": [
                    "cash_and_cash_equivalents",
                    "current_assets",
                    "total_assets",
                    "total_liabilities",
                    "owners_of_parent_equity",
                ],
                "항목": ["현금및현금성자산", "유동자산", "자산총계", "부채총계", "지배주주지분"],
                "2025Q4": [
                    57_856_000_000_000,
                    247_680_000_000_000,
                    566_900_000_000_000,
                    130_600_000_000_000,
                    424_300_000_000_000,
                ],
            }
        )


class _FakePeerCompany:
    stockCode = "000660"
    corpName = "SK하이닉스"

    def show(self, statement: str):
        assert statement == "BS"
        return pl.DataFrame(
            {
                "snakeId": [
                    "cash_and_cash_equivalents",
                    "current_assets",
                    "total_assets",
                    "total_liabilities",
                    "owners_of_parent_equity",
                ],
                "항목": ["현금및현금성자산", "유동자산", "자산총계", "부채총계", "지배주주지분"],
                "2025Q4": [
                    10_000_000_000_000,
                    70_000_000_000_000,
                    176_000_000_000_000,
                    55_000_000_000_000,
                    120_000_000_000_000,
                ],
            }
        )


def _answer(events) -> str:
    return "".join(str(event.data.get("text") or "") for event in events if event.kind == "chunk")


def _done(events) -> dict:
    return [event for event in events if event.kind == "done"][-1].data


@pytest.mark.skip(
    reason=(
        "intent.py keyword routing 폐기 (SSOT P-revised, 2026-05-07) — kernel 은 "
        "mode==analyze 또는 LLM tool 호출만 분기. 'unknown_api_ref' 결과는 "
        "verifyAnswer 가 financialStatement apiRef 를 capability catalog 에서 "
        "찾지 못함. RunPython 패턴 + mock provider 로 재작성 필요 (별도 PR)."
    )
)
def test_ask_public_entry_financial_statement_uses_engine_call(monkeypatch) -> None:
    import dartlab.ai.tools.engineCall as engine_call_mod
    from dartlab.ai.kernel import ask

    monkeypatch.setattr(engine_call_mod, "_resolveCompany", lambda target: _FakeCompany())

    events = list(ask("삼성전자 재무상태표 확인", events=True))
    answer = _answer(events)
    done = _done(events)

    assert "삼성전자(005930)" in answer
    assert "재무상태표 (2025Q4)" in answer
    assert "57.9조원" in answer
    assert "5.7856e13" not in answer
    assert done["responseMeta"]["responseStatus"] == "ok"
    assert any(ref["kind"] == "tableRef" for ref in done["refs"])
    assert any(ref["kind"] == "valueRef" for ref in done["refs"])
    assert any(ref["kind"] == "dateRef" for ref in done["refs"])


def test_ask_public_entry_compares_two_financial_statements(monkeypatch) -> None:
    import dartlab.ai.tools.engineCall as engine_call_mod
    from dartlab.ai.kernel import ask

    def fake_resolve(target: str):
        return _FakePeerCompany() if "하이닉스" in target else _FakeCompany()

    monkeypatch.setattr(engine_call_mod, "_resolveCompany", fake_resolve)

    events = list(ask("삼성전자와 SK하이닉스 재무상태표 비교", events=True))
    answer = _answer(events)
    done = _done(events)

    assert "삼성전자(005930)와 SK하이닉스(000660)" in answer
    assert "자산총계" in answer
    assert "약 3.2배" in answer
    assert done["responseMeta"]["responseStatus"] == "ok"


def test_ask_growth_scan_returns_candidate_table(monkeypatch) -> None:
    import dartlab.ai.workbench.heuristic as heuristic_mod
    from dartlab.ai.contracts import Ref
    from dartlab.ai.kernel import ask
    from dartlab.ai.tools.types import ToolResult

    monkeypatch.setattr(
        heuristic_mod,
        "engineCall",
        lambda plan: ToolResult(
            True,
            "growth scan 후보 1개",
            refs=[Ref(id="table:scan:growth:top", kind="tableRef", title="growth top")],
            data={
                "markdown": '`dartlab.scan("growth")`로 2,116개 기업의 성장성 스캔을 확인했습니다.\n\n| 순위 | 기업 |\n|---:|---|\n| 1 | 하나투어(039130) |'
            },
        ),
    )

    events = list(ask("요즘 성장하는 회사는?", events=True))
    answer = _answer(events)

    assert "성장성 스캔" in answer
    assert "하나투어(039130)" in answer


def test_runask_is_not_public_kernel_entry() -> None:
    import dartlab.ai.kernel as kernel

    assert not hasattr(kernel, "runAsk")


def test_ask_missing_company_returns_actionable_failure(monkeypatch) -> None:
    import dartlab.ai.tools.engineCall as engine_call_mod
    from dartlab.ai.kernel import ask

    monkeypatch.setattr(engine_call_mod, "_resolveCompany", lambda target: None)

    answer = ask("재무상태표 확인", stream=False)

    assert "종목을 먼저 특정" in answer
    assert "삼성전자 재무상태표 확인" in answer
