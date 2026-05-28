"""bridge SSOT loader + tier1 seed (수동 큐레이션, sections disclosure 한정).

Layer 3 — DART ACLASS rawId / EDGAR us-gaap TextBlock concept ↔ universal
disclosureKey (snakeId SSOT).

tier1 ~30 seed (마스터 플랜 v5 §2.1):
    BS/IS/CF/EF 4 재무제표 + 핵심 주석 disclosure 5~10 종 + 사업 일반 정보.
    EdgarTools 150 매핑 + dartlab xbrlConcepts 100 + 운영자 30 seed.

LLM Specifications:
    AntiPatterns:
        - tier1 entry 손수 regex 매핑 금지 — Layer 1 ref table 의 rawId 직접
          참조 (정부 표준 cross-company canonical).
        - finance 영역 매핑 (BS/IS/CF line item) 절대 포함 금지 — sections =
          narrative + footnote disclosure 한정. BS/IS/CF 는 finance 엔진.
        - disclosureKey 양식 자유롭게 추가 금지 — SSOT (snakeId, 의미 단위).
    OutputSchema:
        - ``loadBridge() -> pl.DataFrame`` 7 col (disclosureKey/marketNs/rawId/
          tier/confidence/curatorNote/addedAt).
        - ``seedBridgeTier1() -> pl.DataFrame`` ~30 entry hardcoded.
    Prerequisites:
        - data/bridge/sectionsBridge.parquet (seedBridgeTier1 으로 생성).
    Freshness:
        - tier2/3 확장 시 별도 cycle. tier1 은 stable.
    Dataflow:
        - bridge parquet read → resolveDisclosureKey 가 rawId → disclosureKey
          lookup.
    TargetMarkets:
        - KR + US 통합.

마스터 플랜: v5 §1 + §3.2.
"""

from __future__ import annotations

import datetime
from functools import lru_cache
from pathlib import Path

import polars as pl

import dartlab.config as _cfg


def _bridgePath() -> Path:
    return Path(_cfg.dataDir) / "bridge" / "sectionsBridge.parquet"


def _tier1Seed() -> list[dict]:
    """tier1 ~30 entry seed — DART ACLASS rawId + EDGAR us-gaap TextBlock 매핑.

    DART side 는 P-S1 5 baseline scan 에서 확인된 NT_C_D###### / NT_S_D######
    (재고자산 / 유형자산 / 무형자산 / 법인세비용 / 금융수익 등) 의 rawId.
    EDGAR side 는 us-gaap 표준 TextBlock concept name.
    """
    today = datetime.date.today()
    note = "tier1 seed (마스터 플랜 v5 §2.1) — 운영자 큐레이션"
    # 형식: (disclosureKey, marketNs, rawId, confidence)
    rows: list[tuple[str, str, str, float]] = [
        # ── 재무제표 표 (신 양식 ACLASS) ──
        ("consolidatedBalanceSheet", "kr", "BS_C", 1.0),
        ("standaloneBalanceSheet", "kr", "BS_S", 1.0),
        # IS_C1 = 손익+포괄손익 통합 (035720/207940/000660 양식)
        # IS_C2 = 손익 / IS_C3 = 포괄손익 (005930/005380 분리 양식)
        ("consolidatedIncomeStatement", "kr", "IS_C1", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS_C2", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS_C3", 1.0),
        ("standaloneIncomeStatement", "kr", "IS_S1", 1.0),
        ("standaloneIncomeStatement", "kr", "IS_S2", 1.0),
        ("standaloneIncomeStatement", "kr", "IS_S3", 1.0),
        ("consolidatedCashFlowStatement", "kr", "CF_C", 1.0),
        ("standaloneCashFlowStatement", "kr", "CF_S", 1.0),
        ("consolidatedEquityChanges", "kr", "EF_C", 1.0),
        ("standaloneEquityChanges", "kr", "EF_S", 1.0),
        # ── 재무제표 표 (옛 양식 suffix 없는 ACLASS, ~2020) ──
        # corpCount 1,988 (전종목 68%) — 누락 시 옛 분기 연결재무 매핑 0
        ("consolidatedBalanceSheet", "kr", "BS", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS2", 1.0),
        ("consolidatedIncomeStatement", "kr", "IS3", 1.0),
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
        ("generalInformation", "kr", "NT_S_D800600", 1.0),  # [추측]
        # ── 주석 확장 (top corpCount entry from P-S3 ref) ──
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
        # ── EDGAR us-gaap TextBlock 매핑 (tier1 seed) ──
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
    """tier1 seed parquet 생성 — 마스터 플랜 v5 §2.1.

    Args:
        overwrite: 기존 parquet 덮어쓰기 여부.

    Returns:
        seed DataFrame (~30 entry).
    """
    bridgePath = _bridgePath()
    bridgePath.parent.mkdir(parents=True, exist_ok=True)
    if bridgePath.exists() and not overwrite:
        return pl.read_parquet(str(bridgePath))
    df = pl.DataFrame(
        _tier1Seed(),
        schema={
            "disclosureKey": pl.Utf8,
            "marketNs": pl.Utf8,
            "rawId": pl.Utf8,
            "tier": pl.UInt8,
            "confidence": pl.Float32,
            "curatorNote": pl.Utf8,
            "addedAt": pl.Date,
        },
    )
    df.write_parquet(str(bridgePath))
    loadBridge.cache_clear()  # cache invalidate
    return df


@lru_cache(maxsize=1)
def loadBridge() -> pl.DataFrame:
    """bridge parquet load (lru_cache).

    Returns:
        bridge DataFrame. 없으면 빈 DataFrame.
    """
    p = _bridgePath()
    if not p.exists():
        return pl.DataFrame(
            schema={
                "disclosureKey": pl.Utf8,
                "marketNs": pl.Utf8,
                "rawId": pl.Utf8,
                "tier": pl.UInt8,
                "confidence": pl.Float32,
                "curatorNote": pl.Utf8,
                "addedAt": pl.Date,
            }
        )
    return pl.read_parquet(str(p))
