"""Tool registry 부트스트랩.

앱/세션 시작 시 1회 호출하여 기본 tool 집합을 registry 에 등록한다.
멱등 (중복 호출 안전).
"""

from __future__ import annotations

from dartlab.ai.tools.adapters import HANDLERS
from dartlab.ai.tools.registry import AITool, getDefaultRegistry
from dartlab.ai.tools.schemas import buildToolSchemas


def bootstrapDefaultTools() -> None:
    """dartlab 공개 API tool 10종을 기본 registry 에 등록."""
    reg = getDefaultRegistry()
    schemas = buildToolSchemas()
    for schema in schemas:
        fn = schema["function"]
        name = fn["name"]
        handler = HANDLERS.get(name)
        if handler is None:
            continue  # 스키마는 있는데 핸들러 미등록 — 무시
        reg.register(
            AITool(
                name=name,
                description=fn["description"],
                parameters=fn["parameters"],
                handler=handler,
            )
        )


def ensureBootstrapped() -> None:
    """registry 가 비어있으면 bootstrap. 멱등."""
    reg = getDefaultRegistry()
    if not reg.tools:
        bootstrapDefaultTools()
