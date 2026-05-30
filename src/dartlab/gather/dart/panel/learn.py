"""panel bridge-learning (L1 gather) — ref 제목 truth → seed disclosureKey 전파.

회사간·세계마켓간 정규화의 데이터 토대. tier1 seed(~50 KR disclosure)를 **동일
rawTitleCanonical 그룹의 옛/신 ACLASS 전체에 전파**(tier2) → era drift 흡수 (같은
disclosure 가 2020 BS / 2024 BS_C 로 흔들려도 같은 disclosureKey). 손수 regex 0 —
정부 표준 ACLASS+TITLE truth 기반 (R5).

전파 규칙 (정공 — 추측 안 함):
    - 제목 그룹에 seed rawId 1+ 있고 그 disclosureKey 가 **유일**하면 그룹 전체 전파(tier2).
    - seed disclosureKey 가 **충돌**(2+)하면 그 그룹 skip (모호 → 추측 금지).
    - 제목 빈 정형폼(COVER/DIVIDEND/INC_STAT 등)은 전파 대상 X — 직접 seed (제목 truth 없음).

LLM Specifications:
    AntiPatterns:
        - 충돌 그룹 임의 다수결 전파 금지 — skip (모호 추측 = mapper 회귀).
        - 빈 제목 그룹 전파 금지 — 한 거대 그룹에 무관 ACLASS 혼재.
        - 손수 per-title regex 추가 금지 — ref truth 그룹핑만(R5).
    OutputSchema:
        - ``learnBridge(refDf, ...) -> dict`` (tier1/tier2New/conflicts/total 통계).
        - ``bridgeCoverage(refDf, ...) -> dict`` (occurrence/entry/topN 커버리지).
    Prerequisites:
        - polars. panelXbrlRef ref DataFrame. tier1 seed (seedBridgeTier1).
    Freshness:
        - ref(refScan) 갱신 시 재실행 → bridge 재산출(idempotent).
    Dataflow:
        - ref → 제목 그룹 → seed 유일성 검사 → tier2 전파 → tier1+tier2 writeBridge.
    TargetMarkets:
        - KR (DART). US tier1 seed 는 유지(전파는 kr ref 대상).
"""

from __future__ import annotations

import datetime
import logging

import polars as pl

from dartlab.core.panel import (
    BRIDGE_SCHEMA,
    loadBridge,
    resolveDisclosureKey,
    seedBridgeTier1,
    writeBridge,
)

_log = logging.getLogger(__name__)


