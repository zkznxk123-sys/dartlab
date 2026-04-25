"""macro 보고서 — story/macro/.

macro 엔진(L2)의 서사/빌더/보고서를 story(L3)로 이동.
macro 엔진은 dict만 반환, 서사 조립은 review가 담당.
"""

from .report import macroReport

__all__ = ["macroReport"]
