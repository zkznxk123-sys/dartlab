"""분석 lens 패널 (P5).

질문 난이도가 임계 넘으면 BRIEF 가 단일 분석가 대신 lens 패널로 분기.
각 lens 는 같은 도구를 쓰되 시각이 다르다 — system prompt 차이 + capability 힌트로 표현.
"""

from .fundamental import FUNDAMENTAL_LENS
from .macro import MACRO_LENS
from .sentiment import SENTIMENT_LENS
from .technical import TECHNICAL_LENS
from .types import Lens

LENSES: dict[str, Lens] = {
    "fundamental": FUNDAMENTAL_LENS,
    "macro": MACRO_LENS,
    "technical": TECHNICAL_LENS,
    "sentiment": SENTIMENT_LENS,
}

__all__ = [
    "FUNDAMENTAL_LENS",
    "LENSES",
    "Lens",
    "MACRO_LENS",
    "SENTIMENT_LENS",
    "TECHNICAL_LENS",
]
