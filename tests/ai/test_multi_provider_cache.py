"""multi-provider cache observability — 마스터 플랜 v2 트랙 7 PR-M2.

OpenAI / Gemini usage dict + _pricing cacheRead 단위. 외부 호출 0.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


# ────────────────────────── OpenAI _usageDict ──────────────────────────


def test_openai_usageDict_extracts_cached_tokens() -> None:
    """prompt_tokens_details.cached_tokens → cache_read_input_tokens."""
    from dartlab.ai.providers.openai import _usageDict

    usage = SimpleNamespace(
        prompt_tokens=1000,
        completion_tokens=200,
        prompt_tokens_details=SimpleNamespace(cached_tokens=600),
    )
    out = _usageDict(usage)
    assert out["input_tokens"] == 1000
    assert out["output_tokens"] == 200
    assert out["cache_read_input_tokens"] == 600
    assert out["cache_creation_input_tokens"] == 0


def test_openai_usageDict_no_cache_details() -> None:
    """prompt_tokens_details 없으면 cached=0."""
    from dartlab.ai.providers.openai import _usageDict

    usage = SimpleNamespace(prompt_tokens=500, completion_tokens=100)
    out = _usageDict(usage)
    assert out["cache_read_input_tokens"] == 0


def test_openai_usageDict_none_returns_empty() -> None:
    from dartlab.ai.providers.openai import _usageDict

    assert _usageDict(None) == {}


# ────────────────────────── Gemini _usageDict ──────────────────────────


def test_gemini_usageDict_extracts_cached_content() -> None:
    """usage_metadata.cached_content_token_count → cache_read_input_tokens."""
    from dartlab.ai.providers.google import _usageDict

    meta = SimpleNamespace(
        prompt_token_count=2000,
        candidates_token_count=400,
        cached_content_token_count=1500,
    )
    out = _usageDict(meta)
    assert out["input_tokens"] == 2000
    assert out["output_tokens"] == 400
    assert out["cache_read_input_tokens"] == 1500
    assert out["cache_creation_input_tokens"] == 0


def test_gemini_usageDict_no_cache() -> None:
    from dartlab.ai.providers.google import _usageDict

    meta = SimpleNamespace(prompt_token_count=1000, candidates_token_count=200)
    out = _usageDict(meta)
    assert out["cache_read_input_tokens"] == 0
    assert out["input_tokens"] == 1000


def test_gemini_usageDict_none_returns_empty() -> None:
    from dartlab.ai.providers.google import _usageDict

    assert _usageDict(None) == {}


# ────────────────────────── _pricing cacheRead ──────────────────────────


def test_pricing_openai_gpt4o_cache_read_half_input() -> None:
    """OpenAI gpt-4o cacheRead = input × 0.5 (cached 토큰 50% 할인)."""
    from dartlab.ai.providers._pricing import _lookupPrice

    price = _lookupPrice("openai", "gpt-4o")
    assert price is not None
    assert price["input"] == 2.5
    assert price["cacheRead"] == 1.25  # 50% of input


def test_pricing_gemini_cache_read_quarter_input() -> None:
    """Gemini 2.5-pro cacheRead = input × 0.25 (cached 75% 할인)."""
    from dartlab.ai.providers._pricing import _lookupPrice

    price = _lookupPrice("gemini", "gemini-2.5-pro")
    assert price is not None
    assert price["input"] == 1.25
    assert price["cacheRead"] == 0.3125  # 25% of input


def test_calcCostFromUsage_openai_with_cache() -> None:
    """OpenAI usage (cache_read 포함) → cost 환산 정확성."""
    from dartlab.ai.providers._pricing import calcCostFromUsage

    cost = calcCostFromUsage(
        "openai",
        "gpt-4o",
        {
            "input_tokens": 1000,
            "output_tokens": 200,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 600,
        },
    )
    assert cost["priced"] is True
    # input 1000 × $2.5/1M = $0.0025
    assert cost["inputUsd"] == pytest.approx(0.0025, abs=1e-6)
    # output 200 × $10/1M = $0.002
    assert cost["outputUsd"] == pytest.approx(0.002, abs=1e-6)
    # cacheRead 600 × $1.25/1M = $0.00075
    assert cost["cacheReadUsd"] == pytest.approx(0.00075, abs=1e-6)


def test_calcCostFromUsage_gemini_with_cache() -> None:
    """Gemini usage (cache_read 포함) → cost 환산."""
    from dartlab.ai.providers._pricing import calcCostFromUsage

    cost = calcCostFromUsage(
        "gemini",
        "gemini-2.5-pro",
        {
            "input_tokens": 2000,
            "output_tokens": 400,
            "cache_read_input_tokens": 1500,
        },
    )
    assert cost["priced"] is True
    # cacheRead 1500 × $0.3125/1M
    assert cost["cacheReadUsd"] == pytest.approx(1500 * 0.3125 / 1_000_000, abs=1e-6)


def test_pricing_table_has_openai_mini() -> None:
    """gpt-4o-mini (PR-L3 cheap tier) cacheRead 룰 등록."""
    from dartlab.ai.providers._pricing import _lookupPrice

    price = _lookupPrice("openai", "gpt-4o-mini")
    assert price is not None
    assert price["cacheRead"] == 0.075


def test_pricing_table_has_gemini_flash() -> None:
    """gemini-2.5-flash cacheRead 룰 등록."""
    from dartlab.ai.providers._pricing import _lookupPrice

    price = _lookupPrice("gemini", "gemini-2.5-flash")
    assert price is not None
    assert price["cacheRead"] == 0.01875
