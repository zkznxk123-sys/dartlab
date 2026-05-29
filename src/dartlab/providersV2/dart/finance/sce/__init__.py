"""SCE (자본변동표) — 2-tier 정규화 + matrix 빌드 (변동사유 × 자본항목 × period).

cause/detail 정규화는 ``sceMapper``/``sceMapperNormalize``, matrix 빌드는
``pivotSce``. 공개 표면은 본 __init__.
"""

from __future__ import annotations

from .pivotSce import buildSceAnnual, buildSceMatrix

__all__ = ["buildSceAnnual", "buildSceMatrix"]
