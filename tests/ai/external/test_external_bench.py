"""외부 한국 benchmark runner 단위 테스트 (cryptic-discovering-kettle G 트랙).

실 dataset 다운로드 X · dartlab.ai.ask 호출 X — mock askFn 으로 dispatch + scoring +
baseline write 검증. CI Fast 통과 보장.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_match_expected_string_substring():
    from tests.ai.external._common import _matchExpected

    assert _matchExpected("삼성전자 ROE 12.3%", "삼성전자") is True
    assert _matchExpected("애플", "삼성전자") is False


def test_match_expected_list_all_required():
    from tests.ai.external._common import _matchExpected

    assert _matchExpected("삼성전자 메모리 ASP 추세", ["삼성전자", "메모리"]) is True
    assert _matchExpected("삼성전자 ASP 추세", ["삼성전자", "메모리"]) is False  # 메모리 누락


def test_run_benchmark_dispatch_scoring(tmp_path, monkeypatch):
    from tests.ai.external import _common
    from tests.ai.external._common import runBenchmark

    # baseline 경로를 tmp_path 로 redirect
    baseline_path = tmp_path / "externalBenchBaseline.json"
    monkeypatch.setattr(_common, "_BASELINE_PATH", baseline_path)

    cases = [
        {"question": "삼성전자 ROE", "expected": "삼성전자"},
        {"question": "애플 revenue", "expected": "삼성전자"},  # mismatch
        {"question": "", "expected": "x"},  # skip (empty question)
    ]

    def mock_ask(q: str) -> str:
        return f"{q} 답변 mock"

    result = runBenchmark(
        benchmark="MockBench",
        cases=cases,
        askFn=mock_ask,
        writeBaseline=True,
    )

    assert result.benchmark == "MockBench"
    assert result.sample == 3
    assert result.completed == 2
    assert result.skipped == 1
    assert result.correct == 1
    assert result.score == 0.5
    assert baseline_path.exists()

    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert "MockBench" in data
    assert data["MockBench"]["score"] == 0.5


def test_run_benchmark_sample_limit():
    from tests.ai.external._common import runBenchmark

    cases = [{"question": f"q{i}", "expected": "q"} for i in range(100)]
    result = runBenchmark(
        benchmark="MockBench",
        cases=cases,
        askFn=lambda q: "q match",
        sample=10,
        writeBaseline=False,
    )
    assert result.sample == 10
    assert result.completed == 10
    assert result.correct == 10


def test_run_benchmark_handles_ask_exception():
    from tests.ai.external._common import runBenchmark

    def raising_ask(q: str) -> str:
        raise RuntimeError("network down")

    cases = [{"question": "삼성전자", "expected": "삼성전자"}]
    result = runBenchmark(
        benchmark="MockBench",
        cases=cases,
        askFn=raising_ask,
        writeBaseline=False,
    )
    assert result.completed == 0
    assert result.skipped == 1
    assert "network down" in result.cases[0]["reason"]


def test_krx_loader_missing_dataset_raises(tmp_path):
    from tests.ai.external.runKrxBench import _loadKrxBench

    nonexistent = tmp_path / "missing.jsonl"
    with pytest.raises(FileNotFoundError):
        list(_loadKrxBench(nonexistent))


def test_krx_loader_jsonl_parse(tmp_path):
    from tests.ai.external.runKrxBench import _loadKrxBench

    jsonl = tmp_path / "krx.jsonl"
    jsonl.write_text(
        '{"question": "KOSPI 시가총액 1 위?", "answer": "삼성전자"}\n'
        '{"question": "KOSDAQ?", "answer": ["에코프로비엠"]}\n',
        encoding="utf-8",
    )
    rows = list(_loadKrxBench(jsonl))
    assert len(rows) == 2
    assert rows[0]["question"] == "KOSPI 시가총액 1 위?"
    assert rows[0]["expected"] == "삼성전자"


def test_won_loader_jsonl_parse(tmp_path):
    from tests.ai.external.runWonBench import _loadWonBench

    jsonl = tmp_path / "won.jsonl"
    jsonl.write_text(
        '{"question": "K-IFRS 별도 정의?", "answer": "parent-only"}\n',
        encoding="utf-8",
    )
    rows = list(_loadWonBench(jsonl))
    assert len(rows) == 1
    assert "별도" in rows[0]["question"]


def test_kfineval_loader_jsonl_parse(tmp_path):
    from tests.ai.external.runKFinEval import _loadKFinEval

    jsonl = tmp_path / "kfin.jsonl"
    jsonl.write_text(
        '{"question": "BIS 자기자본비율 의무는?", "answer": "8"}\n',
        encoding="utf-8",
    )
    rows = list(_loadKFinEval(jsonl))
    assert len(rows) == 1
    assert rows[0]["expected"] == "8"
