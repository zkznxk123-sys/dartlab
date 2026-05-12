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

from functools import lru_cache

from dartlab.core.mapperEngine import BaseMapper, MapperEngine, MapperStats


@lru_cache(maxsize=1)
def getEngine() -> MapperEngine:
    """매퍼 엔진 싱글턴. 6개 매퍼 자동 등록."""
    from dartlab.providers.mappers.notesMapper import NotesMapper
    from dartlab.providers.mappers.parserMapper import ParserMapper
    from dartlab.reference.mappers.accountMapper import AccountMapper
    from dartlab.reference.mappers.aliasMapper import AliasMapper
    from dartlab.reference.mappers.flowMapper import FlowMapper
    from dartlab.reference.mappers.topicMapper import TopicMapper

    engine = MapperEngine()
    engine.register(AccountMapper())
    engine.register(TopicMapper())
    engine.register(AliasMapper())
    engine.register(FlowMapper())
    engine.register(NotesMapper())
    engine.register(ParserMapper())
    return engine


__all__ = [
    "BaseMapper",
    "MapperEngine",
    "MapperStats",
    "getEngine",
]
