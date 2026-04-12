"""SuperMaster — Retrieval + Experience 통합 진입점.

AI가 dartlab을 "당연히 아는 것처럼" 쓰게 만드는 수퍼마스터.
매 질문마다 동적으로:
1. 관련 API (CAPABILITIES에서 top-k)
2. 과거 성공 사례 (experience에서 top-k)
을 ContextPart로 반환한다.

하부 엔진이 81개든 200개든 자동 적응.
"""

from __future__ import annotations

import logging

from dartlab.ai.superfeature.capability_index import getCapabilityIndex
from dartlab.ai.superfeature.experience_index import getExperienceIndex

log = logging.getLogger(__name__)


class SuperMaster:
    """AI의 수퍼마스터 — Retrieval + Experience 루프.

    ContextBuilder에서 질문당 1회 호출.
    실패해도 조용히 빈 리스트 (graceful degradation).
    """

    def __init__(self) -> None:
        self._cap = getCapabilityIndex()
        self._exp = getExperienceIndex()

    def gather(
        self,
        question: str,
        *,
        stockCode: str | None = None,
        apiK: int = 5,
        exampleK: int = 3,
    ) -> tuple[str, str]:
        """질문에 대한 관련 API + 과거 성공 사례를 수집.

        Args:
            question: 사용자 질문
            stockCode: 종목코드 (있으면 경험 검색에 가점)
            apiK: 반환할 API 개수
            exampleK: 반환할 성공 사례 개수

        Returns:
            (api_text, example_text) — 프롬프트 주입용 마크다운.
            실패 시 ("", "") 반환.
        """
        api_text = ""
        example_text = ""

        try:
            hits = self._cap.search(question, k=apiK)
            api_text = self._cap.formatForPrompt(hits)
        except Exception as e:
            log.debug("SuperMaster capability search 실패 %s", e)

        try:
            exps = self._exp.search(question, stockCode=stockCode, k=exampleK)
            example_text = self._exp.formatForPrompt(exps)
        except Exception as e:
            log.debug("SuperMaster experience search 실패 %s", e)

        return api_text, example_text


# 싱글턴
_instance: SuperMaster | None = None


def getSuperMaster() -> SuperMaster:
    """싱글턴 SuperMaster 인스턴스."""
    global _instance
    if _instance is None:
        _instance = SuperMaster()
    return _instance
