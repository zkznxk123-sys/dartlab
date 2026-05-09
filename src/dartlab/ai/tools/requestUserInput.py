"""RequestUserInput — MCP elicit_form 표면화 도구.

ask 가 ambiguity 만나면 자연어 질문으로 응답하는 패턴 → schema 있는 *structured* 사용자
입력 요청으로 격상. MCP 클라이언트 (Claude Desktop 등) 가 폼 UI 로 렌더링 → 사용자 응답을
구조화된 dict 으로 받는다.

이 도구의 sync 함수는 *non-MCP 컨텍스트의 fallback only*. 실제 elicit 호출은 mcp/__init__.py
의 call_tool handler 가 RequestContext.session.elicit_form 으로 직접 dispatch — sync
registry executor 시그니처에 async session 의존을 끼워넣는 것을 피하기 위함.
"""

from __future__ import annotations

from typing import Any

from .types import ToolResult


def buildElicitSchema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """fields 단순 dict 리스트를 JSON Schema (object) 로 변환.

    각 field 는 {name, description?, type?, enum?} dict.
    type 미지정 시 "string". enum 있으면 enum 검증.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in fields or []:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "").strip()
        if not name:
            continue
        prop: dict[str, Any] = {"type": str(field.get("type") or "string")}
        desc = field.get("description")
        if desc:
            prop["description"] = str(desc)
        if "enum" in field and isinstance(field["enum"], list):
            prop["enum"] = list(field["enum"])
        properties[name] = prop
        if field.get("required") is not False:
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def requestUserInput(
    *,
    message: str,
    fields: list[dict[str, Any]] | None = None,
) -> ToolResult:
    """*Non-MCP* 컨텍스트 fallback. MCP 컨텍스트에선 call_tool handler 가 직접 dispatch.

    fields 예시: ``[{"name": "company", "description": "분석할 회사", "enum": ["005930", "AAPL"]}]``.

    MCP 외 환경 (CLI 직접 ask 등) 에서 호출되면 ok=False 반환 — 호출자가 자연어 fallback 으로
    분기. tool 자체는 안 깨짐.
    """
    schema = buildElicitSchema(fields or [])
    return ToolResult(
        ok=False,
        summary="RequestUserInput 은 MCP 컨텍스트 전용 — 현재 transport 가 elicit 미지원. 자연어 응답 fallback 권장.",
        data={"message": str(message or ""), "requestedSchema": schema, "fallback": True},
        error="elicit_unsupported_transport",
    )
