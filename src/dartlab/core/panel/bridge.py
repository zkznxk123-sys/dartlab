"""panel disclosureKey bridge SSOT (L0) — rawId ↔ universal disclosureKey.

Layer 3 — DART ACLASS rawId / EDGAR us-gaap TextBlock concept ↔ universal
disclosureKey(snakeId SSOT). 회사간·세계마켓간 정규화의 핵심 — 같은 의미 disclosure 가
시장·era 무관 동일 disclosureKey 로 묶인다.

bridge = parquet 데이터 (코드 regex 0, [[feedback]] R5). tier1 ~60 seed(운영자 큐레이션)
+ tier2/3 corpus-learned(gather ``learn.learnBridge`` 가 채움). 본 모듈은 seed 생성 +
loader 만 — 학습 전파는 gather 책임 (build write 층).

LLM Specifications:
    AntiPatterns:
        - tier1 entry 손수 per-title regex 매핑 금지 — rawId 직접 참조 (정부 표준 canonical).
        - finance 영역 매핑(BS/IS/CF line item) 포함 금지 — panel = narrative + footnote
          disclosure 한정. line item 은 finance 엔진.
        - disclosureKey 양식 자유 추가 금지 — snakeId 의미 단위 SSOT.
    OutputSchema:
        - ``loadBridge() -> pl.DataFrame`` 7 col (disclosureKey/marketNs/rawId/tier/
          confidence/curatorNote/addedAt).
        - ``seedBridgeTier1(*, overwrite) -> pl.DataFrame``.
    Prerequisites:
        - polars. data/bridge/panelBridge.parquet (seedBridgeTier1 으로 생성).
    Freshness:
        - tier2/3 확장(learn) 시 별도 cycle. tier1 stable.
    Dataflow:
        - bridge parquet read → canonical.resolveDisclosureKey 가 rawId → disclosureKey lookup.
    TargetMarkets:
        - KR + US 통합 (동일 disclosureKey 어휘).
"""

from __future__ import annotations

import datetime
from functools import lru_cache
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

