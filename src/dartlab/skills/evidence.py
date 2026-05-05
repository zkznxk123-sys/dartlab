"""Evidence helpers for shared DartLab skills."""

from __future__ import annotations

from .models import EvidenceCheckResult
from .registry import checkEvidence

__all__ = ["checkEvidence", "EvidenceCheckResult"]
