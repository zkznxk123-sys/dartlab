"""dartlab 외부 plugin 로더 — entry_points 기반 discover + introspection (T5-1).

외부 plugin 패키지가 `pyproject.toml [project.entry-points."dartlab.plugins"]`
선언으로 dartlab 에 새 recipe / engine / tool 을 등록할 수 있다.

목적:
    - 외부 기여자가 dartlab fork 없이 *분석 recipe 1 개* 추가 가능
    - 회사 내부 / private plugin 도 동일 인터페이스

API:
    discoverPlugins() -> list[PluginDescriptor]  # entry_points 스캔
    loadPlugin(name) -> module
    listPlugins() -> list[dict]   # introspection (dartlab.plugins.list 진입점)

Example::

    >>> from dartlab.core.plugins import discoverPlugins
    >>> for d in discoverPlugins():
    ...     print(d.name, d.kind, d.version)

후속 트랙:
    - T5-2 plugin example 패키지 (examples/plugin-example/)
    - T5-5 introspection API (dartlab.plugins namespace + MCP ListPlugins)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from importlib.metadata import entry_points
from types import ModuleType
from typing import Any

_ENTRY_GROUP = "dartlab.plugins"


@dataclass
class PluginDescriptor:
    """단일 plugin 메타 — entry_points 스캔 결과."""

    name: str
    moduleName: str
    kind: str = "unknown"  # "scan" / "analysis" / "tool" / "recipe" / "unknown"
    version: str = "0.0.0"
    distName: str = ""  # 배포 패키지 이름
    docstring: str = ""
    schema: dict[str, Any] = field(default_factory=dict)


def discoverPlugins() -> list[PluginDescriptor]:  # noqa: N802  (Python convention)
    """`dartlab.plugins` entry group 의 plugin 목록 메타 수집.

    동일 name 충돌 시: 첫 발견 우선 + warning (silent — logger.warn).

    Returns:
        PluginDescriptor 리스트 (sorted by name).
    """
    descriptors: dict[str, PluginDescriptor] = {}
    try:
        eps = entry_points(group=_ENTRY_GROUP)
    except TypeError:
        # Python <= 3.9 의 dict-based API fallback
        try:
            eps = entry_points().get(_ENTRY_GROUP, [])  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            return []

    for ep in eps:
        if ep.name in descriptors:
            # 중복 — 첫 발견 우선 (logger.warn 도 가능, 본 v1 은 silent)
            continue
        # 메타 수집 — load 는 lazy
        descriptor = PluginDescriptor(
            name=ep.name,
            moduleName=ep.value,
            distName=getattr(ep.dist, "name", "") if hasattr(ep, "dist") and ep.dist else "",
            version=getattr(ep.dist, "version", "0.0.0") if hasattr(ep, "dist") and ep.dist else "0.0.0",
        )
        descriptors[ep.name] = descriptor

    return sorted(descriptors.values(), key=lambda d: d.name)


def loadPlugin(name: str) -> ModuleType:  # noqa: N802
    """지정된 plugin 의 모듈 로드 + 메타 보강.

    Args:
        name: entry_point 이름.

    Returns:
        로드된 모듈.

    Raises:
        KeyError: 해당 name 의 plugin 없음.
        ImportError: 모듈 import 실패.
    """
    for d in discoverPlugins():
        if d.name == name:
            module = import_module(d.moduleName)
            # 메타 보강 — docstring + schema (선택)
            d.docstring = (getattr(module, "__doc__", "") or "").strip()[:200]
            if hasattr(module, "PLUGIN_KIND"):
                d.kind = str(module.PLUGIN_KIND)
            if hasattr(module, "PLUGIN_SCHEMA"):
                schema = module.PLUGIN_SCHEMA
                if isinstance(schema, dict):
                    d.schema = dict(schema)
            return module
    raise KeyError(f"plugin not found: {name!r}")


def listPlugins() -> list[dict[str, Any]]:  # noqa: N802
    """introspection — dict list 반환 (외부 LLM / MCP tool 호환).

    각 entry: `{name, moduleName, kind, version, distName, docstring}`.
    docstring/schema 는 load 후에만 채워지므로 본 함수는 *전체 load* 후 dict 변환.
    """
    plugins: list[dict[str, Any]] = []
    for d in discoverPlugins():
        try:
            loadPlugin(d.name)
        except (KeyError, ImportError):
            pass
        plugins.append(
            {
                "name": d.name,
                "moduleName": d.moduleName,
                "kind": d.kind,
                "version": d.version,
                "distName": d.distName,
                "docstring": d.docstring,
                "schema": d.schema,
            }
        )
    return plugins


def describePlugin(name: str) -> dict[str, Any]:  # noqa: N802
    """단일 plugin 상세 — load 후 dict 반환.

    Raises:
        KeyError: plugin 없음.
    """
    for d in discoverPlugins():
        if d.name == name:
            loadPlugin(name)
            return {
                "name": d.name,
                "moduleName": d.moduleName,
                "kind": d.kind,
                "version": d.version,
                "distName": d.distName,
                "docstring": d.docstring,
                "schema": d.schema,
            }
    raise KeyError(f"plugin not found: {name!r}")


__all__ = [
    "PluginDescriptor",
    "discoverPlugins",
    "loadPlugin",
    "listPlugins",
    "describePlugin",
]
