"""gather entry — `dartlab.gather()` 콜러블 진입점 패키지.

thin facade. 구현:
    - `dispatch.py` — AXIS_REGISTRY (13 axis 메타: 공개 11 + 베타 hidden 2), AXIS_ALIASES,
      API_KEY_INFO, INDEX_SYMBOLS, _resolveAxis, _fetchNaverIndex, TargetType, GatherAxisEntry
    - `main.py` — GatherEntry 클래스 (__call__ / _run / _guide / __repr__)
    - `providerAdapter.py` — _GatherProviderAdapter + getDefaultGather + 자동 register

외부 caller (10+ 호출부):
    - dartlab.gather.entry — getDefaultGather, GatherEntry, AXIS_REGISTRY, AXIS_ALIASES, API_KEY_INFO, TargetType
    - dartlab.gather — getDefaultGather (re-export 경유)
"""

from __future__ import annotations

from .dispatch import (
    API_KEY_INFO,
    AXIS_ALIASES,
    AXIS_REGISTRY,
    INDEX_SYMBOLS,
    GatherAxisEntry,
    TargetType,
)
from .main import GatherEntry
from .providerAdapter import getDefaultGather

# providerAdapter import 시 _registerGatherProvider 자동 호출 (side-effect).

__all__ = [
    "API_KEY_INFO",
    "AXIS_ALIASES",
    "AXIS_REGISTRY",
    "GatherAxisEntry",
    "GatherEntry",
    "INDEX_SYMBOLS",
    "TargetType",
    "getDefaultGather",
]