def learnBridge(
    refDf: pl.DataFrame,
    *,
    minCorpCount: int = 3,
    confidence: float = 0.85,
    write: bool = True,
) -> dict:
    """ref 제목 truth 그룹핑 → tier1 seed disclosureKey 를 era-variant 에 전파(tier2).

    Args:
        refDf: panelXbrlRef ref DataFrame (rawId/rawTitleCanonical/corpCount/marketNs).
        minCorpCount: 전파 대상 rawId 최소 corpCount (noise 차단, 기본 3).
        confidence: tier2 entry confidence (기본 0.85).
        write: True 면 tier1+tier2 결합본을 panelBridge.parquet 로 write.

    Returns:
        통계 dict — ``{tier1, tier2New, conflicts, titledGroups, total}``.

    Raises:
        없음 — ref 빈/컬럼 부재 시 tier1 만 유지.

    Example:
        >>> learnBridge(ref, minCorpCount=3)  # doctest: +SKIP
        {'tier1': 59, 'tier2New': 412, 'conflicts': 7, 'titledGroups': 1820, 'total': 471}

    SeeAlso:
        - ``bridgeCoverage`` — 학습 후 커버리지 측정.
        - ``core.panel.seedBridgeTier1`` — tier1 seed.
        - ``core.panel.writeBridge`` — 결합본 write.

    Requires:
        - polars. core.panel (seed/write).

    Capabilities:
        - era drift 흡수 — seed disclosure 의 옛/신 ACLASS 변형을 동일 disclosureKey 로.

    Guide:
        - refScan 산출 후 운영자/CI 호출. idempotent (재실행 시 ref 로 tier2 재계산).

    AIContext:
        - 충돌 그룹 skip = 추측 안 함 (정공). 전파는 제목 유일 seed 그룹만.

    LLM Specifications:
        AntiPatterns:
            - tier1 rawId 에 tier2 덮어쓰기 금지 — seed 우선.
            - 충돌(2+ seed disclosureKey) 그룹 전파 금지 — skip.
        OutputSchema:
            - ``dict`` (tier1/tier2New/conflicts/titledGroups/total).
        Prerequisites:
            - ref DataFrame + tier1 seed.
        Freshness:
            - ref 갱신 시 재실행.
        Dataflow:
            - tier1 seed → ref 제목 그룹 → 유일 seed dk 전파 → tier1+tier2 write.
        TargetMarkets:
            - KR (DART) 전파. US seed 유지.
    """
    tier1Df = seedBridgeTier1().filter(pl.col("tier") == 1)
    seedKr = {row["rawId"]: row["disclosureKey"] for row in tier1Df.iter_rows(named=True) if row["marketNs"] == "kr"}

    stats = {"tier1": tier1Df.height, "tier2New": 0, "conflicts": 0, "titledGroups": 0, "total": tier1Df.height}
    if refDf is None or refDf.is_empty() or "rawTitleCanonical" not in refDf.columns:
        if write:
            writeBridge(tier1Df)
        return stats

    titled = refDf.filter(
        (pl.col("marketNs") == "kr")
        & pl.col("rawTitleCanonical").is_not_null()
        & (pl.col("rawTitleCanonical").str.len_chars() > 0)
        & (pl.col("corpCount") >= minCorpCount)
    )
    groups = titled.group_by("rawTitleCanonical").agg(pl.col("rawId").unique().alias("rawIds"))
    stats["titledGroups"] = groups.height

    today = datetime.date.today()
    tier2Rows: list[dict] = []
    tier2Seen: set[str] = set()
    conflicts = 0
    for grp in groups.iter_rows(named=True):
        title = grp["rawTitleCanonical"]
        rawIds = grp["rawIds"]
        seededKeys = {seedKr[r] for r in rawIds if r in seedKr}
        if len(seededKeys) != 1:
            if len(seededKeys) > 1:
                conflicts += 1
            continue
        dk = next(iter(seededKeys))
        for r in rawIds:
            if r in seedKr or r in tier2Seen:
                continue
            tier2Rows.append(
                {
                    "disclosureKey": dk,
                    "marketNs": "kr",
                    "rawId": r,
                    "tier": 2,
                    "confidence": confidence,
                    "curatorNote": f"learned via title '{title}'",
                    "addedAt": today,
                }
            )
            tier2Seen.add(r)

    stats["tier2New"] = len(tier2Rows)
    stats["conflicts"] = conflicts

    if tier2Rows:
        tier2Df = pl.DataFrame(tier2Rows, schema=BRIDGE_SCHEMA)
        combined = pl.concat([tier1Df, tier2Df], how="vertical")
    else:
        combined = tier1Df
    stats["total"] = combined.height

    if write:
        writeBridge(combined)
    return stats


