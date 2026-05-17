"""Ref confidence 정책 + 데코레이터 — Track B (Trail-of-Evidence + Confidence).

신뢰도 0-100 정수. 표시 매핑은 1 곳 (display label):
- low (<40): 가정 강함 또는 verify 실패 — 답변 안 빨강 chip
- mid (40-70): deterministic 계산이지만 잠재 가정 — 회색 chip
- high (>70): filing 직접 인용 또는 검증된 비율 — emerald chip

정책 (method → base score):
- "filing_direct" = 95   raw 공시 본문 / 계정 매핑된 단일 값
- "ratio" = 80           발급된 raw 값들 결합한 비율 (ROE, PER 등)
- "trend" = 75           시계열 추세 (CAGR, YoY)
- "forecast" = 30        예측·DCF·forecast (가정 강함)
- "scenario" = 35        시나리오 시뮬레이션 (어떤 가정에 종속)
- "llm" = 40             LLM 자체 추정·해석 (외부 가공)
- "external" = 50        WebSearch 본문 (untrusted)

verify_answer 페널티:
- verify fail → -50 (정책 호출자에서 적용)

표시 라벨 → 색상 매핑 SSOT 는 UI [chat/refs/confidence.ts](file://./ui/web/src/features/chat/refs/confidence.ts) 와 1 대 1.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

ConfidenceMethod = Literal[
    "filing_direct",
    "ratio",
    "trend",
    "forecast",
    "scenario",
    "llm",
    "external",
]

_BASE_SCORES: dict[str, int] = {
    "filing_direct": 95,
    "ratio": 80,
    "trend": 75,
    "forecast": 30,
    "scenario": 35,
    "llm": 40,
    "external": 50,
}

_LOW_HIGH = (40, 70)


def baseScore(method: ConfidenceMethod) -> int:
    """method 별 기본 신뢰도. 알 수 없는 method 는 보수적 40 반환."""
    return _BASE_SCORES.get(method, 40)


def label(confidence: int) -> Literal["low", "mid", "high"]:
    """0-100 → low/mid/high 매핑 (SSOT). UI confidence chip 색상의 단일 진실 소스."""
    if confidence < _LOW_HIGH[0]:
        return "low"
    if confidence > _LOW_HIGH[1]:
        return "high"
    return "mid"


def tagConfidence(
    method: ConfidenceMethod, base: int | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """analysis/credit/quant 함수 결과 dict 에 _confidence 필드 부착.

    사용:
        @tagConfidence("ratio")
        def calcRoe(...): return {"roe": 0.135, ...}

    함수 반환이 dict 면 dict["_confidence"] = base score 부착. dict 아니면 그대로.
    """
    score = base if base is not None else baseScore(method)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        """함수 fn 을 wrapped 로 감싸 결과 dict 에 _confidence 메타 부착."""

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            """원본 fn 호출 후 결과가 dict 면 _confidence + _confidenceMethod 키 부착."""
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and "_confidence" not in result:
                result["_confidence"] = score
                result["_confidenceMethod"] = method
            return result

        wrapped.__name__ = getattr(fn, "__name__", "wrapped")
        wrapped.__doc__ = getattr(fn, "__doc__", None)
        return wrapped

    return decorator


def applyVerifyPenalty(confidence: int, *, verifyOk: bool) -> int:
    """verify_answer 실패 시 -50 페널티. 0 미만으로는 떨어지지 않음."""
    if verifyOk:
        return confidence
    return max(0, confidence - 50)


__all__ = [
    "ConfidenceMethod",
    "baseScore",
    "label",
    "tagConfidence",
    "applyVerifyPenalty",
]
