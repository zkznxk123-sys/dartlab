"""Provider 모델 가격표 + cost 환산 — KPI 관측 인프라 SSOT.

마스터 플랜 트랙 2 PR-O1 (cryptic-discovering-kettle.md). 회귀 — provider usage dict
(input_tokens / output_tokens / cache_*) 는 박혀있는데 *비용 환산 없어서* KPI digest 가
turn 당 비용 추적 불가. 박제 → 측정 가능 인프라.

가격 정책: 운영자 *수동* 갱신 (자동 fetch 금지 — 외부 의존성). 모델 추가 시 본
파일만 수정. 미등록 모델은 0 USD 반환 + warning log (강한 실패 회피 — 측정 정보성).

USD/1M tokens 단위 (provider 공식 가격표). cache_creation_input ≈ input × 1.25,
cache_read_input ≈ input × 0.1 (anthropic 기준). 모델별 직접 명시도 가능.

마지막 갱신: 2026-05-28.
"""

from __future__ import annotations

from typing import Any

# 모델 가격표 — USD per 1M tokens. (provider, modelPrefix) 키.
# modelPrefix = startswith 매칭 (예: "claude-opus-4-7" 으로 박혀있어도 "claude-opus" prefix 매칭).
# cacheCreate / cacheRead 가 None 이면 input 의 1.25× / 0.1× 자동 적용 (anthropic 기준).
_PRICE_TABLE: dict[tuple[str, str], dict[str, float | None]] = {
    # Anthropic — 2026-05 공식 가격
    ("anthropic", "claude-opus-4-7"): {"input": 15.0, "output": 75.0, "cacheCreate": 18.75, "cacheRead": 1.5},
    ("anthropic", "claude-opus"): {"input": 15.0, "output": 75.0, "cacheCreate": 18.75, "cacheRead": 1.5},
    ("anthropic", "claude-sonnet-4-6"): {"input": 3.0, "output": 15.0, "cacheCreate": 3.75, "cacheRead": 0.3},
    ("anthropic", "claude-sonnet"): {"input": 3.0, "output": 15.0, "cacheCreate": 3.75, "cacheRead": 0.3},
    ("anthropic", "claude-haiku-4-5"): {"input": 0.8, "output": 4.0, "cacheCreate": 1.0, "cacheRead": 0.08},
    ("anthropic", "claude-haiku"): {"input": 0.8, "output": 4.0, "cacheCreate": 1.0, "cacheRead": 0.08},
    # OpenAI — 2026-05 공식. PR-M2 — cacheRead 명시 (자동 prompt cache 50% 할인).
    ("openai", "gpt-5"): {"input": 10.0, "output": 40.0, "cacheCreate": 0.0, "cacheRead": 5.0},
    ("openai", "gpt-4o"): {"input": 2.5, "output": 10.0, "cacheCreate": 0.0, "cacheRead": 1.25},
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.6, "cacheCreate": 0.0, "cacheRead": 0.075},
    ("openai", "gpt-4"): {"input": 30.0, "output": 60.0, "cacheCreate": 0.0, "cacheRead": 30.0},
    # Google Gemini — PR-M2 cached_content_token_count 가 cache hit (context caching).
    # cacheRead = input × 0.25 (Gemini 75% 할인).
    ("gemini", "gemini-2.5-pro"): {"input": 1.25, "output": 5.0, "cacheCreate": 0.0, "cacheRead": 0.3125},
    ("gemini", "gemini-2.5-flash"): {"input": 0.075, "output": 0.3, "cacheCreate": 0.0, "cacheRead": 0.01875},
    ("gemini", "gemini-1.5-pro"): {"input": 1.25, "output": 5.0, "cacheCreate": 0.0, "cacheRead": 0.3125},
    ("google", "gemini-2.5-pro"): {"input": 1.25, "output": 5.0, "cacheCreate": 0.0, "cacheRead": 0.3125},
    # xAI Grok
    ("xai", "grok"): {"input": 5.0, "output": 15.0, "cacheCreate": None, "cacheRead": None},
    # OAuth / Codex / Ollama / DartLab — local 또는 무과금 가정
    ("codex", ""): {"input": 0.0, "output": 0.0, "cacheCreate": None, "cacheRead": None},
    ("ollama", ""): {"input": 0.0, "output": 0.0, "cacheCreate": None, "cacheRead": None},
    ("dartlab", ""): {"input": 0.0, "output": 0.0, "cacheCreate": None, "cacheRead": None},
}


def _lookupPrice(provider: str, model: str) -> dict[str, float | None] | None:
    """(provider, model) → 가격 dict. modelPrefix startswith 매칭. 미등록 None."""
    prov = (provider or "").lower()
    mdl = (model or "").lower()
    # 정확 매칭 우선
    exact = _PRICE_TABLE.get((prov, mdl))
    if exact is not None:
        return exact
    # prefix 매칭
    best_match: tuple[str, dict[str, float | None]] | None = None
    for (pv, prefix), price in _PRICE_TABLE.items():
        if pv != prov:
            continue
        if prefix and mdl.startswith(prefix):
            if best_match is None or len(prefix) > len(best_match[0]):
                best_match = (prefix, price)
        elif prefix == "" and best_match is None:
            best_match = (prefix, price)
    return best_match[1] if best_match else None


