"""ParseChart — multimodal vision 도구.

runtime.multimodal SSOT — 차트/PDF 이미지 → JSON schema 추출. 결과 자동
wrap_external_in_result (untrusted tier).

Status: stub — 실 vision API 호출은 별 commit (외부 SDK 의존성 추가 후).

Sig
---
parseChart(imagePath: str, schema: dict, sourceUrl: str = "") -> ToolResult

Args
----
imagePath : str — 이미지 파일 path 또는 URL
schema : dict — 추출할 JSON schema (필수, free-form 금지)
sourceUrl : str — 원본 URL (untrusted wrap 용)

Returns
-------
ToolResult — data 안 extracted JSON + sentinel 마커 wrap

Example
-------
result = parseChart("chart.png", schema={"type": "object"}, sourceUrl="...")
"""

from __future__ import annotations

from .types import ToolResult


def parseChart(imagePath: str, schema: dict, sourceUrl: str = "") -> ToolResult:
    """multimodal 차트/PDF parse.

    Stub: vision API 미활성. 현재는 빈 결과 + drafted 표기.
    """
    if not imagePath or not imagePath.strip():
        return ToolResult(False, "imagePath 미지정", error="missing_image")
    if not schema:
        return ToolResult(
            False,
            "schema 강행 (free-form 추출 금지 — runtime.multimodal SSOT)",
            error="missing_schema",
        )

    data = {
        "imagePath": imagePath,
        "schema": schema,
        "sourceUrl": sourceUrl,
        "extracted": {},
        "status": "drafted — vision API 미활성",
    }
    # 실 vision API 시 Ref(sourceType="external") 추가 + wrapExternalInResult(result.toDict()) 적용
    return ToolResult(True, "parseChart stub", data=data)
