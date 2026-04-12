"""SuperMaster — AI가 dartlab 전체를 동적으로 아는 수퍼마스터 기능.

두 개의 인덱스 위에서 작동한다:
- CapabilityIndex: CAPABILITIES dict에서 질문 관련 API를 검색
- ExperienceIndex: KnowledgeDB.executions에서 과거 성공 사례를 검색

하부 엔진이 어떻게 확장되어도 AI가 자동 적응한다. 매뉴얼 수정 0.
"""

from dartlab.ai.superfeature.capability_index import CapabilityIndex, getCapabilityIndex
from dartlab.ai.superfeature.experience_index import ExperienceIndex, getExperienceIndex
from dartlab.ai.superfeature.master import SuperMaster, getSuperMaster

__all__ = [
    "CapabilityIndex",
    "ExperienceIndex",
    "SuperMaster",
    "getCapabilityIndex",
    "getExperienceIndex",
    "getSuperMaster",
]
