"""panel canonical resolver (L0) — raw ACLASS / us-gaap concept → disclosureKey.

(rawId, marketNs) + bridge SSOT → disclosureKey(snakeId). gather build(disclosureKey
채움) · providers reader(fallback) 공통 계약. 회사간·세계마켓간 정규화의 lookup 엔진.

LLM Specifications:
    AntiPatterns:
        - 직접 hardcoded 매핑 금지 — bridge parquet 만 활용.
        - 매번 bridge read 금지 — lru_cache dict.
        - unmapped rawId 에 임의 disclosureKey 부여 금지 — None 반환 (narrative fallback).
    OutputSchema:
        - ``resolveDisclosureKey(rawId, marketNs) -> str | None``.
        - ``resolveBatch(df, *, marketNs) -> pl.DataFrame`` (disclosureKey 컬럼 부착).
    Prerequisites:
        - polars. data/bridge/panelBridge.parquet (seedBridgeTier1 후 존재).
    Freshness:
        - bridge parquet 변경 시 invalidateCache.
    Dataflow:
        - rawId + marketNs → bridge lookup dict → disclosureKey.
    TargetMarkets:
        - KR + US 통합.
"""

from __future__ import annotations

from functools import lru_cache

import polars as pl

from .bridge import loadBridge


@lru_cache(maxsize=1)
def _lookupDict() -> dict[tuple[str, str], str]:
    """bridge parquet → ``(rawId, marketNs) -> disclosureKey`` dict (tier 우선).

    Args:
        없음.

    Returns:
        ``(rawId, marketNs) -> disclosureKey`` dict. 동일 키 다중 tier 시 tier1 우선.

    Raises:
        없음.

    Example:
        >>> d = _lookupDict()  # doctest: +SKIP
        >>> isinstance(d, dict)  # doctest: +SKIP
        True

    SeeAlso:
        - ``bridge.loadBridge`` — 원천 parquet.
        - ``invalidateCache`` — bridge 변경 후 무효화.

    Requires:
        - polars.

    Capabilities:
        - rawId lookup 의 메모리 dict (tier1 우선 — manual seed > corpus-learned).

    Guide:
        - 내부 helper — resolve* 경유.

    AIContext:
        - lru_cache — invalidateCache 로만 갱신.

    LLM Specifications:
        AntiPatterns:
            - tier 무시 금지 — tier 오름차순 정렬 후 첫 매핑 채택(tier1 우선).
        OutputSchema:
            - ``dict[tuple[str, str], str]``.
        Prerequisites:
            - bridge parquet (없으면 빈 dict).
        Freshness:
            - invalidateCache 시 재계산.
        Dataflow:
            - loadBridge → tier sort → dict.
        TargetMarkets:
            - KR + US 통합.
    """
    bridge = loadBridge()
    if bridge.is_empty():
        return {}
    sortedDf = bridge.sort("tier")
    out: dict[tuple[str, str], str] = {}
    for row in sortedDf.iter_rows(named=True):
        k = (row["rawId"], row["marketNs"])
        if k not in out:
            out[k] = row["disclosureKey"]
    return out


def resolveDisclosureKey(rawId: str | None, marketNs: str) -> str | None:
    """단일 rawId → disclosureKey (또는 None).

    Args:
        rawId: Layer 1 rawId (DART "NT_C_D826380" / US "us-gaap:...TextBlock").
        marketNs: 시장 namespace ("kr" / "us").

    Returns:
        disclosureKey 또는 None (unmapped → narrative fallback).

    Raises:
        없음.

    Example:
        >>> resolveDisclosureKey("BS_C", "kr")  # doctest: +SKIP
        'consolidatedBalanceSheet'
        >>> resolveDisclosureKey(None, "kr")

    SeeAlso:
        - ``resolveBatch`` — DataFrame 일괄 부착.
        - ``bridge`` — disclosureKey 어휘 SSOT.

    Requires:
        - polars (lookup dict).

    Capabilities:
        - 회사간·세계마켓간 정렬 키 단건 조회.

    Guide:
        - build 단계 disclosureKey 부착에 사용. None 은 정상(narrative).

    AIContext:
        - 순수 lookup — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - unmapped 에 임의 키 부여 금지 — None.
        OutputSchema:
            - ``str | None``.
        Prerequisites:
            - bridge parquet.
        Freshness:
            - invalidateCache 후 반영.
        Dataflow:
            - (rawId, marketNs) → _lookupDict → disclosureKey.
        TargetMarkets:
            - KR + US 통합.
    """
    if not rawId:
        return None
    return _lookupDict().get((rawId, marketNs))


