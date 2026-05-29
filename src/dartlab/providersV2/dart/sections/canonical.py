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
    return df.with_columns(keys.alias("disclosureKey"))


def scopeExpr(col: str = "xbrlClass") -> pl.Expr:
    """xbrlClass → scope ('consolidated' / 'standalone').

    DART ACLASS 명명 규약: 별도(개별) 재무·주석은 ``_S`` 표식 (BS_S / IS_S2 /
    NT_S_D######), 연결은 ``_C`` 또는 옛 무접미사 (BS / IS2 / CF). ``_S`` 가
    없으면 연결로 본다 (옛 무접미사 = 연결).

    Args:
        col: xbrlClass 컬럼명.

    Returns:
        ``scope`` 별칭 Utf8 Expr ("consolidated" / "standalone").

    Examples:
        >>> import polars as pl
        >>> df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
        >>> df.select(scopeExpr())["scope"].to_list()
        ['consolidated', 'standalone', 'consolidated', 'standalone', 'consolidated']

    LLM Specifications:
        AntiPatterns:
            - ``_S`` 부분일치를 regex 로 처리 금지 — literal 매칭 (특수문자 0).
            - narrative(xbrlClass null) 에 None scope 부여 금지 — consolidated 기본 (pivot index 안정).
        OutputSchema:
            - ``pl.Expr`` (alias "scope", Utf8).
        Prerequisites:
            - polars. xbrlClass 컬럼.
        TargetMarkets:
            - KR (DART ACLASS _C/_S 규약). EDGAR 는 별도 scope 규칙.
    """
    c = pl.col(col)
    return (
        pl.when(c.is_null())
        .then(pl.lit("consolidated"))
        .when(c.str.contains("_S", literal=True))
        .then(pl.lit("standalone"))
        .otherwise(pl.lit("consolidated"))
        .alias("scope")
    )


def anchorLatest(df: pl.DataFrame) -> pl.DataFrame:
    """과거 기간을 최신기준으로 수평화 — disclosureKey 단일 앵커 정렬 (요구 #7).

    같은 disclosure 가 era 마다 xbrlClass(BS→BS_C)·제목(연결 재무상태표→"")이
    흔들려 pivot 이 era 별로 행을 쪼갬 → ``(disclosureKey, scope)`` 그룹의 **최신
    period 라벨**(chapter/sectionLeaf/blockLeaf)을 전 기간에 덮어써 한 행으로 정렬.
    scope 로 연결/별도 분리 보존 (NT_C vs NT_S 병합 방지). disclosureKey null
    (narrative) 행은 손대지 않음 (텍스트 정렬 유지).

    Args:
        df: sections long DataFrame (disclosureKey/xbrlClass/period/chapter/
            sectionLeaf/blockLeaf 포함).

    Returns:
        ``scope`` 컬럼 추가 + keyed 행의 chapter/sectionLeaf/blockLeaf 가 최신기준
        으로 통일된 DataFrame.

    LLM Specifications:
        AntiPatterns:
            - disclosureKey 단독 group 금지 — (disclosureKey, scope) 페어 (연결/별도 병합 방지).
            - xbrlClass 를 pivot index 에 유지 금지 — era drift 로 행 쪼개짐 (scope 로 대체).
            - 최신 = period 최대 문자열 (YYYYQn 정렬). 결산월 무관 12월결산화된 키라 안전.
        OutputSchema:
            - 입력과 동일 컬럼 + ``scope``, keyed 행 라벨 최신 통일.
        Prerequisites:
            - polars. disclosureKey/period/scope 원천(xbrlClass).
        Dataflow:
            - scope 부착 → keyed 행 (disclosureKey,scope)별 최신 period 라벨 추출 →
              join 후 keyed 행 라벨 덮어쓰기.
        TargetMarkets:
            - KR + US 공통 (disclosureKey 계약 동일).
    """
    if df.is_empty() or "disclosureKey" not in df.columns or "period" not in df.columns:
        return df
    df = df.with_columns(scopeExpr())
    keyed = df.filter(pl.col("disclosureKey").is_not_null())
    if keyed.is_empty():
        return df
    latest = (
        keyed.sort("period")
        .group_by(["disclosureKey", "scope"], maintain_order=True)
        .agg(
            pl.col("chapter").last().alias("_chapterL"),
            pl.col("sectionLeaf").last().alias("_sectionLeafL"),
            pl.col("blockLeaf").last().alias("_blockLeafL"),
        )
    )
    df = df.join(latest, on=["disclosureKey", "scope"], how="left")
    return df.with_columns(
        pl.when(pl.col("_chapterL").is_not_null())
        .then(pl.col("_chapterL"))
        .otherwise(pl.col("chapter"))
        .alias("chapter"),
        pl.when(pl.col("_sectionLeafL").is_not_null())
        .then(pl.col("_sectionLeafL"))
        .otherwise(pl.col("sectionLeaf"))
        .alias("sectionLeaf"),
        pl.when(pl.col("_blockLeafL").is_not_null())
        .then(pl.col("_blockLeafL"))
        .otherwise(pl.col("blockLeaf"))
        .alias("blockLeaf"),
    ).drop(["_chapterL", "_sectionLeafL", "_blockLeafL"])


def invalidateCache() -> None:
    """bridge parquet 변경 후 호출 — lru_cache 초기화."""
    _lookupDict.cache_clear()
    loadBridge.cache_clear()
