"""dpoPairs DPO preference 추출 단위 — 마스터 플랜 v2 트랙 8 PR-T2.

passed / failed trace pair → DPO {prompt, chosen, rejected}. ML 의존성 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dartlab.ai.training.dpoPairs import buildDpoDataset, extractDpoPairs

pytestmark = pytest.mark.unit


def _mkTrace(question: str, answer: str, *, tools: list[str] | None = None, withError: bool = False) -> dict:
    events: list[dict] = []
    if tools:
        for tool in tools:
            events.append({"kind": "tool_start", "data": {"tool": tool, "input": {}}})
            events.append({"kind": "tool_result", "data": {"tool": tool, "result": {"ok": True}}})
    if withError:
        events.append({"kind": "error", "data": {"error": "RuntimeError"}})
    if answer:
        for i in range(0, len(answer), 10):
            events.append({"kind": "chunk", "data": {"text": answer[i : i + 10]}})
    events.append({"kind": "done", "data": {}})
    return {
        "sessionId": f"s-{question[:8]}-{answer[:8]}",
        "question": question,
        "events": events,
    }


def test_extractDpoPairs_basic_pair() -> None:
    """같은 질문에 passed (chosen) + failed (rejected) → pair 1 건."""
    chosen_answer = "삼성전자 ROE 는 8.94% 입니다. 정상 범위 내."
    rejected_answer = "삼성전자 ROE 는 알 수 없습니다."
    traces = [
        _mkTrace("ROE", chosen_answer, tools=["EngineCall"]),  # passed
        _mkTrace("ROE", rejected_answer, withError=True),  # rejected
    ]
    pairs = extractDpoPairs(traces, minAnswerLen=10)
    assert len(pairs) == 1
    assert pairs[0]["prompt"] == "ROE"
    assert pairs[0]["chosen"] == chosen_answer
    assert pairs[0]["rejected"] == rejected_answer


def test_extractDpoPairs_no_pair_if_only_passed() -> None:
    traces = [_mkTrace("Q", "긴 답변 텍스트 충분히 sample.", tools=["EngineCall"])]
    pairs = extractDpoPairs(traces)
    assert pairs == []


def test_extractDpoPairs_no_pair_if_only_failed() -> None:
    traces = [_mkTrace("Q", "짧음", withError=True)]
    pairs = extractDpoPairs(traces)
    assert pairs == []


def test_extractDpoPairs_no_tool_fails_verify() -> None:
    """도구 호출 없는 trace 는 verify fail → rejected 로 분류."""
    chosen = _mkTrace("Q", "긴 답변 텍스트 충분히 sample.", tools=["EngineCall"])
    no_tool = _mkTrace("Q", "도구 없이 답변 sample 텍스트 sample.")  # 도구 0
    pairs = extractDpoPairs([chosen, no_tool], minAnswerLen=10)
    assert len(pairs) == 1
    assert "도구 없이" in pairs[0]["rejected"]


def test_extractDpoPairs_short_answer_fails_verify() -> None:
    """answer 가 minAnswerLen 미만 → rejected 로 분류."""
    chosen = _mkTrace("Q", "긴 답변 텍스트 충분히 sample.", tools=["EngineCall"])
    short = _mkTrace("Q", "짧음", tools=["EngineCall"])
    pairs = extractDpoPairs([chosen, short], minAnswerLen=10)
    assert len(pairs) == 1
    assert pairs[0]["rejected"] == "짧음"


def test_extractDpoPairs_cartesian_when_multiple() -> None:
    """passed 2 + failed 2 → 2x2=4 pair."""
    traces = [
        _mkTrace("Q", "passed answer one sample 1.", tools=["EngineCall"]),
        _mkTrace("Q", "passed answer two sample 2.", tools=["EngineCall"]),
        _mkTrace("Q", "rejected one sample 1.", withError=True),
        _mkTrace("Q", "rejected two sample 2.", withError=True),
    ]
    pairs = extractDpoPairs(traces, minAnswerLen=10)
    assert len(pairs) == 4


def test_extractDpoPairs_group_by_question() -> None:
    """다른 질문은 cross-pair 0."""
    traces = [
        _mkTrace("Q1", "Q1 chosen long answer sample.", tools=["EngineCall"]),
        _mkTrace("Q2", "Q2 rejected text sample.", withError=True),
    ]
    pairs = extractDpoPairs(traces, minAnswerLen=10)
    assert pairs == []


def test_extractDpoPairs_skips_empty_question() -> None:
    traces = [
        {"question": "", "events": [{"kind": "chunk", "data": {"text": "x"}}]},
        _mkTrace("Q", "long answer text sample sample.", tools=["EngineCall"]),
    ]
    pairs = extractDpoPairs(traces)
    assert pairs == []


def test_buildDpoDataset_e2e(tmp_path: Path) -> None:
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    t1 = _mkTrace("Q", "chosen long answer text sample.", tools=["EngineCall"])
    t2 = _mkTrace("Q", "rejected text sample.", withError=True)
    (trace_dir / "t1.json").write_text(json.dumps(t1), encoding="utf-8")
    (trace_dir / "t2.json").write_text(json.dumps(t2), encoding="utf-8")

    out = tmp_path / "dpo.jsonl"
    stats = buildDpoDataset(traceDir=trace_dir, outPath=out, minAnswerLen=10)
    assert stats["totalTraces"] == 2
    assert stats["uniqueQuestions"] == 1
    assert stats["pairs"] == 1
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    pair = json.loads(lines[0])
    assert "prompt" in pair and "chosen" in pair and "rejected" in pair


def test_buildDpoDataset_no_pairs_when_no_failed(tmp_path: Path) -> None:
    """passed 만 있으면 pairs=0 + empty JSONL."""
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    t1 = _mkTrace("Q", "passed long text sample sample.", tools=["EngineCall"])
    (trace_dir / "t1.json").write_text(json.dumps(t1), encoding="utf-8")

    out = tmp_path / "dpo.jsonl"
    stats = buildDpoDataset(traceDir=trace_dir, outPath=out)
    assert stats["pairs"] == 0
    assert out.read_text(encoding="utf-8") == ""


def test_dpoPairs_no_ml_deps() -> None:
    """import 만으로 transformers / peft 활성화 안 되는지 가드."""
    import sys

    import dartlab.ai.training.dpoPairs  # noqa: F401

    assert "transformers" not in sys.modules
    assert "peft" not in sys.modules
    assert "torch" not in sys.modules


def test_training_package_exposes_dpo() -> None:
    """dartlab.ai.training 에서 extractDpoPairs / buildDpoDataset lazy 접근."""
    import dartlab.ai.training as t

    assert callable(t.extractDpoPairs)
    assert callable(t.buildDpoDataset)