def calcCostUsd(
    provider: str,
    model: str,
    inputTokens: int = 0,
    outputTokens: int = 0,
    cacheCreateTokens: int = 0,
    cacheReadTokens: int = 0,
) -> dict[str, float]:
    """usage → USD 환산. 미등록 모델 0 USD 반환 (warning 없음 — 정보성).

    Parameters
    ----------
    provider : str
        ``"anthropic"`` / ``"openai"`` / ``"gemini"`` / ``"xai"`` / ``"codex"`` / ``"ollama"`` / ``"dartlab"``.
    model : str
        provider 별 모델명 (예: ``"claude-opus-4-7"``).
    inputTokens, outputTokens : int
        사용량 (provider usage dict 의 input_tokens / output_tokens).
    cacheCreateTokens, cacheReadTokens : int
        anthropic prompt cache 사용량 (마스터 플랜 PR-O3 활성 후 의미). None 시 0.

    Returns
    -------
    dict[str, float]
        - ``inputUsd`` / ``outputUsd`` / ``cacheCreateUsd`` / ``cacheReadUsd`` : 항목별 USD
        - ``totalUsd`` : 합계
        - ``priced`` : bool — 가격표 등록 모델 여부 (False 면 0 환산, 측정 불가 신호)

    Example
    -------
        >>> calcCostUsd("anthropic", "claude-opus-4-7", 1000, 500)
        {"inputUsd": 0.015, "outputUsd": 0.0375, ..., "totalUsd": 0.0525, "priced": True}

    Raises
    ------
    없음 — 미등록 모델도 0 USD + priced=False 반환.
    """
    price = _lookupPrice(provider, model)
    if price is None:
        return {
            "inputUsd": 0.0,
            "outputUsd": 0.0,
            "cacheCreateUsd": 0.0,
            "cacheReadUsd": 0.0,
            "totalUsd": 0.0,
            "priced": False,
        }
    inp_per_m = float(price.get("input", 0.0) or 0.0)
    out_per_m = float(price.get("output", 0.0) or 0.0)
    cache_create_per_m = price.get("cacheCreate")
    cache_read_per_m = price.get("cacheRead")
    # None fallback — anthropic 룰 (1.25× / 0.1×) 적용. 다른 provider 도 동일 fallback 사용.
    cc_per_m = float(cache_create_per_m) if cache_create_per_m is not None else inp_per_m * 1.25
    cr_per_m = float(cache_read_per_m) if cache_read_per_m is not None else inp_per_m * 0.1
    input_usd = inputTokens * inp_per_m / 1_000_000.0
    output_usd = outputTokens * out_per_m / 1_000_000.0
    cc_usd = cacheCreateTokens * cc_per_m / 1_000_000.0
    cr_usd = cacheReadTokens * cr_per_m / 1_000_000.0
    total = input_usd + output_usd + cc_usd + cr_usd
    return {
        "inputUsd": round(input_usd, 6),
        "outputUsd": round(output_usd, 6),
        "cacheCreateUsd": round(cc_usd, 6),
        "cacheReadUsd": round(cr_usd, 6),
        "totalUsd": round(total, 6),
        "priced": True,
    }


def calcCostFromUsage(provider: str, model: str, usage: dict[str, Any]) -> dict[str, float]:
    """usage dict (provider stop event payload) → cost dict.

    usage 표준 키: ``input_tokens`` · ``output_tokens`` · ``cache_creation_input_tokens`` ·
    ``cache_read_input_tokens``. 미존재 키는 0 처리.
    """
    return calcCostUsd(
        provider=provider,
        model=model,
        inputTokens=int(usage.get("input_tokens", 0) or 0),
        outputTokens=int(usage.get("output_tokens", 0) or 0),
        cacheCreateTokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
        cacheReadTokens=int(usage.get("cache_read_input_tokens", 0) or 0),
    )


class CostTracker:
    """turn 별 cost 누적기 — 본체 자율 호출 loop 종료 시 KPI digest 입력.

    Usage
    -----
        tracker = CostTracker(provider="anthropic", model="claude-opus-4-7")
        tracker.record(usage={"input_tokens": 1000, "output_tokens": 500})
        snapshot = tracker.snapshot()  # {totalUsd, perTurn[], breakdown}
    """

    def __init__(self, *, provider: str = "", model: str = "") -> None:
        self._provider = provider
        self._model = model
        self._perTurn: list[dict[str, float]] = []
        self._total: float = 0.0

    def record(self, usage: dict[str, Any]) -> dict[str, float]:
        """turn 종료 시 usage 적재. 반환 = 본 turn 의 cost dict."""
        cost = calcCostFromUsage(self._provider, self._model, usage)
        self._perTurn.append(cost)
        self._total += cost["totalUsd"]
        return cost

    def snapshot(self) -> dict[str, Any]:
        """누적 상태 dict — KPI digest / TraceEvent 본문."""
        return {
            "provider": self._provider,
            "model": self._model,
            "totalUsd": round(self._total, 6),
            "turnCount": len(self._perTurn),
            "perTurn": list(self._perTurn),
            "priced": all(t.get("priced", False) for t in self._perTurn) if self._perTurn else False,
        }


__all__ = ["calcCostUsd", "calcCostFromUsage", "CostTracker"]