# bridge parquet 7-col schema (seed·learn 공통).
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
    """tier1 ~60 entry seed — DART ACLASS + EDGAR us-gaap TextBlock 매핑.

    DART side = 5 baseline scan 에서 확인된 NT_C_D######/NT_S_D######(재고/유형/무형/
    법인세/금융손익 등) + 재무제표 ACLASS(BS/IS/CF/EF, 신·옛 양식). EDGAR side = us-gaap
    표준 TextBlock concept. corpus-learned tier2/3 은 gather ``learn`` 이 추가.

    Args:
        없음.

    Returns:
        seed dict 리스트 (~60 entry, 7-col).

    Raises:
        없음.

    Example:
        >>> rows = _tier1Seed()
        >>> rows[0]["disclosureKey"]
        'consolidatedBalanceSheet'

    SeeAlso:
        - ``seedBridgeTier1`` — 본 seed 를 parquet 로 write.
        - gather ``learn.learnBridge`` — tier2/3 corpus 전파.

    Requires:
        - datetime.

    Capabilities:
        - 회사간·세계마켓간 정규화의 manual anchor — 가장 빈출 disclosure 의 cross-market 어휘.

    Guide:
        - 내부 helper — seedBridgeTier1 경유.

    AIContext:
        - 정적 큐레이션 데이터 — AI 자유 추가 금지(R5).

    LLM Specifications:
        AntiPatterns:
            - finance line item 추가 금지 (panel = disclosure 한정).
            - 손수 regex 기반 entry 금지 — rawId 직접.
        OutputSchema:
            - ``list[dict]`` (disclosureKey/marketNs/rawId/tier/confidence/curatorNote/addedAt).
        Prerequisites:
            - 없음.
        Freshness:
            - tier1 stable. 확장은 learn(tier2/3).
        Dataflow:
            - 정적 튜플 → dict 리스트.
        TargetMarkets:
            - KR (ACLASS) + US (us-gaap TextBlock).
    """
    today = datetime.date.today()
    note = "tier1 seed — 운영자 큐레이션"
    # 형식: (disclosureKey, marketNs, rawId, confidence)
    rows: list[tuple[str, str, str, float]] = [
        # ── 재무제표 표 (신 양식 ACLASS) ──
        ("consolidatedBalanceSheet", "kr", "BS_C", 1.0),
        ("standaloneBalanceSheet", "kr", "BS_S", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS_C1", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS_C2", 1.0),
        ("consolidatedComprehensiveIncome", "kr", "IS_C3", 1.0),
        ("standaloneIncomeStatement", "kr", "IS_S1", 1.0),
        ("standaloneIncomeStatement", "kr", "IS_S2", 1.0),
        ("standaloneComprehensiveIncome", "kr", "IS_S3", 1.0),
        ("consolidatedCashFlowStatement", "kr", "CF_C", 1.0),
        ("standaloneCashFlowStatement", "kr", "CF_S", 1.0),
        ("consolidatedEquityChanges", "kr", "EF_C", 1.0),
        ("standaloneEquityChanges", "kr", "EF_S", 1.0),
        # ── 재무제표 표 (옛 양식 suffix 없는 ACLASS, ~2020) ──
        ("consolidatedBalanceSheet", "kr", "BS", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS2", 1.0),
        ("consolidatedComprehensiveIncome", "kr", "IS3", 1.0),
        ("consolidatedCashFlowStatement", "kr", "CF", 1.0),
        ("consolidatedEquityChanges", "kr", "EF", 1.0),
        # ── 주석 핵심 disclosure (NT_C_D###### + NT_S_D###### 페어) ──
        ("inventoryDisclosure", "kr", "NT_C_D826380", 1.0),
        ("inventoryDisclosure", "kr", "NT_S_D826385", 1.0),
        ("propertyPlantEquipmentDisclosure", "kr", "NT_C_D822100", 1.0),
        ("propertyPlantEquipmentDisclosure", "kr", "NT_S_D822105", 1.0),
        ("intangibleAssetsDisclosure", "kr", "NT_C_D823180", 1.0),
        ("intangibleAssetsDisclosure", "kr", "NT_S_D823185", 1.0),
        ("incomeTaxDisclosure", "kr", "NT_C_D835110", 1.0),
        ("incomeTaxDisclosure", "kr", "NT_S_D835115", 1.0),
        ("financialIncomeAndCosts", "kr", "NT_C_D834330", 1.0),
        ("financialIncomeAndCosts", "kr", "NT_S_D834335", 1.0),
        ("generalInformation", "kr", "NT_C_D810000", 1.0),
        ("generalInformation", "kr", "NT_S_D800600", 1.0),
        # ── 주석 확장 (top corpCount entry) ──
        ("cashAndEquivalentsDisclosure", "kr", "NT_C_D822410", 1.0),
        ("cashAndEquivalentsDisclosure", "kr", "NT_S_D822415", 1.0),
        ("provisionsDisclosure", "kr", "NT_C_D827570", 1.0),
        ("provisionsDisclosure", "kr", "NT_S_D827575", 1.0),
        ("earningsPerShareDisclosure", "kr", "NT_C_D838000", 1.0),
        ("earningsPerShareDisclosure", "kr", "NT_S_D838005", 1.0),
        ("sellingGeneralAdminExpenses", "kr", "NT_C_D834310", 1.0),
        ("sellingGeneralAdminExpenses", "kr", "NT_S_D834315", 1.0),
        ("relatedPartyDisclosure", "kr", "NT_C_D818000", 1.0),
        ("relatedPartyDisclosure", "kr", "NT_S_D818005", 1.0),
        ("accountingEstimatesDisclosure", "kr", "NT_C_D810010", 1.0),
        ("accountingEstimatesDisclosure", "kr", "NT_S_D810015", 1.0),
        ("tradeReceivablesDisclosure", "kr", "NT_C_D822420", 1.0),
        ("tradeReceivablesDisclosure", "kr", "NT_S_D822425", 1.0),
        ("financialInstrumentsByCategory", "kr", "NT_C_D822430", 1.0),
        ("financialInstrumentsByCategory", "kr", "NT_S_D822435", 1.0),
        ("otherLiabilitiesDisclosure", "kr", "NT_C_D822310", 1.0),
        ("otherLiabilitiesDisclosure", "kr", "NT_S_D822315", 1.0),
        ("capitalDisclosure", "kr", "NT_C_D861200", 1.0),
        ("capitalDisclosure", "kr", "NT_S_D861205", 1.0),
        # ── EDGAR us-gaap TextBlock 매핑 (세계마켓간 seed) ──
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
        seed DataFrame (~60 entry, 7-col).

    Raises:
        없음.

    Example:
        >>> df = seedBridgeTier1(overwrite=True)  # doctest: +SKIP
        >>> df.height >= 60  # doctest: +SKIP
        True

    SeeAlso:
        - ``loadBridge`` — 생성된 parquet read.
        - gather ``learn.learnBridge`` — tier2/3 corpus 전파.

    Requires:
        - polars. dartlab.config.

    Capabilities:
        - 회사간·세계마켓간 정규화의 manual anchor 데이터 부트스트랩.

    Guide:
        - 최초 1회 또는 seed 갱신 시 운영자 호출. learn 이 그 위에 tier2/3 누적.

    AIContext:
        - parquet write 부작용 — overwrite 인자로 보호.

    When:
        - 최초 또는 tier1 seed 갱신 시 (운영자).

    How:
        - _tier1Seed → DataFrame → parquet write → loadBridge.cache_clear.

    LLM Specifications:
        AntiPatterns:
            - 매 build 마다 overwrite=True 금지 — learn(tier2/3) 산출 소실.
        OutputSchema:
            - ``pl.DataFrame`` (7-col).
        Prerequisites:
            - data/bridge/ 디렉터리(자동 생성).
        Freshness:
            - tier1 갱신 시점.
        Dataflow:
            - _tier1Seed → DataFrame → parquet write → cache invalidate.
        TargetMarkets:
            - KR + US 통합.
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
    """bridge DataFrame 을 panelBridge.parquet 로 write (SSOT 갱신).

    gather ``learn.learnBridge`` 가 tier1 seed + tier2 corpus-learned 결합본을 본 함수로
    저장한다. write 책임은 gather(L1) 이지만 SSOT 포맷·경로는 core(L0) 소유 — 본 함수가
    경계.

    Args:
        df: 7-col bridge DataFrame (BRIDGE_SCHEMA). tier1 + tier2 결합본.
        invalidate: True 면 write 후 canonical/bridge lru_cache 무효화.

    Returns:
        None.

    Raises:
        없음 — 디렉터리 자동 생성.

    Example:
        >>> writeBridge(combinedDf)  # doctest: +SKIP

    SeeAlso:
        - ``loadBridge`` — 본 함수가 쓴 parquet read.
        - ``seedBridgeTier1`` — tier1 seed 생성.
        - gather ``learn.learnBridge`` — tier2 corpus 전파 후 본 함수로 저장.

    Requires:
        - polars. dartlab.config.

    Capabilities:
        - tier1+tier2 결합 bridge SSOT 단일 write 경로 — 회사간·세계마켓간 정규화 어휘 확정.

    Guide:
        - learnBridge 가 호출 — 직접 호출 X.

    AIContext:
        - parquet write + cache invalidate 부작용. 양식 자유 추가 금지(R5).

    When:
        - learnBridge 가 tier1+tier2 결합본을 SSOT 로 저장할 때.

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
            - KR + US 통합.
    """
    bridgePath = _bridgePath()
    bridgePath.parent.mkdir(parents=True, exist_ok=True)
    df.select(list(BRIDGE_SCHEMA.keys())).write_parquet(str(bridgePath))
    if invalidate:
        from .canonical import invalidateCache

        invalidateCache()
