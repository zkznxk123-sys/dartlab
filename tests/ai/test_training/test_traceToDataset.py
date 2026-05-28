"""traceToDataset SFT 변환 단위 — 마스터 플랜 v2 트랙 8 PR-T1.

trace JSON → SFT JSONL dataset. ML 의존성 0 (transformers 등 미사용).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dartlab.ai.training.traceToDataset import (
    buildSftDataset,
    loadTraceDir,
    traceToSftSample,
    writeJsonl,
)

pytestmark = pytest.mark.unit


def _mkTrace(question: str, answer: str, *, tools: list[str] | None = None) -> dict:
    events: list[dict] = []
    # 시작 chunk + tool 호출 + 결과 chunk
    if tools:
        for tool in tools:
            events.append({"kind": "tool_start", "data": {"tool": tool, "input": {}}})
            events.append({"kind": "tool_result", "data": {"tool": tool, "result": {"ok": True}}})
    if answer:
        # chunk 단위 분할 모사
        for i in range(0, len(answer), 10):
            events.append({"kind": "chunk", "data": {"text": answer[i : i + 10]}})
    events.append({"kind": "done", "data": {}})
    return {
        "sessionId": "test-001",
        "question": question,
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "startedAt": "2026-05-28T00:00:00",
        "finishedAt": "2026-05-28T00:00:10",
        "events": events,
    }


# ────────────────────────── traceToSftSample ──────────────────────────


def test_traceToSftSample_basic_round_trip() -> None:
    trace = _mkTrace("ROE 알려줘", "삼성전자 ROE 는 8.94% 입니다.")
    sample = traceToSftSample(trace)
    assert sample is not None
    assert sample["messages"][0]["role"] == "system"
    assert sample["messages"][1]["role"] == "user"
    assert sample["messages"][1]["content"] == "ROE 알려줘"
    assert sample["messages"][2]["role"] == "assistant"
    assert sample["messages"][2]["content"] == "삼성전자 ROE 는 8.94% 입니다."


def test_traceToSftSample_tools_used() -> None:
    trace = _mkTrace("DCF", "결과", tools=["EngineCall", "DCFValuation"])
    sample = traceToSftSample(trace)
    assert sample["tools_used"] == ["EngineCall", "DCFValuation"]


def test_traceToSftSample_missing_question_returns_none() -> None:
    trace = {"question": "", "events": [{"kind": "chunk", "data": {"text": "hi"}}]}
    assert traceToSftSample(trace) is None


def test_traceToSftSample_missing_answer_returns_none() -> None:
    trace = _mkTrace("질문", "")
    assert traceToSftSample(trace) is None


def test_traceToSftSample_non_dict_returns_none() -> None:
    assert traceToSftSample(None) is None
    assert traceToSftSample("string") is None
    assert traceToSftSample(123) is None


def test_traceToSftSample_custom_system_prompt() -> None:
    trace = _mkTrace("ROE", "8.94%")
    sample = traceToSftSample(trace, systemPrompt="custom prompt")
    assert sample["messages"][0]["content"] == "custom prompt"


def test_traceToSftSample_trace_meta_preserved() -> None:
    trace = _mkTrace("ROE", "answer text long enough")
    sample = traceToSftSample(trace)
    assert sample["trace_meta"]["sessionId"] == "test-001"
    assert sample["trace_meta"]["provider"] == "anthropic"
    assert sample["trace_meta"]["model"] == "claude-sonnet-4-5"


# ────────────────────────── loadTraceDir ──────────────────────────


def test_loadTraceDir_reads_all_json(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps({"sessionId": "a"}), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"sessionId": "b"}), encoding="utf-8")
    traces = list(loadTraceDir(tmp_path))
    assert len(traces) == 2
    assert {t["sessionId"] for t in traces} == {"a", "b"}


def test_loadTraceDir_skips_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "ok.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    (tmp_path / "bad.json").write_text("not json {{", encoding="utf-8")
    traces = list(loadTraceDir(tmp_path))
    assert len(traces) == 1


def test_loadTraceDir_missing_dir() -> None:
    traces = list(loadTraceDir("/nonexistent/path/xyz"))
    assert traces == []


# ────────────────────────── writeJsonl ──────────────────────────


def test_writeJsonl_creates_parent_dir(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "data.jsonl"
    writeJsonl([{"x": 1}, {"y": 2}], out)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"x": 1}


def test_writeJsonl_empty(tmp_path: Path) -> None:
    out = tmp_path / "empty.jsonl"
    writeJsonl([], out)
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


# ────────────────────────── buildSftDataset ──────────────────────────


def test_buildSftDataset_e2e(tmp_path: Path) -> None:
    """trace dir → JSONL dataset 전체 파이프라인."""
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    t1 = _mkTrace("ROE 알려줘", "삼성전자 ROE 는 8.94% 입니다.", tools=["EngineCall"])
    t2 = _mkTrace("PER", "PER 은 12.3 배 입니다. 정상 범위.", tools=["EngineCall"])
    (trace_dir / "t1.json").write_text(json.dumps(t1), encoding="utf-8")
    (trace_dir / "t2.json").write_text(json.dumps(t2), encoding="utf-8")

    out = tmp_path / "sft_v1.jsonl"
    stats = buildSftDataset(traceDir=trace_dir, outPath=out, minAnswerLen=5)
    assert stats["totalTraces"] == 2
    assert stats["accepted"] == 2
    assert stats["rejected"] == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_buildSftDataset_min_tool_calls_filter(tmp_path: Path) -> None:
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    t1 = _mkTrace("Q1", "answer text long enough", tools=["EngineCall"])  # 1 tool
    t2 = _mkTrace("Q2", "answer text long enough")  # 0 tool
    (trace_dir / "t1.json").write_text(json.dumps(t1), encoding="utf-8")
    (trace_dir / "t2.json").write_text(json.dumps(t2), encoding="utf-8")

    out = tmp_path / "sft.jsonl"
    stats = buildSftDataset(traceDir=trace_dir, outPath=out, minToolCalls=1, minAnswerLen=5)
    assert stats["accepted"] == 1
    assert stats["rejected"] == 1


def test_buildSftDataset_min_answer_len_filter(tmp_path: Path) -> None:
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    t1 = _mkTrace("Q1", "긴 답변 텍스트 충분히 긴 응답 sample.", tools=["EngineCall"])
    t2 = _mkTrace("Q2", "ok", tools=["EngineCall"])  # too short
    (trace_dir / "t1.json").write_text(json.dumps(t1), encoding="utf-8")
    (trace_dir / "t2.json").write_text(json.dumps(t2), encoding="utf-8")

    out = tmp_path / "sft.jsonl"
    stats = buildSftDataset(traceDir=trace_dir, outPath=out, minAnswerLen=10)
    assert stats["accepted"] == 1
    assert stats["rejected"] == 1


def test_buildSftDataset_no_ml_deps() -> None:
    """import 만으로 ML 의존성 (transformers / peft) 활성화 안 되는지 가드."""
    import importlib
    import sys

    importlib.import_module("dartlab.ai.training.traceToDataset")
    assert "transformers" not in sys.modules
    assert "peft" not in sys.modules
    assert "torch" not in sys.modules


def test_training_package_lazy_export() -> None:
    """dartlab.ai.training __init__ 에서 lazy attribute 접근 동작."""
    import dartlab.ai.training as t

    assert callable(t.traceToSftSample)
    assert callable(t.buildSftDataset)
