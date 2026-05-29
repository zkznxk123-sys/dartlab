"""canonicalResolver — raw ACLASS / TextBlock → universal disclosureKey.

Layer 1 (rawId, marketNs) + Layer 3 bridge → disclosureKey (snakeId SSOT).

LLM Specifications:
    AntiPatterns:
        - 직접 hardcoded 매핑 금지 — bridge parquet 만 활용.
        - 매번 bridge read 금지 — lru_cache dict 사용.
        - unmapped rawId 에 None 반환 강제 — silent fallback (mapper 회귀 위험).
    OutputSchema:
        - ``resolveDisclosureKey(rawId, marketNs) -> str | None``
        - ``resolveBatch(df: pl.DataFrame) -> pl.DataFrame`` 신 컬럼 추가.
    Prerequisites:
        - data/bridge/sectionsBridge.parquet (seedBridgeTier1 후 존재).
    Freshness:
        - bridge parquet 변경 시 lookup dict cache invalidate.
    Dataflow:
        - rawId + marketNs → bridge.parquet 의 (rawId, marketNs) join →
          disclosureKey 반환.
    TargetMarkets:
        - KR + US 통합.
"""

from __future__ import annotations

from functools import lru_cache

import polars as pl

from .bridge import loadBridge


@lru_cache(maxsize=1)
def _lookupDict() -> dict[tuple[str, str], str]:
    """bridge parquet → ``(rawId, marketNs) -> disclosureKey`` dict.

    tier1 (confidence=1.0) 우선. 동일 (rawId, marketNs) 가 tier2/3 있으면
    tier1 채택.
    """
    bridge = loadBridge()
    if bridge.is_empty():
        return {}
    sorted_df = bridge.sort("tier")
    out: dict[tuple[str, str], str] = {}
    for row in sorted_df.iter_rows(named=True):
        k = (row["rawId"], row["marketNs"])
        if k not in out:
            out[k] = row["disclosureKey"]
    return out


def resolveDisclosureKey(rawId: str | None, marketNs: str) -> str | None:
    """단일 rawId → disclosureKey (또는 None).

    Args:
        rawId: Layer 1 rawId (DART: "NT_C_D826380", US: "us-gaap:...TextBlock").
        marketNs: "kr" / "us".

    Returns:
        disclosureKey or None (unmapped).
    """
    if not rawId:
        return None
    return _lookupDict().get((rawId, marketNs))


def resolveBatch(df: pl.DataFrame, *, marketNs: str) -> pl.DataFrame:
    """sections artifact DataFrame → disclosureKey 컬럼 부착.

    Args:
        df: sections artifact (14 col). ``xbrlClass`` 컬럼 활용.
        marketNs: 빌드 시장 ("kr" / "us").

    Returns:
        ``disclosureKey`` 컬럼이 채워진 DataFrame.

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["NT_C_D826380", "UNKNOWN"]})
        >>> out = resolveBatch(df, marketNs="kr")  # doctest: +SKIP
        >>> out["disclosureKey"].to_list()  # doctest: +SKIP
        ['inventoryDisclosure', None]
    """
    if df.is_empty() or "xbrlClass" not in df.columns:
        return df
    lookup = _lookupDict()
    # polars apply via map_elements 가 빠르진 않지만 row 수 적어 OK
    keys = df["xbrlClass"].map_elements(
        lambda x: lookup.get((x, marketNs)) if x else None,
        return_dtype=pl.Utf8,
    )
    if "disclosureKey" in df.columns:
        return df.with_columns(keys.alias("disclosureKey"))
    return df.with_columns(keys.alias("disclosureKey"))


def invalidateCache() -> None:
    """bridge parquet 변경 후 호출 — lru_cache 초기화."""
    _lookupDict.cache_clear()
    loadBridge.cache_clear()
