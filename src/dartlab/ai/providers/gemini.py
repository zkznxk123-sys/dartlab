"""Google Gemini provider.

인증: API key (AI Studio에서 무료 발급)
- https://aistudio.google.com/apikey 에서 발급
- GEMINI_API_KEY 또는 GOOGLE_API_KEY 환경변수, 또는 설정 패널에서 입력
"""

from __future__ import annotations

import logging
from typing import Generator

from dartlab.ai.providers.base import BaseProvider
from dartlab.ai.types import LLMConfig, LLMResponse, ToolCall, ToolResponse

_log = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _getClient(self):
        if self._client is not None:
            return self._client
        try:
            from google import genai
        except ImportError:
            raise ImportError("google-genai 패키지가 필요합니다.\n  pip install google-genai")

        import os

        apiKey = self.config.apiKey
        if not apiKey:
            apiKey = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if not apiKey:
            raise ValueError(
                "Gemini API key가 필요합니다.\n"
                "  발급: https://aistudio.google.com/apikey (무료)\n"
                "  설정: GEMINI_API_KEY 환경변수 또는 설정 패널에서 입력"
            )

        self._client = genai.Client(apiKey=apiKey)
        return self._client

    @property
    def defaultModel(self) -> str:
        """defaultModel — TODO 한국어 동작 설명."""
        return "gemini-2.5-flash"

    @property
    def supportsNativeTools(self) -> bool:
        """supportsNativeTools — TODO 한국어 동작 설명."""
        return True

    def checkAvailable(self) -> bool:
        """checkAvailable — TODO 한국어 동작 설명."""
        try:
            self._getClient()
            return True
        except (ImportError, ValueError, OSError):
            return False

    def complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        """complete — TODO 한국어 동작 설명."""
        client = self._getClient()
        systemInstruction, contents = _splitSystemAndContents(messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.maxTokens,
        )
        if systemInstruction:
            config.system_instruction = systemInstruction

        response = client.models.generate_content(
            model=self.resolvedModel,
            contents=contents,
            config=config,
        )

        usage = None
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        return LLMResponse(
            answer=response.text or "",
            provider="gemini",
            model=self.resolvedModel,
            usage=usage,
        )

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """stream — TODO 한국어 동작 설명."""
        client = self._getClient()
        systemInstruction, contents = _splitSystemAndContents(messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.maxTokens,
        )
        if systemInstruction:
            config.system_instruction = systemInstruction

        for chunk in client.models.generate_content_stream(
            model=self.resolvedModel,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text

    def completeWithTools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        toolChoice: str | None = None,
    ) -> ToolResponse:
        """completeWithTools — TODO 한국어 동작 설명."""
        client = self._getClient()
        from google.genai import types

        systemInstruction, contents = _splitSystemAndContents(messages)
        geminiTools = _convertToolsToGemini(tools)

        toolConfig = None
        if toolChoice == "any":
            toolConfig = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY"),
            )
        elif toolChoice == "none":
            toolConfig = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="NONE"),
            )

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.maxTokens,
            tools=geminiTools,
        )
        if toolConfig is not None:
            config.tool_config = toolConfig
        if systemInstruction:
            config.system_instruction = systemInstruction

        response = client.models.generate_content(
            model=self.resolvedModel,
            contents=contents,
            config=config,
        )

        usage = None
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        toolCalls: list[ToolCall] = []
        answer = ""
        finishReason = "stop"

        if response.candidates:
            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if part.text:
                    answer += part.text
                if part.function_call:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    toolCalls.append(
                        ToolCall(
                            id=f"call_{fc.name}_{len(toolCalls)}",
                            name=fc.name,
                            arguments=args,
                        )
                    )
            if toolCalls:
                finishReason = "tool_calls"

        return ToolResponse(
            answer=answer,
            provider="gemini",
            model=self.resolvedModel,
            usage=usage,
            toolCalls=toolCalls,
            finish_reason=finishReason,
        )

    def formatAssistantToolCalls(
        self,
        answer: str | None,
        toolCalls: list,
    ) -> dict:
        """formatAssistantToolCalls — TODO 한국어 동작 설명."""
        from google.genai import types

        parts = []
        if answer:
            parts.append(types.Part(text=answer))
        for tc in toolCalls:
            parts.append(types.Part(function_call=types.FunctionCall(name=tc.name, args=tc.arguments)))
        return {"role": "model", "parts": parts, "_gemini_native": True}

    def formatToolResult(self, toolCallId: str, result: str) -> dict:
        """formatToolResult — TODO 한국어 동작 설명."""
        from google.genai import types

        name = toolCallId
        if name.startswith("call_") and "_" in name[5:]:
            name = name[5:].rsplit("_", 1)[0]
        parts = [types.Part(function_response=types.FunctionResponse(name=name, response={"result": result}))]
        return {"role": "user", "parts": parts, "_gemini_native": True}


def _splitSystemAndContents(messages: list[dict]) -> tuple[str | None, list]:
    system = None
    contents = []

    for msg in messages:
        if msg.get("_gemini_native"):
            role = msg.get("role", "user")
            contents.append({"role": role, "parts": msg["parts"]})
            continue

        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system = content
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content or ""}]})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"[Tool Result] {content}"}],
                }
            )
        else:
            contents.append({"role": "user", "parts": [{"text": content or ""}]})

    return system, contents


def _convertToolsToGemini(tools: list[dict]) -> list:
    from google.genai import types

    declarations = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        func = tool["function"]
        params = func.get("parameters", {})

        cleanedParams = _cleanSchemaForGemini(params)

        declarations.append(
            types.FunctionDeclaration(
                name=func["name"],
                description=func.get("description", ""),
                parameters=cleanedParams if cleanedParams.get("properties") else None,
            )
        )

    if not declarations:
        return []
    return [types.Tool(function_declarations=declarations)]


def _cleanSchemaForGemini(schema: dict) -> dict:
    cleaned = {}
    for key, value in schema.items():
        if key in ("additionalProperties", "$schema"):
            continue
        if isinstance(value, dict):
            cleaned[key] = _cleanSchemaForGemini(value)
        elif isinstance(value, list):
            cleaned[key] = [_cleanSchemaForGemini(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
    return cleaned
