"""ContextBuilder selectors — Intent별 컨텍스트 생산자.

각 selector는 (question, company, intent) → list[ContextPart] 형태.
순수 함수, 부수효과 없음. 실패 시 빈 리스트 반환 (에러 전파 금지).

Phase 1 (현재):
    legacy.py — 기존 ai/runtime/core.py의 pre-grounding 5개 헬퍼 래핑
                (손실 없는 이주, A/B 비교 가능)

Phase 1.5 (다음):
    act1~6.py, compare.py, concept.py — analysis calc 결과를 intent별로 선택 주입
"""

from __future__ import annotations

from dartlab.ai.context.selectors.legacy import (
    selectCompanySearch,
    selectDisclosureBrief,
    selectExternalSearch,
    selectInsightHints,
    selectMemoryHints,
)
from dartlab.ai.context.selectors.playbook import selectPlaybookBullets

__all__ = [
    "selectCompanySearch",
    "selectDisclosureBrief",
    "selectExternalSearch",
    "selectInsightHints",
    "selectMemoryHints",
    "selectPlaybookBullets",
]
