"""AI context 헬퍼 — post-response 학습 + tool_result 직렬화 보조.

사상 (src/dartlab/ai/README.md): AI 가 모든 엔진을 tool 로 자율 호출. 사전 주입/떠먹이기는 없다.
이 패키지는 **응답 후** 학습 루프(intent/playbook) 와 **tool_result** 의 맥락 보강(aiview) 만 담당.
"""

from __future__ import annotations

from dartlab.ai.context.aiview import autoEnrich
from dartlab.ai.context.intent import Intent, classifyIntent
from dartlab.ai.context.playbook import curate, extractBullets, retrieveBullets

__all__ = [
    "Intent",
    "autoEnrich",
    "classifyIntent",
    "curate",
    "extractBullets",
    "retrieveBullets",
]
