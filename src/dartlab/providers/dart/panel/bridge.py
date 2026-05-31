"""panel disclosureKey bridge SSOT (L0) — US↔KR cross-market overlay.

EDGAR us-gaap TextBlock concept ↔ universal disclosureKey(snakeId). **KR within-market 정렬은
core.panel.canonicalKey(native ACLASS scope-strip)가 대체** — 본 bridge 는 이제 두 택소노미
(us-gaap ↔ KR ACLASS)를 화해시키는 cross-market overlay 전용(비가역 매핑이라 hand-seed 유지).
손수 KR seed + corpus 학습 농장은 2026-05 redesign 으로 폐기.

bridge = parquet 데이터 (코드 regex 0, R5). US us-gaap tier1 seed 만(운영자 큐레이션, ~10).
본 모듈은 seed 생성 + loader. (cross-market 활성은 EDGAR panel 빌드 후속.)

LLM Specifications:
    AntiPatterns:
        - KR rawId(ACLASS) 추가 금지 — KR 은 canonicalKey 가 SSOT(bridge 우회).
        - tier1 entry 손수 per-title regex 매핑 금지 — concept 직접 참조.
        - finance line item 매핑 포함 금지 — panel = disclosure 한정.
    OutputSchema:
        - ``loadBridge() -> pl.DataFrame`` 7 col (disclosureKey/marketNs/rawId/tier/
          confidence/curatorNote/addedAt).
        - ``seedBridgeTier1(*, overwrite) -> pl.DataFrame``.
    Prerequisites:
        - polars. data/bridge/panelBridge.parquet (seedBridgeTier1 으로 생성).
    Freshness:
        - US seed stable. KR 은 canonicalKey(코드 규칙).
    Dataflow:
        - bridge parquet read → canonical.resolveDisclosureKey 가 us-gaap → disclosureKey lookup.
    TargetMarkets:
        - US cross-market overlay (KR within = canonicalKey).
"""

from __future__ import annotations

import datetime
from functools import lru_cache
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

# bridge parquet 7-col schema (US overlay seed).
BRIDGE_SCHEMA: dict[str, pl.DataType] = {
    "disclosureKey": pl.Utf8,
    "marketNs": pl.Utf8,
    "rawId": pl.Utf8,
    "tier": pl.UInt8,
    "confidence": pl.Float32,
    "curatorNote": pl.Utf8,
    "addedAt": pl.Date,
}


def _bridgePath() -> Path:
    """panel bridge parquet 경로 반환.

    Args:
        없음.

    Returns:
        ``data/bridge/panelBridge.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> _bridgePath().name
        'panelBridge.parquet'

    SeeAlso:
        - ``loadBridge`` — 본 경로 read.
        - ``seedBridgeTier1`` — 본 경로 write.

    Requires:
        - dartlab.config.

    Capabilities:
        - bridge SSOT 단일 경로 (S3) — 다른 모듈은 본 함수만 경유.

    Guide:
        - 내부 helper — 직접 호출 X.

    AIContext:
        - 경로 계산만 — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 경로 하드코딩 분산 금지 — 본 함수 단일 SSOT.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - dartlab.config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - config.dataDir → data/bridge/panelBridge.parquet.
        TargetMarkets:
            - KR + US 공통.
    """
    return Path(_cfg.dataDir) / "bridge" / "panelBridge.parquet"


