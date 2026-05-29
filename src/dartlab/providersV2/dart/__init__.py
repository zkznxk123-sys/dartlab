"""DART (KR) market provider — providersV2.

Phase 1: sections 사전빌드 + runtime reader. finance / report / openapi / search /
Company facade 는 후속 phase. 공개 표면은 본 __init__ 에 모은다
(feedback_clean_module_tree).
"""

from __future__ import annotations

from . import sections

__all__ = ["sections"]
