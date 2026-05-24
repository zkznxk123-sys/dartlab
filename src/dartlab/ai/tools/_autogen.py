"""ai/tools/_autogen — engine 함수 → tool wrapper 자동 변환 (T11-1).

dartlab 의 분석 엔진 (analysis / credit / macro / quant / industry / scan / story)
의 public 함수를 LLM tool-call 인터페이스로 자동 변환. 수동 등록한 32 tool 외에
약 120+ engine 함수를 추가 노출.

전략:
    1. dartlab 의 sub-namespace 순회 (analysis / credit / macro / quant / industry / scan / story)
    2. 각 모듈의 `__all__` 또는 public 함수 (이름이 underscore 안 시작) 수집
    3. 시그니처 inspect 로 input schema 추출 (type annotation 필수)
    4. docstring 첫 줄 → description
    5. tool wrapper 생성 (LLM tool-call dict 포맷)

본 v1 은 *최소 scaffold* — 실제 LLM tool 등록 + MCP 노출은 후속.

실행::

    >>> from dartlab.ai.tools._autogen import generateToolSchemas
    >>> schemas = generateToolSchemas()
    >>> print(f"{len(schemas)} tool schemas auto-generated")
    120 tool schemas auto-generated
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any

# 자동 변환 대상 sub-namespace.
_TARGET_NAMESPACES: tuple[str, ...] = (
    "dartlab.analysis",
    "dartlab.credit",
    "dartlab.macro",
    "dartlab.quant",
    "dartlab.industry",
    "dartlab.scan",
    "dartlab.story",
)


def _annotationToSchema(annotation: Any) -> dict[str, str]:
    """type annotation → JSON schema fragment (간단 변환).

    완전한 JSON Schema 변환은 후속 (pydantic.TypeAdapter 등 활용).
    """
    if annotation is inspect.Parameter.empty:
        return {"type": "any"}
    name = getattr(annotation, "__name__", str(annotation))
    mapping = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "tuple": "array",
        "set": "array",
        "None": "null",
        "NoneType": "null",
    }
    return {"type": mapping.get(name, "any"), "pythonType": name}


def _functionToSchema(name: str, func: Any) -> dict[str, Any] | None:
    """단일 public function → tool schema dict.

    Returns:
        {name, description, parameters: {type, properties, required}}. type annotation
        부재 또는 시그니처 inspect 실패 시 None.
    """
    if not (inspect.isfunction(func) or inspect.isbuiltin(func)):
        return None
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return None

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for paramName, param in sig.parameters.items():
        if paramName in ("self", "cls"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        properties[paramName] = _annotationToSchema(param.annotation)
        if param.default is inspect.Parameter.empty:
            required.append(paramName)

    doc = inspect.getdoc(func) or ""
    description = doc.split("\n", 1)[0].strip()[:200]

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def generateToolSchemas() -> list[dict[str, Any]]:
    """대상 sub-namespace 순회 → tool schema list 반환 (T10-4).

    Capabilities:
        7 분석 엔진 (analysis/credit/macro/quant/industry/scan/story) 의 public
        함수를 LLM tool-call dict 로 자동 변환. 32 수동 등록 외 120+ 추가 노출
        (T11-1).

    Args:
        없음 (대상 namespace 는 _TARGET_NAMESPACES 상수).

    Returns:
        list[dict] — 각 entry: name / description / parameters (JSON Schema-like).

    Example:
        >>> from dartlab.ai.tools._autogen import generateToolSchemas
        >>> schemas = generateToolSchemas()
        >>> len(schemas)

    Guide:
        실제 LLM tool registry 등록 + MCP 노출은 후속 (T5-5). 본 함수는 *schema
        생성만*.

    SeeAlso:
        countAutoGenTools: quick count.
        dartlab.ai.agent: chat-native 본체.

    Requires:
        대상 namespace 의 public 함수가 type annotation + docstring 보유.

    AIContext:
        T11-1 워크벤치 tool 카탈로그 확장 트랙.

    Raises:
        없음 — 개별 namespace import 실패 silent skip.
    """
    schemas: list[dict[str, Any]] = []
    seenNames: set[str] = set()

    for moduleName in _TARGET_NAMESPACES:
        try:
            module = importlib.import_module(moduleName)
        except ImportError:
            continue

        # __all__ 우선 / 없으면 dir() 의 public 이름
        symbols = list(getattr(module, "__all__", []))
        if not symbols:
            symbols = [name for name in dir(module) if not name.startswith("_")]

        for sym in symbols:
            try:
                obj = getattr(module, sym)
            except AttributeError:
                continue
            # 충돌 방지 — 다른 namespace 와 같은 이름이면 namespace prefix 추가
            shortName = sym
            fullName = f"{moduleName.split('.')[-1]}_{sym}"
            schemaName = shortName if shortName not in seenNames else fullName
            schema = _functionToSchema(schemaName, obj)
            if schema is not None:
                schemas.append(schema)
                seenNames.add(schemaName)

    return schemas


def countAutoGenTools() -> int:
    """자동 생성 가능한 tool 수 — quick measure (T10-4).

    Returns:
        generateToolSchemas() 결과 length.

    Example:
        >>> from dartlab.ai.tools._autogen import countAutoGenTools
        >>> countAutoGenTools()
        120  # 예시

    SeeAlso:
        generateToolSchemas: 실제 schema list.

    AIContext:
        T11-1 진척 추적 — metrics workflow 가 시계열 측정.
    """
    return len(generateToolSchemas())


__all__ = ["generateToolSchemas", "countAutoGenTools"]