def _tier1Seed() -> list[dict]:
    """tier1 US us-gaap TextBlock → universal disclosureKey seed (cross-market overlay, ~10).

    EDGAR us-gaap 표준 TextBlock concept ↔ universal disclosureKey. **KR ACLASS seed 는 폐기**
    (KR within = core.panel.canonicalKey native 정렬). 두 택소노미 화해는 비가역 매핑이라 US
    overlay 만 hand-seed 유지. cross-market 활성은 EDGAR panel 빌드 후속.

    Args:
        없음.

    Returns:
        seed dict 리스트 (US us-gaap, ~10 entry, 7-col).

    Raises:
        없음.

    Example:
        >>> rows = _tier1Seed()
        >>> rows[0]["marketNs"]
        'us'

    SeeAlso:
        - ``seedBridgeTier1`` — 본 seed 를 parquet 로 write.
        - ``canonical.canonicalKey`` — KR within 정렬키(bridge 우회).

    Requires:
        - datetime.

    Capabilities:
        - US↔KR cross-market 정규화의 manual anchor — us-gaap TextBlock 어휘.

    Guide:
        - 내부 helper — seedBridgeTier1 경유.

    AIContext:
        - 정적 큐레이션 데이터 — KR rawId 추가 금지(canonicalKey SSOT).

    LLM Specifications:
        AntiPatterns:
            - KR rawId 추가 금지 — canonicalKey 가 KR SSOT.
            - finance line item 추가 금지 (panel = disclosure 한정).
        OutputSchema:
            - ``list[dict]`` (disclosureKey/marketNs/rawId/tier/confidence/curatorNote/addedAt).
        Prerequisites:
            - 없음.
        Freshness:
            - US seed stable.
        Dataflow:
            - 정적 튜플 → dict 리스트.
        TargetMarkets:
            - US (us-gaap TextBlock). KR = canonicalKey.
    """
    today = datetime.date.today()
    note = "tier1 seed — 운영자 큐레이션"
    # 형식: (disclosureKey, marketNs, rawId, confidence)
    # KR within-market 정렬은 core.panel.canonicalKey(native ACLASS scope-strip)가 대체 —
    # 손수 KR seed 농장 폐기(2026-05 redesign). bridge 는 이제 US↔KR cross-market overlay 전용
    # (두 택소노미 화해는 비가역 매핑이라 hand-seed 유지). KR rawId 는 절대 추가 금지.
    rows: list[tuple[str, str, str, float]] = [
        # ── EDGAR us-gaap TextBlock ↔ universal disclosureKey (세계마켓간 overlay) ──
        ("consolidatedBalanceSheet", "us", "us-gaap:BalanceSheetTextBlock", 1.0),
        ("consolidatedIncomeStatement", "us", "us-gaap:IncomeStatementTextBlock", 1.0),
        ("consolidatedCashFlowStatement", "us", "us-gaap:CashFlowStatementTextBlock", 1.0),
        ("inventoryDisclosure", "us", "us-gaap:InventoryDisclosureTextBlock", 1.0),
        ("propertyPlantEquipmentDisclosure", "us", "us-gaap:PropertyPlantAndEquipmentDisclosureTextBlock", 1.0),
        ("intangibleAssetsDisclosure", "us", "us-gaap:IntangibleAssetsDisclosureTextBlock", 1.0),
        ("incomeTaxDisclosure", "us", "us-gaap:IncomeTaxDisclosureTextBlock", 1.0),
        ("revenueRecognitionPolicy", "us", "us-gaap:RevenueRecognitionPolicyTextBlock", 1.0),
        ("significantAccountingPolicies", "us", "us-gaap:SignificantAccountingPoliciesTextBlock", 1.0),
        ("relatedPartyDisclosure", "us", "us-gaap:RelatedPartyTransactionsDisclosureTextBlock", 1.0),
    ]
    return [
        {
            "disclosureKey": dk,
            "marketNs": ns,
            "rawId": rid,
            "tier": 1,
            "confidence": conf,
            "curatorNote": note,
            "addedAt": today,
        }
        for (dk, ns, rid, conf) in rows
    ]


def seedBridgeTier1(*, overwrite: bool = False) -> pl.DataFrame:
    """tier1 seed parquet 생성 (panelBridge.parquet).

    Args:
        overwrite: 기존 parquet 덮어쓰기 여부. False 면 존재 시 read 만.

    Returns:
        seed DataFrame (US us-gaap, ~10 entry, 7-col).

    Raises:
        없음.

    Example:
        >>> df = seedBridgeTier1(overwrite=True)  # doctest: +SKIP
        >>> df.height >= 10  # doctest: +SKIP
        True

    SeeAlso:
        - ``loadBridge`` — 생성된 parquet read.
        - ``canonical.canonicalKey`` — KR within 정렬키(bridge 우회).

    Requires:
        - polars. dartlab.config.

    Capabilities:
        - US↔KR cross-market 정규화의 manual anchor 부트스트랩 (EDGAR panel 후속).

    Guide:
        - cross-market 활성 시 운영자 호출. KR within 은 canonicalKey(seed 불요).

    AIContext:
        - parquet write 부작용 — overwrite 인자로 보호.

    When:
        - US cross-market overlay seed 가 필요할 때 (운영자).

    How:
        - _tier1Seed → DataFrame → parquet write → loadBridge.cache_clear.

    LLM Specifications:
        AntiPatterns:
            - KR rawId seed 추가 금지 — canonicalKey 가 KR SSOT.
        OutputSchema:
            - ``pl.DataFrame`` (7-col).
        Prerequisites:
            - data/bridge/ 디렉터리(자동 생성).
        Freshness:
            - US seed 갱신 시점.
        Dataflow:
            - _tier1Seed → DataFrame → parquet write → cache invalidate.
        TargetMarkets:
            - US (cross-market overlay).
    """
    bridgePath = _bridgePath()
    bridgePath.parent.mkdir(parents=True, exist_ok=True)
    if bridgePath.exists() and not overwrite:
        return pl.read_parquet(str(bridgePath))
    df = pl.DataFrame(_tier1Seed(), schema=BRIDGE_SCHEMA)
    df.write_parquet(str(bridgePath))
    loadBridge.cache_clear()
    return df


