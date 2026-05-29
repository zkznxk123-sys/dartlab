"""filings.core — 시장 무관 공통 (모든 market backend 가 의존).

구성:
    - ``schema`` — sections 14-col schema SSOT (cross-market 계약).
    - ``sections`` — RUNTIME canonical pivot reader (scan/meta/wide/long).
    - ``bridge`` — disclosureKey bridge SSOT (KR+US+… seed).
    - ``canonical`` — rawId(ACLASS/concept) → disclosureKey.
    - ``tagstrip`` — contentRaw → plain (polars expr, 사전파생 0).
    - ``period`` — period(YYYYQn) 정규화 공통.
    - ``loader`` — HF download 공통 (market 가 repo/path 주입).
    - ``memory`` — BoundedCache + Company context-manager 가드.
    - ``backend`` — MarketBackend Protocol.

의존: dartlab.config(dataDir) + polars + (loader 한정) huggingface_hub 만.
providers/scan/dataLoader 의존 0.
"""

from __future__ import annotations

__all__: list[str] = []
