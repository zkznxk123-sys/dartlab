"""reference mapper engine factory."""

from __future__ import annotations

from functools import lru_cache

from dartlab.core.mapperEngine import MapperEngine


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


__all__ = ["getEngine"]
