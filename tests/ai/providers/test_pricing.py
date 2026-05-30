"""provider 가격표 + CostTracker 단위 테스트.

마스터 플랜 트랙 2 PR-O1 동행. 미등록 모델 fallback / prefix 매칭 / cache 환산 /
turn 누적 등 KPI 측정 인프라 결정론 검증.
"""

from __future__ import annotations

import pytest

from dartlab.ai.providers._pricing import (
    CostTracker,
    calcCostFromUsage,
    calcCostUsd,
)

pytestmark = pytest.mark.unit


def test_calcCostUsd_anthropic_opus_exact() -> None:
    """anthropic claude-opus 정확 매칭 — 1000 input + 500 output."""
    cost = calcCostUsd("anthropic", "claude-opus-4-7", inputTokens=1000, outputTokens=500)
    assert cost["priced"] is True
    # 1000 * 15 / 1M = 0.015
    assert cost["inputUsd"] == pytest.approx(0.015, abs=1e-6)
    # 500 * 75 / 1M = 0.0375
    assert cost["outputUsd"] == pytest.approx(0.0375, abs=1e-6)
    assert cost["totalUsd"] == pytest.approx(0.0525, abs=1e-6)


def test_calcCostUsd_prefix_match_sonnet() -> None:
    """prefix 매칭 — claude-sonnet 으로 등록된 표가 4-6 같은 변형 모델 잡음."""
    cost = calcCostUsd("anthropic", "claude-sonnet-4-6-2026-05", inputTokens=1000, outputTokens=1000)
    assert cost["priced"] is True
    # 1000 * 3 / 1M = 0.003 + 1000 * 15 / 1M = 0.015 → 0.018
    assert cost["totalUsd"] == pytest.approx(0.018, abs=1e-6)


def test_calcCostUsd_unknown_model_unpriced() -> None:
    """미등록 모델 → priced=False + 0 USD (강한 실패 회피)."""
    cost = calcCostUsd("provider_xyz", "model_xyz", inputTokens=1000, outputTokens=500)
    assert cost["priced"] is False
    assert cost["totalUsd"] == 0.0


def test_calcCostUsd_cache_tokens_anthropic() -> None:
    """anthropic cache_create / cache_read 환산.

    claude-opus-4-7 의 cacheCreate=18.75/M (input × 1.25), cacheRead=1.5/M (input × 0.1).
    """
    cost = calcCostUsd(
        "anthropic",
        "claude-opus-4-7",
        inputTokens=0,
        outputTokens=0,
        cacheCreateTokens=1000,
        cacheReadTokens=10_000,
    )
    # 1000 * 18.75 / 1M = 0.01875
    assert cost["cacheCreateUsd"] == pytest.approx(0.01875, abs=1e-6)
    # 10000 * 1.5 / 1M = 0.015
    assert cost["cacheReadUsd"] == pytest.approx(0.015, abs=1e-6)


def test_calcCostUsd_openai_cacheCreate_is_zero() -> None:
    """openai 는 cacheCreate=0.0 등록 — 캐시 생성 별도 과금 없음.

    Anthropic 은 cache write 가 input×1.25 프리미엄이지만 OpenAI prompt caching 은
    cache write 무과금 (정상 input 으로만 계산, cache read 만 50% 할인). 게다가 OpenAI
    usage dict 에 cache_creation_input_tokens 필드가 없어 cacheCreateTokens 는 실무상 0.
    가격표가 0.0 으로 명시 override → fallback(1.25×) 미적용이 정상.
    """
    cost = calcCostUsd(
        "openai",
        "gpt-4o",
        inputTokens=0,
        outputTokens=0,
        cacheCreateTokens=1000,
    )
    # gpt-4o cacheCreate=0.0 (명시) → 1000 * 0.0 / 1M = 0.0
    assert cost["cacheCreateUsd"] == pytest.approx(0.0, abs=1e-6)


def test_calcCostFromUsage_anthropic_usage_dict() -> None:
    """provider stop event 의 usage dict → cost 환산."""
    usage = {
        "input_tokens": 2000,
        "output_tokens": 1000,
        "cache_creation_input_tokens": 500,
        "cache_read_input_tokens": 5000,
    }
    cost = calcCostFromUsage("anthropic", "claude-opus-4-7", usage)
    assert cost["priced"] is True
    # 2000 * 15 / 1M + 1000 * 75 / 1M + 500 * 18.75 / 1M + 5000 * 1.5 / 1M
    expected = 0.03 + 0.075 + 0.009375 + 0.0075
    assert cost["totalUsd"] == pytest.approx(expected, abs=1e-6)


def test_calcCostFromUsage_empty_usage() -> None:
    """빈 usage dict → 모든 항목 0."""
    cost = calcCostFromUsage("anthropic", "claude-opus-4-7", {})
    assert cost["totalUsd"] == 0.0
    assert cost["priced"] is True  # 모델은 등록됨


def test_CostTracker_accumulates_per_turn() -> None:
    """turn 별 record + snapshot 누적 검증."""
    tracker = CostTracker(provider="anthropic", model="claude-opus-4-7")
    tracker.record({"input_tokens": 1000, "output_tokens": 500})
    tracker.record({"input_tokens": 2000, "output_tokens": 1000})
    snap = tracker.snapshot()
    assert snap["turnCount"] == 2
    # 0.0525 + 0.105 = 0.1575
    assert snap["totalUsd"] == pytest.approx(0.1575, abs=1e-6)
    assert snap["priced"] is True
    assert len(snap["perTurn"]) == 2


def test_CostTracker_empty_snapshot() -> None:
    """빈 tracker → priced False (turn 0 기준)."""
    tracker = CostTracker(provider="anthropic", model="claude-opus-4-7")
    snap = tracker.snapshot()
    assert snap["turnCount"] == 0
    assert snap["totalUsd"] == 0.0
    assert snap["priced"] is False


def test_CostTracker_unknown_model_priced_false() -> None:
    """미등록 모델 tracker → snapshot priced=False."""
    tracker = CostTracker(provider="zzz", model="zzz")
    tracker.record({"input_tokens": 100, "output_tokens": 50})
    snap = tracker.snapshot()
    assert snap["priced"] is False
    assert snap["totalUsd"] == 0.0
