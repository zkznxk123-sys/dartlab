"""DART Company sections / profile / chapter 메타 helpers.

Company.sections / _profileTable / _chapterMap / _chapterForTopic / _topicLabel 본체를
facade 에서 분리. Company facade 는 thin delegate.

sections 는 docs + finance + report 3 source 통합 지도. show/trace/diff 의 근간.

Module-level constants:
    _STATIC_CHAPTER_MAP — topic → chapter (II~XII) 정적 매핑

Module-level functions:
    buildSections      — sections property 본체 (3 source 병합)
    profileTable       — section profile artifact (캐시)
    chapterMap         — static + profile-derived 매핑 (캐시)
    chapterForTopic    — topic → chapter (notes XI / unknown XII fallback)
    topicLabel         — topic → 한글 라벨 (CIS/SCE 우선 + registry/_TOPIC_LABELS)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.providers.dart._utils import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


_STATIC_CHAPTER_MAP: dict[str, str] = {
    "BS": "III",
    "IS": "III",
    "CIS": "III",
    "CF": "III",
    "SCE": "III",
    "ratios": "III",
    "audit": "V",
    "auditContract": "V",
    "nonAuditContract": "V",
    "majorHolder": "VII",
    "majorHolderChange": "VII",
    "minorityHolder": "VII",
    "treasuryStock": "VII",
    "stockTotal": "VII",
    "capitalChange": "VII",
    "shareholderMeeting": "VII",
    "employee": "VIII",
    "executive": "VIII",
    "topPay": "VIII",
    "unregisteredExecutivePay": "VIII",
    "executivePayAllTotal": "VIII",
    "executivePayIndividual": "VIII",
    "investedCompany": "IX",
    "relatedPartyTx": "IX",
    "publicOfferingUsage": "X",
    "privateOfferingUsage": "X",
    "corporateBond": "X",
    "shortTermBond": "X",
    "auditOpinion": "V",
    "outsideDirector": "VI",
    "executivePayByType": "VIII",
    "executivePayTotal": "VIII",
}


def profileTable(company: Company) -> pl.DataFrame | None:
    cacheKey = "_sectionProfileTable"
    if cacheKey in company._cache:
        return company._cache[cacheKey]
    from dartlab.providers.dart.docs.sections.artifacts import loadSectionProfileTable

    table = loadSectionProfileTable()
    company._cache[cacheKey] = table
    return table


def chapterMap(company: Company) -> dict[str, str]:
    cacheKey = "_chapterMap"
    if cacheKey in company._cache:
        return company._cache[cacheKey]

    mapping: dict[str, str] = dict(_STATIC_CHAPTER_MAP)

    table = profileTable(company)
    if table is not None and not table.is_empty():
        canonicalCol = "canonicalTopic" if "canonicalTopic" in table.columns else "topic"
        grouped = (
            table.filter(pl.col(canonicalCol).is_not_null(), pl.col("chapter").is_not_null())
            .group_by([canonicalCol, "chapter"])
            .agg(pl.len().alias("count"))
            .sort(["count", canonicalCol], descending=[True, False])
        )
        for row in grouped.iter_rows(named=True):
            topic = row.get(canonicalCol)
            chapter = row.get("chapter")
            if isinstance(topic, str) and isinstance(chapter, str) and topic not in mapping:
                mapping[topic] = chapter

    company._cache[cacheKey] = mapping
    return mapping


def chapterForTopic(company: Company, topic: str) -> str:
    cm = chapterMap(company)
    if topic in cm:
        return cm[topic]
    if company._notesAccessor is not None:
        from dartlab.providers.dart.docs.notes import _REGISTRY as _NOTES_REGISTRY

        if topic in _NOTES_REGISTRY:
            return "XI"
    return "XII"


def topicLabel(company: Company, topic: str) -> str:
    from dartlab.core.registry import getEntry as _getEntry
    from dartlab.providers.dart.company import _TOPIC_LABELS, _getAllProperties

    if topic == "CIS":
        return "포괄손익계산서"
    if topic == "SCE":
        return "자본변동표"
    if topic in _TOPIC_LABELS:
        return _TOPIC_LABELS[topic]
    entry = _getEntry(topic)
    if entry is not None:
        return entry.label
    for name, label in _getAllProperties():
        if name == topic:
            return label
    return topic


def buildSections(company: Company) -> pl.DataFrame | None:
    """sections — docs + finance + report 통합 지도 (property 본체)."""
    from dartlab.providers.dart.company import _CHAPTER_TITLES, _topicForApiType
    from dartlab.providers.dart.docs.sections import reorderPeriodColumns

    cacheKey = "_sections"
    if cacheKey in company._cache:
        return company._cache[cacheKey]

    sectionsSource = company._docs.sections
    if sectionsSource is None:
        company._hintOnce("sections", "sections", "docs")
        company._cache[cacheKey] = None
        return None

    docsSec = sectionsSource.raw
    if docsSec is None:
        company._hintOnce("sections", "sections", "docs")
        company._cache[cacheKey] = None
        return None
    periodCols = [c for c in docsSec.columns if _isPeriodColumn(c)]
    cm = chapterMap(company)

    if "source" not in docsSec.columns:
        docsSec = docsSec.with_columns(pl.lit("docs").alias("source"))

    docsSchema = dict(docsSec.schema)
    if "source" not in docsSchema:
        docsSchema["source"] = pl.Utf8
    metaCols = [c for c in docsSec.columns if c not in periodCols]

    # finance/report에서 추가할 행 수집
    # key: topic → (chapter, source, maxBlockOrder)
    topicExtras: dict[str, list[dict[str, Any]]] = {}

    def _baseExtraRow(*, chapter: str, topic: str, source: str) -> dict[str, Any]:
        row = {col: None for col in metaCols}
        row.update(
            {
                "chapter": chapter,
                "topic": topic,
                "blockType": "table",
                "source": source,
            }
        )
        for p in periodCols:
            row[p] = None
        return row

    if company._hasFinance:
        for ft in ("BS", "IS", "CIS", "CF", "SCE"):
            if getattr(company._finance, ft, None) is not None:
                topicExtras.setdefault(ft, []).append(_baseExtraRow(chapter="III", topic=ft, source="finance"))
        if company._ratioSeries() is not None:
            topicExtras.setdefault("ratios", []).append(_baseExtraRow(chapter="III", topic="ratios", source="finance"))

    if company.rawReport is not None:
        try:
            for apiType in company._report.availableApiTypes:
                topic = _topicForApiType(apiType)
                chapter = cm.get(topic, "X")
                topicExtras.setdefault(topic, []).append(_baseExtraRow(chapter=chapter, topic=topic, source="report"))
        except (ValueError, KeyError, AttributeError) as e:
            import logging

            logging.getLogger(__name__).warning("sections report merge failed for %s: %s", company.stockCode, e)

    if not topicExtras:
        company._cache[cacheKey] = docsSec
        return docsSec

    # topic 순서대로 순회하면서 extra 행을 끼워넣기
    docsTopics = docsSec.get_column("topic").drop_nulls().unique(maintain_order=True).to_list()

    schema = docsSchema

    result_frames: list[pl.DataFrame] = []
    insertedExtras: set[str] = set()

    for topic in docsTopics:
        # 이 topic의 docs 행
        topicDocs = docsSec.filter(pl.col("topic") == topic)
        result_frames.append(topicDocs)

        # 이 topic에 대응하는 extra 행 → docs 블록 뒤에 append
        if topic in topicExtras:
            maxBo = topicDocs["blockOrder"].max()
            nextBo = (maxBo + 1) if maxBo is not None else 0
            for extra in topicExtras[topic]:
                extra["blockOrder"] = nextBo
                nextBo += 1
            result_frames.append(pl.DataFrame(topicExtras[topic], schema=schema))
            insertedExtras.add(topic)

    # docs에 없는 extra topic → 해당 chapter 위치에 독립 삽입
    orphanRows: list[dict[str, Any]] = []
    for topic, extras in topicExtras.items():
        if topic in insertedExtras:
            continue
        for extra in extras:
            extra["blockOrder"] = 0
            orphanRows.append(extra)

    if orphanRows:
        # chapter별로 그룹핑해서 해당 chapter의 마지막에 삽입
        orphanDf = pl.DataFrame(orphanRows, schema=schema)
        # result_frames 끝에 chapter 순서로 삽입
        for ch in _CHAPTER_TITLES.keys():
            chOrphans = orphanDf.filter(pl.col("chapter") == ch)
            if not chOrphans.is_empty():
                # 해당 chapter의 마지막 위치 찾기
                insertIdx = len(result_frames)
                for i, f in enumerate(result_frames):
                    if "chapter" in f.columns:
                        chapters = f["chapter"].to_list()
                        if ch in chapters:
                            insertIdx = i + 1
                result_frames.insert(insertIdx, chOrphans)

    if not result_frames:
        result = reorderPeriodColumns(docsSec, descending=True, annualAsQ4=True)
        company._cache[cacheKey] = result
        return result

    merged = pl.concat(result_frames, how="diagonal_relaxed")
    merged = reorderPeriodColumns(merged, descending=True, annualAsQ4=True)
    company._cache[cacheKey] = merged
    return merged
