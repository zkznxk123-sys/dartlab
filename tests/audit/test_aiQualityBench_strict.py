"""aiQualityBench strict mode smoke 단위 — 마스터 플랜 v2 트랙 5 PR-Q2.

mock dartlab.ask 로 _measureStrict + _renderStrictReport 검증. 실 LLM 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dartlab.ai.contracts import TraceEvent

# tests/_attempts 는 gitignore 스크래치 — CI 엔 부재(dd11d47b4 untrack). direct import path 추가 후
# importorskip 로 가드: 로컬(존재)이면 실행, CI(부재)면 collection 단계서 skip(ImportError 방지).
_ATTEMPTS = Path(__file__).resolve().parents[1] / "_attempts"
if str(_ATTEMPTS.parent) not in sys.path:
    sys.path.insert(0, str(_ATTEMPTS.parent))

aiQualityBench = pytest.importorskip("_attempts.aiQualityBench")

pytestmark = pytest.mark.unit


def test_measureStrict_uses_v2_rubric(monkeypatch: pytest.MonkeyPatch) -> None:
    """mock ask → _measureStrict 가 v2 rubric 평가 결과 반환."""
    import dartlab

    def mockAsk(question: str, *, events: bool = False, stream: bool = True):
        # v2 golden q1_roe_basic 의 rubric 통과 답변 시뮬
        yield TraceEvent("chunk", {"text": "삼성전자 005930 ROE 8.94%"}, ts="2026-05-28T12:00:00")
        yield TraceEvent("tool_start", {"tool": "EngineCall"}, ts="2026-05-28T12:00:01")
        yield TraceEvent("done", {"refs": [{"kind": "tableRef", "id": "t1"}]}, ts="2026-05-28T12:00:05")
        yield TraceEvent("first_chunk_ms", {"ms": 1500}, ts="2026-05-28T12:00:00")

    monkeypatch.setattr(dartlab, "ask", mockAsk)

    legacy_q = {"id": "q1_roe_basic", "question": "삼성전자 ROE", "expected": [], "tool_hint": ""}
    result = aiQualityBench._measureStrict(legacy_q)

    assert result["id"] == "q1_roe_basic"
    assert "totalScore" in result
    assert "passed" in result
    assert "dimensions" in result
    # accuracy 통과 + completeness 통과 + toolSelection 통과 + refsQuality 통과 → passed
    assert result["totalScore"] >= 70.0


def test_measureStrict_handles_missing_golden_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """legacy golden id 가 v2 에 없으면 error 반환."""
    legacy_q = {"id": "qXX_unknown", "question": "?", "expected": [], "tool_hint": ""}
    result = aiQualityBench._measureStrict(legacy_q)
    assert result["passed"] is False
    assert "golden v2 entry not found" in result["error"]


def test_measureStrict_handles_ask_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """dartlab.ask 예외 → error 필드 채움."""
    import dartlab

    def boomAsk(question: str, *, events: bool = False, stream: bool = True):
        raise RuntimeError("provider down")

    monkeypatch.setattr(dartlab, "ask", boomAsk)

    legacy_q = {"id": "q1_roe_basic", "question": "?", "expected": [], "tool_hint": ""}
    result = aiQualityBench._measureStrict(legacy_q)
    assert result["passed"] is False
    assert "RuntimeError" in result["error"]


def test_renderStrictReport_includes_5_dimensions() -> None:
    """report 출력에 5 차원 헤더 + total + acc/comp/tool/ref/lat 열 포함."""
    results = [
        {
            "id": "q1_test",
            "question": "x",
            "totalScore": 85.0,
            "passed": True,
            "answerLen": 100,
            "elapsedSec": 30.0,
            "dimensions": {
                "accuracy": {"raw": 80.0, "passed": True},
                "completeness": {"raw": 90.0, "passed": True},
                "toolSelection": {"raw": 100.0, "passed": True},
                "refsQuality": {"raw": 100.0, "passed": True},
                "latency": {"raw": 100.0, "passed": True},
            },
            "error": None,
        }
    ]
    text = aiQualityBench._renderStrictReport(results)
    assert "strict quality benchmark" in text
    assert "q1_test" in text
    # 5 차원 column 헤더 — acc / comp / tool / ref / lat
    assert " acc " in text
    assert " comp " in text
    assert " tool " in text
    assert " ref " in text
    assert " lat " in text
    assert "85.0%" in text


def test_renderStrictReport_empty() -> None:
    assert "결과 없음" in aiQualityBench._renderStrictReport([])
