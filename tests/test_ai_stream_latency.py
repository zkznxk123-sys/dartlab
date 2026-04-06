"""P1-1: preGround 백그라운드 thread 화 검증.

`_analyze_inner` 가 ground 호출 (disclosure / search / insight) 를
ThreadPoolExecutor 로 병렬 fire 하고 timeout 으로 join 하는지 확인.

검증 방식: ground 함수들을 sleep 으로 monkeypatch 하고
첫 chunk yield 까지 측정.
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.unit


def _make_mock_company():
    """최소한의 Company stub."""
    class MockCompany:
        corpName = "TestCorp"
        stockCode = "000000"
        market = "KR"
        sector = ""

        def filings(self):
            return None

    return MockCompany()


def _make_mock_provider():
    """즉시 chunk yield 하는 mock LLM provider."""
    class MockProvider:
        supports_cache_control = False
        config = None

        def stream(self, messages):
            yield "first chunk"

    return MockProvider()


@pytest.fixture
def patch_runtime(monkeypatch):
    """core.py 의 외부 의존성을 mock 으로 교체."""
    from dartlab.ai.runtime import core

    # ground 함수들을 sleep 으로 교체 — 각 1초씩
    def slow_disclosure(stockCode=None):
        time.sleep(1.0)
        return "<disclosure-brief>mock</disclosure-brief>"

    def slow_search(question, stockCode=None, corpName=None):
        time.sleep(1.0)
        return "<search>mock</search>"

    def slow_insight(stock_id, company):
        time.sleep(1.0)
        return "## insight mock"

    monkeypatch.setattr(core, "_preGroundDisclosure", slow_disclosure)
    monkeypatch.setattr(core, "_preGroundSearch", slow_search)
    monkeypatch.setattr(core, "_gatherInsightHints", slow_insight)
    monkeypatch.setattr(core, "_needsExternalSearch", lambda q: True)

    # provider mock
    def fake_create_provider(config):
        return _make_mock_provider()

    monkeypatch.setattr("dartlab.ai.providers.create_provider", fake_create_provider)

    # config mock
    class FakeConfig:
        def merge(self, _):
            return self

    def fake_get_config(role=None):
        return FakeConfig()

    monkeypatch.setattr("dartlab.ai.get_config", fake_get_config)

    # 시스템 프롬프트 빌드 — 빠른 mock
    monkeypatch.setattr(
        core,
        "_buildSystemPromptParts",
        lambda *a, **k: ("static", "dynamic"),
    )

    # selfai 폐기 — few_shot / router mock 불필요


def test_parallel_ground_total_under_2s(patch_runtime, monkeypatch):
    """3개 ground 호출 (각 1초) 를 병렬 fire → 총 시간 < 2초.

    동기 모드면 3초 (1+1+1), 병렬이면 1초 + overhead.
    """
    from dartlab.ai.runtime.core import analyze

    monkeypatch.delenv("DARTLAB_AI_PREGROUND_SYNC", raising=False)

    company = _make_mock_company()
    start = time.monotonic()
    chunks_received = []
    for event in analyze(company, "최근 실적 알려줘"):
        if event.kind == "chunk":
            chunks_received.append(event.data)
            if len(chunks_received) >= 1:
                break

    elapsed = time.monotonic() - start
    assert chunks_received, "첫 chunk 받지 못함"
    assert elapsed < 2.5, (
        f"병렬 fire 가 작동하지 않음. 첫 chunk 까지 {elapsed:.2f}초 (목표 < 2.5초)"
    )


def test_sync_mode_falls_back_to_sequential(patch_runtime, monkeypatch):
    """DARTLAB_AI_PREGROUND_SYNC=1 시 동기 경로 (fallback) 동작 확인."""
    from dartlab.ai.runtime.core import analyze

    monkeypatch.setenv("DARTLAB_AI_PREGROUND_SYNC", "1")

    company = _make_mock_company()
    start = time.monotonic()
    for event in analyze(company, "최근 실적 알려줘"):
        if event.kind == "chunk":
            break

    elapsed = time.monotonic() - start
    # 동기 모드 = 1+1+1 = 약 3초 이상이어야 함 (병렬 아니므로)
    assert elapsed >= 2.5, (
        f"sync 모드가 동기적으로 동작하지 않음. {elapsed:.2f}초 (>= 2.5초 기대)"
    )


def test_ground_timeout_does_not_block(patch_runtime, monkeypatch):
    """timeout 환경변수로 ground 가 늦게 와도 첫 chunk 는 빨리 나옴."""
    from dartlab.ai.runtime.core import analyze
    from dartlab.ai.runtime import core

    # ground 를 5초 sleep 으로 교체
    def very_slow(*a, **k):
        time.sleep(5.0)
        return "slow"

    monkeypatch.setattr(core, "_preGroundDisclosure", very_slow)
    monkeypatch.setattr(core, "_preGroundSearch", very_slow)
    monkeypatch.setattr(core, "_gatherInsightHints", very_slow)
    monkeypatch.setenv("DARTLAB_PREGROUND_TIMEOUT", "0.5")
    monkeypatch.delenv("DARTLAB_AI_PREGROUND_SYNC", raising=False)

    company = _make_mock_company()
    start = time.monotonic()
    for event in analyze(company, "최근 실적 알려줘"):
        if event.kind == "chunk":
            break

    elapsed = time.monotonic() - start
    assert elapsed < 1.5, (
        f"timeout 후에도 첫 chunk 가 늦음. {elapsed:.2f}초 (< 1.5초 기대)"
    )