@lru_cache(maxsize=1)
def loadBridge() -> pl.DataFrame:
    """panel bridge parquet load (lru_cache).

    Args:
        없음.

    Returns:
        bridge DataFrame (7-col). 파일 없으면 빈 DataFrame(스키마 유지).

    Raises:
        없음.

    Example:
        >>> df = loadBridge()  # doctest: +SKIP
        >>> set(df.columns) >= {"disclosureKey", "marketNs", "rawId"}  # doctest: +SKIP
        True

    SeeAlso:
        - ``canonical.resolveDisclosureKey`` — 본 DataFrame lookup.
        - ``canonical.invalidateCache`` — parquet 변경 후 cache 무효화.

    Requires:
        - polars. dartlab.config.

    Capabilities:
        - rawId → disclosureKey lookup 의 데이터 원천 (캐시 1회 read).

    Guide:
        - 직접 호출보다 resolveDisclosureKey/resolveBatch 경유 권장.

    AIContext:
        - lru_cache — parquet 변경 시 invalidateCache 필요.

    When:
        - rawId → disclosureKey lookup 의 데이터 원천이 필요할 때.

    How:
        - parquet → DataFrame (lru_cache 1회 read).

    LLM Specifications:
        AntiPatterns:
            - 매 호출 read 금지 — lru_cache 1회.
        OutputSchema:
            - ``pl.DataFrame`` (7-col, 빈 경우 스키마만).
        Prerequisites:
            - data/bridge/panelBridge.parquet (없으면 빈 결과).
        Freshness:
            - parquet 변경 시 invalidateCache 호출.
        Dataflow:
            - parquet → DataFrame (cache).
        TargetMarkets:
            - KR + US 통합.
    """
    p = _bridgePath()
    if not p.exists():
        return pl.DataFrame(schema=BRIDGE_SCHEMA)
    return pl.read_parquet(str(p))


def writeBridge(df: pl.DataFrame, *, invalidate: bool = True) -> None:
    """bridge DataFrame 을 panelBridge.parquet 로 write (US overlay SSOT 갱신).

    US cross-market overlay seed 를 SSOT 포맷·경로(core L0 소유)로 저장하는 write 경계 primitive.
    (KR within 은 canonicalKey 라 bridge write 불요 — 본 함수는 US 도구용.)

    Args:
        df: 7-col bridge DataFrame (BRIDGE_SCHEMA). US us-gaap overlay.
        invalidate: True 면 write 후 canonical/bridge lru_cache 무효화.

    Returns:
        None.

    Raises:
        없음 — 디렉터리 자동 생성.

    Example:
        >>> writeBridge(usOverlayDf)  # doctest: +SKIP

    SeeAlso:
        - ``loadBridge`` — 본 함수가 쓴 parquet read.
        - ``seedBridgeTier1`` — US seed 생성.

    Requires:
        - polars. dartlab.config.

    Capabilities:
        - US cross-market overlay bridge SSOT 단일 write 경로.

    Guide:
        - US overlay 도구가 호출 — KR 파이프라인은 미사용(canonicalKey).

    AIContext:
        - parquet write + cache invalidate 부작용. KR rawId 추가 금지(R5).

    When:
        - US cross-market overlay 를 SSOT 로 저장할 때.

    How:
        - df → BRIDGE_SCHEMA select → parquet write → (invalidate) cache_clear.

    LLM Specifications:
        AntiPatterns:
            - 컬럼 추가/이름 변경 금지 — BRIDGE_SCHEMA 7-col 동결.
            - invalidate=False 후 동일 프로세스 resolve 금지 — stale lookup.
        OutputSchema:
            - ``None`` + 부수효과 data/bridge/panelBridge.parquet.
        Prerequisites:
            - df 가 BRIDGE_SCHEMA 7-col.
        Freshness:
            - write 즉시 (invalidate 시) 다음 resolve 반영.
        Dataflow:
            - df → parquet write → (invalidate) cache_clear.
        TargetMarkets:
            - US (cross-market overlay).
    """
    bridgePath = _bridgePath()
    bridgePath.parent.mkdir(parents=True, exist_ok=True)
    df.select(list(BRIDGE_SCHEMA.keys())).write_parquet(str(bridgePath))
    if invalidate:
        from .canonical import invalidateCache

        invalidateCache()
