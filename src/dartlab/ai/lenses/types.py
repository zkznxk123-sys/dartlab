"""Lens dataclass — 분석 시각의 형태 정의."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lens:
    """분석 시각.

    - name: lens 식별자 (fundamental / macro / technical / sentiment)
    - promptPatch: lens 활성 시 system prompt 에 주입할 텍스트
    - capabilityHints: 이 lens 에서 우선 사용해야 할 capability 식별자 목록 — LLM 이
      ReadCapability 결과 정렬 / RunPython 자동 import 힌트로 활용
    """

    name: str
    promptPatch: str
    capabilityHints: list[str] = field(default_factory=list)


__all__ = ["Lens"]
