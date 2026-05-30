"""DART (KR) market provider — providersV2 (read plane).

read facade ``Company`` (역할 1: 로컬 read) + finance / report / sections reader.
네트워크(역할 2)는 gather 위임, 엔진(역할 3)은 core 레지스트리 IoC — 후속 phase.
공개 표면은 본 __init__ 에 모은다 (feedback_clean_module_tree).
"""

from __future__ import annotations

from . import finance, report, sections
from .company import Company

__all__ = ["Company", "finance", "report", "sections"]
