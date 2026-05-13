"""dartlab 매퍼 통합 엔진.

기존 매퍼 데이터를 읽기 전용으로 래핑하여 통합 인터페이스 제공.
원본 코드 수정 0줄 — 검증 완료 후 순차 교체.

사용법::

    from dartlab.reference.mappers import getEngine

    engine = getEngine()
    engine.summary()                          # 전체 매퍼 통계

    engine.get("account").lookup("매출액")     # 계정 매핑
    engine.get("topic").lookup("dividend")     # topic 키워드
    engine.get("alias").resolve("revenue")     # snakeId 정규화
    engine.get("flow").isEvent("dividends_paid")  # 이벤트 계정 판별
"""

from __future__ import annotations

from dartlab.core.mapperEngine import BaseMapper, MapperEngine, MapperStats
from dartlab.reference.mappers.engine import getEngine

__all__ = [
    "BaseMapper",
    "MapperEngine",
    "MapperStats",
    "getEngine",
]
