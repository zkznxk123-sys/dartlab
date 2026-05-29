"""providersV2 — providers 의 깨끗한 재정립 (다시장 disclosure, drop-in 교체 대상).

Phase 1: dart sections 사전빌드 기반. edgar / show / diff / meta facade 는 후속 phase.
공개 표면 SSOT — caller 는 본 패키지 또는 하위 패키지 표면만 import
(deep leaf path 금지 — feedback_clean_module_tree).
"""

from __future__ import annotations

from . import dart

__all__ = ["dart"]
