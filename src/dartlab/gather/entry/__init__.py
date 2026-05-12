"""gather entry — `dartlab.gather()` 콜러블 진입점 패키지.

thin facade. 구현:
    - `dispatch.py` — _AXIS_REGISTRY (12 axis 메타), _ALIASES, _API_KEY_INFO,
      _INDEX_SYMBOLS, _resolveAxis, _fetchNaverIndex, TargetType, _GatherAxisEntry
    - `main.py` — GatherEntry 클래스 (__call__ / _run / _guide / _apiKeyGuide / __repr__)
    - `providerAdapter.py` — _GatherProviderAdapter + getDefaultGather + 자동 register

외부 caller (10+ 호출부):
    - dartlab.gather.entry — getDefaultGather, GatherEntry, _AXIS_REGISTRY, _ALIASES, _API_KEY_INFO, TargetType
    - dartlab.gather — getDefaultGather (re-export 경유)
"""

from __future__ import annotations

from .dispatch import (
    _ALIASES,
    _API_KEY_INFO,
    _AXIS_REGISTRY,
    _INDEX_SYMBOLS,
    TargetType,
    _GatherAxisEntry,
)
from .main import GatherEntry
from .providerAdapter import getDefaultGather

# providerAdapter import 시 _registerGatherProvider 자동 호출 (side-effect).

__all__ = [
    "GatherEntry",
    "TargetType",
    "_ALIASES",
    "_API_KEY_INFO",
    "_AXIS_REGISTRY",
    "_GatherAxisEntry",
    "_INDEX_SYMBOLS",
    "getDefaultGather",
]