def bridgeCoverage(refDf: pl.DataFrame, *, marketNs: str = "kr", topN: int = 50) -> dict:
    """현 bridge 의 ref 커버리지 측정 — occurrence/entry/topN 가중.

    Args:
        refDf: panelXbrlRef ref DataFrame.
        marketNs: 측정 시장 (기본 "kr").
        topN: corpCount 상위 N rawId 커버리지 측정 개수 (기본 50).

    Returns:
        커버리지 dict — ``{occurrenceTotal, occurrenceTitled, entry, topN}`` (각 0~1).

    Raises:
        없음.

    Example:
        >>> bridgeCoverage(ref)  # doctest: +SKIP
        {'occurrenceTotal': 0.71, 'occurrenceTitled': 0.86, 'entry': 0.34, 'topN': 0.82}

    SeeAlso:
        - ``learnBridge`` — 커버리지 향상 (era 전파).
        - ``core.panel.resolveDisclosureKey`` — rawId → disclosureKey lookup.

    Requires:
        - polars. core.panel.

    Capabilities:
        - G3 게이트 측정 — 회사간 정규화가 corpus 의 어느 비중을 포착하는지 정직 보고.

    Guide:
        - learnBridge 후 호출. occurrenceTitled = 제목 disclosure 커버(전파 효과 핵심).

    AIContext:
        - 측정 전용 — 부작용 0. 80% 강제 X, 실측 보고.

    LLM Specifications:
        AntiPatterns:
            - 커버리지를 80% 로 강제 금지 — 실측. 부족 시 seed 확장(운영자 수동).
        OutputSchema:
            - ``dict[str, float]`` (occurrenceTotal/occurrenceTitled/entry/topN).
        Prerequisites:
            - ref DataFrame + bridge parquet.
        Freshness:
            - bridge/ref 갱신 시 재측정.
        Dataflow:
            - ref rawId → resolveDisclosureKey → mapped mask → occurrence/entry/topN 가중.
        TargetMarkets:
            - KR (DART).
    """
    if refDf is None or refDf.is_empty():
        return {"occurrenceTotal": 0.0, "occurrenceTitled": 0.0, "entry": 0.0, "topN": 0.0}
    df = refDf.filter(pl.col("marketNs") == marketNs) if "marketNs" in refDf.columns else refDf
    mapped = df["rawId"].map_elements(
        lambda r: resolveDisclosureKey(r, marketNs) is not None,
        return_dtype=pl.Boolean,
    )
    df = df.with_columns(mapped.alias("_mapped"))
    occTotal = df["occurrenceCount"].sum() or 1
    occMapped = df.filter(pl.col("_mapped"))["occurrenceCount"].sum()
    titled = df.filter(pl.col("rawTitleCanonical").is_not_null() & (pl.col("rawTitleCanonical").str.len_chars() > 0))
    occTitledTotal = titled["occurrenceCount"].sum() or 1
    occTitledMapped = titled.filter(pl.col("_mapped"))["occurrenceCount"].sum()
    top = df.sort("corpCount", descending=True).head(topN)
    topMapped = top.filter(pl.col("_mapped")).height
    return {
        "occurrenceTotal": round(occMapped / occTotal, 4),
        "occurrenceTitled": round(occTitledMapped / occTitledTotal, 4),
        "entry": round(df.filter(pl.col("_mapped")).height / max(df.height, 1), 4),
        "topN": round(topMapped / max(min(topN, df.height), 1), 4),
    }


def _main() -> None:
    """CLI entry — ``python -X utf8 -m dartlab.gather.dart.panel.learn``.

    Args:
        없음 (argparse: --ref / --min-corp / --no-write).

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> _main()  # doctest: +SKIP

    SeeAlso:
        - ``learnBridge`` / ``bridgeCoverage``.

    Requires:
        - polars. ref parquet 또는 baseline scan.

    Capabilities:
        - ref → bridge 학습 + 커버리지 보고 (운영자/CI).

    Guide:
        - refScan 산출 후 실행. --ref 없으면 baseline scan.

    AIContext:
        - CLI wrapper.

    LLM Specifications:
        AntiPatterns:
            - 없음.
        OutputSchema:
            - stdout 통계.
        Prerequisites:
            - ref parquet 또는 baseline zip.
        Freshness:
            - ref 갱신 시.
        Dataflow:
            - ref load → learnBridge → bridgeCoverage → stdout.
        TargetMarkets:
            - KR (DART).
    """
    import argparse
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="panel bridge-learning")
    ap.add_argument("--ref", type=str, default="data/dart/panelXbrlRef.parquet", help="ref parquet")
    ap.add_argument("--min-corp", type=int, default=3, help="전파 최소 corpCount")
    ap.add_argument("--no-write", action="store_true", help="학습만 (write 생략)")
    args = ap.parse_args()

    refPath = Path(args.ref)
    if refPath.exists():
        ref = pl.read_parquet(str(refPath))
        _log.info("ref load: %s (%d entry)", refPath, ref.height)
    else:
        from .build.refScan import scanRefBaseline

        _log.info("ref parquet 없음 — baseline scan")
        ref = scanRefBaseline(minCorpCount=1)

    stats = learnBridge(ref, minCorpCount=args.min_corp, write=not args.no_write)
    _log.info("learnBridge: %s", stats)
    cov = bridgeCoverage(ref)
    _log.info("coverage: %s", cov)


if __name__ == "__main__":
    _main()