def resolveBatch(df: pl.DataFrame, *, marketNs: str) -> pl.DataFrame:
    """sections/panel artifact DataFrame → disclosureKey 컬럼 부착.

    Args:
        df: panel artifact (xbrlClass 컬럼 보유).
        marketNs: 빌드 시장 ("kr" / "us").

    Returns:
        ``disclosureKey`` 컬럼이 채워진 DataFrame (원본 비면 그대로).

    Raises:
        없음.

    Example:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["NT_C_D826380", "UNKNOWN"]})
        >>> out = resolveBatch(df, marketNs="kr")  # doctest: +SKIP
        >>> out["disclosureKey"].to_list()  # doctest: +SKIP
        ['inventoryDisclosure', None]

    SeeAlso:
        - ``resolveDisclosureKey`` — 단건 조회.
        - gather ``builder`` — BUILD 단계 본 함수로 disclosureKey 채움.

    Requires:
        - polars.

    Capabilities:
        - BUILD 단계 일괄 disclosureKey 부착 → runtime resolve 회피(경량).

    Guide:
        - build write 시점 호출. reader 는 이미 채워진 컬럼 사용(없을 때만 fallback).

    AIContext:
        - map_elements lookup — row 수 적어 OK.

    LLM Specifications:
        AntiPatterns:
            - runtime 매 read resolve 금지 — build 에서 1회 부착.
        OutputSchema:
            - ``pl.DataFrame`` (+ disclosureKey Utf8).
        Prerequisites:
            - xbrlClass 컬럼 + bridge parquet.
        Freshness:
            - bridge 변경 시 재빌드 또는 invalidateCache.
        Dataflow:
            - xbrlClass → _lookupDict → disclosureKey 컬럼.
        TargetMarkets:
            - KR + US 통합.
    """
    if df.is_empty() or "xbrlClass" not in df.columns:
        return df
    lookup = _lookupDict()
    keys = df["xbrlClass"].map_elements(
        lambda x: lookup.get((x, marketNs)) if x else None,
        return_dtype=pl.Utf8,
    )
    return df.with_columns(keys.alias("disclosureKey"))


def invalidateCache() -> None:
    """bridge parquet 변경 후 lookup·bridge 캐시 초기화.

    Args:
        없음.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> invalidateCache()

    SeeAlso:
        - ``bridge.loadBridge`` — 무효화 대상 캐시.
        - ``_lookupDict`` — 무효화 대상 캐시.

    Requires:
        - 없음.

    Capabilities:
        - learn(tier2/3) 또는 seed 갱신 후 동일 프로세스 내 즉시 반영.

    Guide:
        - bridge parquet write 직후 호출.

    AIContext:
        - 캐시 clear 부작용만.

    LLM Specifications:
        AntiPatterns:
            - bridge 갱신 후 미호출 시 stale lookup.
        OutputSchema:
            - ``None``.
        Prerequisites:
            - 없음.
        Freshness:
            - 호출 즉시 다음 resolve 가 재로드.
        Dataflow:
            - cache_clear (_lookupDict + loadBridge).
        TargetMarkets:
            - KR + US 공통.
    """
    _lookupDict.cache_clear()
    loadBridge.cache_clear()
