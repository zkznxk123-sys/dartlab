"""Reference mapper engine factory.

Capabilities:
    - Builds and caches the unified mapper engine used by account/topic/alias/flow lookups.

Args:
    Public factory takes no arguments.

Returns:
    A cached ``MapperEngine`` instance.

Example:
    >>> from dartlab.reference.mappers.engine import getEngine
    >>> engine = getEngine()

Guide:
    Keep registration logic here, not in package ``__init__``. Package init should only re-export.

SeeAlso:
    ``dartlab.reference.mappers`` and ``dartlab.core.mapperEngine``.

Requires:
    Reference mapper classes and provider mapper adapters import successfully.

AIContext:
    Provides one stable mapper registry so callers do not instantiate individual mappers ad hoc.

LLM Specifications:
    AntiPatterns: Do not import this from lower-level core modules.
    OutputSchema: ``MapperEngine`` with registered mapper instances.
    Prerequisites: Mapper data files are available in package resources.
    Freshness: Cached until process restart or explicit cache clear by tests.
    Dataflow: factory -> mapper instances -> MapperEngine registry.
    TargetMarkets: KR/US reference mapping internals.
"""

from __future__ import annotations

from functools import lru_cache

from dartlab.core.mapperEngine import MapperEngine


@lru_cache(maxsize=1)
def getEngine() -> MapperEngine:
    """Return the cached unified mapper engine.

    Capabilities:
        Registers account, topic, alias, flow, notes, and parser mappers in one engine.

    AIContext:
        This is the canonical entry point for mapper consumers and avoids duplicate registries.

    Guide:
        Import from ``dartlab.reference.mappers`` for public callers; keep implementation here.

    When:
        Called on first mapper use and then served from the process-local cache.

    How:
        Lazily imports mapper classes, creates ``MapperEngine``, registers each mapper, and caches it.

    Args:
        None.

    Returns:
        ``MapperEngine`` with account, topic, alias, flow, notes, and parser mappers registered.

    Requires:
        Reference and provider mapper classes import successfully.

    Raises:
        ImportError when a mapper implementation cannot be imported.

    Example:
        >>> getEngine() is getEngine()
        True

    SeeAlso:
        ``dartlab.reference.mappers`` and ``dartlab.core.mapperEngine.MapperEngine``.
    """
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
