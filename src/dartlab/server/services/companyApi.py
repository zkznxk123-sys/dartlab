from __future__ import annotations

import re as _re
from typing import Any

from dartlab import Company

from ..api.common import HANDLED_API_ERRORS
from ..cache import companyCache
from ..models import TocChapter, TocResponse, TocTopic

_VALID_CODE = _re.compile(r"^[A-Za-z0-9가-힣]{1,20}$")


def getCompany(code: str) -> Company:
    """종목코드로 Company를 조회하거나 생성한다 (캐시 활용)."""
    if not _VALID_CODE.match(code):
        raise ValueError(f"유효하지 않은 종목코드: {code!r}")
    cached = companyCache.get(code)
    if cached:
        return cached[0]
    company = Company(code)
    companyCache.put(code, company, None)
    return company


get_company = getCompany


def safeTopicLabel(company, topic: str) -> str:
    """topic의 한글 라벨을 안전하게 반환한다."""
    try:
        return company._topicLabel(topic)
    except AttributeError:
        return topic


def _findPrevComparable(periods: list[str], target: str) -> str | None:
    import re

    match = re.fullmatch(r"(\d{4})(Q[1-4])?", target)
    if not match:
        return None
    year, quarter = int(match.group(1)), match.group(2)
    best: str | None = None
    best_year = -1
    for period in periods:
        if period == target:
            continue
        period_match = re.fullmatch(r"(\d{4})(Q[1-4])?", period)
        if not period_match:
            continue
        period_year, period_quarter = int(period_match.group(1)), period_match.group(2)
        if quarter == period_quarter and period_year < year and period_year > best_year:
            best = period
            best_year = period_year
    return best


def filterBlocksByPeriod(blocks: list, period: str) -> list:
    """뷰어 블록을 지정 기간과 직전 비교 기간만 남기도록 필터링한다."""
    filtered = []
    for block in blocks:
        if block.data is None:
            filtered.append(block)
            continue

        all_periods = block.meta.periods if block.meta.periods else []
        if period not in all_periods:
            filtered.append(block)
            continue

        prev = _findPrevComparable(all_periods, period)
        keep_periods = [p for p in [period, prev] if p is not None and p in block.data.columns]
        non_period_cols = [column for column in block.data.columns if column not in all_periods]
        select_cols = non_period_cols + keep_periods

        from copy import copy

        new_block = copy(block)
        new_block.data = block.data.select([column for column in select_cols if column in block.data.columns])
        new_block.meta = type(block.meta)(
            unit=block.meta.unit,
            scale=block.meta.scale,
            scaleDivisor=block.meta.scaleDivisor,
            periods=keep_periods,
            rowCount=block.meta.rowCount,
            colCount=len(keep_periods),
        )
        filtered.append(new_block)
    return filtered


# DART 정기보고서 표준 11 장 — Roman numeral → 한글 풀네임.
# 원본 sections.parquet 의 `chapter` 컬럼은 "I"/"II"/.. 만 들고와 한글 풀네임
# 없음. 본 매핑이 사용자 노출용 라벨 표준.
_DART_CHAPTERS_KR: dict[str, str] = {
    "I": "I. 회사의 개요",
    "II": "II. 사업의 내용",
    "III": "III. 재무에 관한 사항",
    "IV": "IV. 이사의 경영진단 및 분석의견 등",
    "V": "V. 회계감사인의 감사의견 등",
    "VI": "VI. 이사회 등 회사의 기관에 관한 사항",
    "VII": "VII. 주주에 관한 사항",
    "VIII": "VIII. 임원 및 직원 등에 관한 사항",
    "IX": "IX. 계열회사 등에 관한 사항",
    "X": "X. 대주주 등과의 거래내용",
    "XI": "XI. 그 밖에 투자자 보호를 위하여 필요한 사항",
}


def _chapterLabelKr(chapter: str) -> str:
    """chapter 키 (예 "I", "II.", "III. 재무에 관한 사항") → 표준 한글 풀네임."""
    if not isinstance(chapter, str):
        return str(chapter)
    raw = chapter.strip()
    if not raw:
        return raw
    # 이미 풀네임 박혀있으면 그대로 (finance_chapter 처럼 코드에서 박은 것).
    if "." in raw and len(raw.split(".", 1)[-1].strip()) > 0:
        return raw
    prefix = raw.split(".")[0].strip()
    return _DART_CHAPTERS_KR.get(prefix, raw)


# dartlab 내부 topic key → DART 정기보고서 표준 한글 라벨.
# safeTopicLabel (Company._topicLabel) 의 결과 ("회사개요정량" 식 dartlab 단축형) 가
# 사용자 노출이라 부적절 — DART 원본 라벨과 일치시켜야 사용자가 인지 가능.
_DART_TOPIC_LABEL: dict[str, str] = {
    # I. 회사의 개요
    "companyOverview": "회사의 개요",
    "companyHistory": "회사의 연혁",
    "capitalChange": "자본금 변동사항",
    "shareCapital": "주식의 총수 등",
    "articlesOfIncorporation": "정관에 관한 사항",
    "dividend": "배당에 관한 사항",
    # II. 사업의 내용
    "businessOverview": "사업의 개요",
    "productService": "주요 제품 및 서비스",
    "rawMaterial": "원재료 및 생산설비",
    "salesOrder": "매출 및 수주상황",
    "riskDerivative": "위험관리 및 파생거래",
    "majorContractsAndRnd": "주요계약 및 연구개발활동",
    "otherReferences": "기타 참고사항",
    # III. 재무에 관한 사항
    "fsSummary": "요약재무정보",
    "consolidatedStatements": "연결재무제표",
    "consolidatedNotes": "연결재무제표 주석",
    "financialStatements": "재무제표",
    "financialNotes": "재무제표 주석",
    "ratios": "재무비율",
    "BS": "재무상태표",
    "IS": "손익계산서",
    "CIS": "포괄손익계산서",
    "CF": "현금흐름표",
    "SCE": "자본변동표",
    # IV. 이사의 경영진단 및 분석의견 등
    "cautionaryStatement": "주의사항",
    "mdnaOverview": "이사의 경영진단 및 분석의견 개요",
    "financialConditionAndResults": "재무상태 및 영업실적",
    "liquidityAndCapitalResources": "유동성 및 자금조달",
    "otherFinance": "기타 재무사항",
    "audit": "회계감사인의 감사의견",
    # V. 회계감사인의 감사의견 등
    "mdna": "경영진단 및 분석의견",
    "internalControl": "내부통제에 관한 사항",
    "auditContract": "감사용역 계약",
    "nonAuditContract": "비감사용역 계약",
}


def _topicDartLabel(topic: str, fallback: str | None = None) -> str:
    """topic 키 → DART 표준 한글 라벨. 매핑 부재 시 fallback 또는 topic 그대로."""
    label = _DART_TOPIC_LABEL.get(topic)
    if label:
        return label
    return fallback or topic


# period (예 "2024Q1") → 정기보고서 기준월 패턴 (예 "(2024.03)").
def _periodToReportPattern(period: str) -> str | None:
    import re as _re

    match = _re.fullmatch(r"(\d{4})(?:Q([1-4]))?", period.strip())
    if not match:
        return None
    year = match.group(1)
    quarter = match.group(2)
    if quarter is None or quarter == "4":
        return f"({year}.12)"  # 사업보고서 (연간 또는 Q4)
    if quarter == "1":
        return f"({year}.03)"
    if quarter == "2":
        return f"({year}.06)"
    if quarter == "3":
        return f"({year}.09)"
    return None


def _dartUrlForPeriod(company: Company, period: str | None = None) -> str | None:
    """period 에 해당하는 정기보고서의 DART 뷰어 URL.

    period=None → 최신 보고서. period 매칭 row 없으면 최신으로 fallback.
    """
    try:
        df = company.filings()
        if df is None or df.is_empty():
            return None
        latest_url = df.row(0, named=True).get("dartUrl")
        if period is None:
            return latest_url

        import polars as pl

        pattern = _periodToReportPattern(period)
        if pattern is None:
            return latest_url
        matched = df.filter(pl.col("reportType").str.contains(pattern, literal=True))
        if matched.is_empty():
            return latest_url
        return matched.row(0, named=True).get("dartUrl")
    except (AttributeError, ValueError, KeyError):
        return None


# 옛 별칭 — 외부 caller 호환.
_latestDartUrl = _dartUrlForPeriod


def buildToc(company: Company, *, metaOnly: bool = False) -> dict[str, Any]:
    """뷰어 목차(Table of Contents)를 구성한다.

    Args:
        company: Company 인스턴스.
        metaOnly: True 면 chapter/topic 트리 + textCount/tableCount 만 반환
            하고 `hasChanges` (period 간 비교) 계산을 skip. period 비교가
            sections frame 의 iter_rows 전체 순회라 가장 무거운 부분 —
            TOC 진입 시 화면 표시에 필요 없으면 metaOnly=True.
    """
    sec = company.sections
    if sec is None:
        return TocResponse(stockCode=company.stockCode, corpName=company.corpName, chapters=[]).model_dump()

    import re as _re

    import polars as pl

    chapter_map: dict[str, list[TocTopic]] = {}
    chapter_order: list[str] = []
    seen_topics: set[str] = set()

    finance_topics = ("BS", "IS", "CIS", "CF", "SCE", "ratios")
    finance_chapter = "III. 재무에 관한 사항"
    for topic in finance_topics:
        try:
            df = getattr(company, topic, None) if topic != "ratios" else None
            if topic == "ratios":
                ratio_pair = company._ratioSeries() if getattr(company, "_hasFinance", False) else None
                if ratio_pair is None:
                    continue
            elif df is None:
                continue
        except (AttributeError, TypeError):
            continue
        seen_topics.add(topic)
        if finance_chapter not in chapter_map:
            chapter_map[finance_chapter] = []
            chapter_order.append(finance_chapter)
        chapter_map[finance_chapter].append(
            TocTopic(
                topic=topic,
                label=_topicDartLabel(topic, safeTopicLabel(company, topic)),
                textCount=0,
                tableCount=1,
            )
        )

    period_re = _re.compile(r"^\d{4}(Q[1-4])?$")
    period_cols = sorted([col for col in sec.columns if period_re.fullmatch(col)], reverse=True)
    latest2 = period_cols[:2] if (not metaOnly and len(period_cols) >= 2) else []

    if "topic" in sec.columns:
        for row in sec.iter_rows(named=True):
            topic = row.get("topic")
            if not isinstance(topic, str) or not topic or topic in seen_topics:
                continue
            seen_topics.add(topic)

            topic_frame = sec.filter(pl.col("topic") == topic)
            block_types = topic_frame["blockType"] if "blockType" in topic_frame.columns else None
            text_count = block_types.eq("text").sum() if block_types is not None else topic_frame.height
            table_count = block_types.eq("table").sum() if block_types is not None else 0

            has_changes = False
            if latest2 and block_types is not None:
                text_rows = topic_frame.filter(pl.col("blockType") == "text")
                for text_row in text_rows.iter_rows(named=True):
                    current = str(text_row.get(latest2[0]) or "").strip()
                    previous = str(text_row.get(latest2[1]) or "").strip()
                    if current and previous and current != previous:
                        has_changes = True
                        break

            chapter_value = topic_frame.item(0, "chapter") if "chapter" in topic_frame.columns else None
            chapter_raw = chapter_value if isinstance(chapter_value, str) and chapter_value else "기타"
            chapter = _chapterLabelKr(chapter_raw)
            if chapter not in chapter_map:
                chapter_map[chapter] = []
                chapter_order.append(chapter)
            chapter_map[chapter].append(
                TocTopic(
                    topic=topic,
                    label=_topicDartLabel(topic, safeTopicLabel(company, topic)),
                    textCount=int(text_count),
                    tableCount=int(table_count),
                    hasChanges=has_changes,
                )
            )

    roman_order = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
    }

    def _chapterSortKey(chapter: str) -> tuple[int, str]:
        prefix = chapter.split(".")[0].strip()
        return (roman_order.get(prefix, 99), chapter)

    sorted_chapters = sorted(chapter_order, key=_chapterSortKey)
    # DART 표준 — chapter 안 topics 자연 순서대로 1, 2, 3... 번호. 이미 "N." 접두 있으면
    # 중복 안 박음 (idempotent).
    for chapter in sorted_chapters:
        topics = chapter_map[chapter]
        for idx, t in enumerate(topics, 1):
            current = t.label or t.topic
            if _re.match(r"^\d+\.\s", current):
                continue
            t.label = f"{idx}. {current}"
    chapters = [TocChapter(chapter=chapter, topics=chapter_map[chapter]) for chapter in sorted_chapters]
    return TocResponse(stockCode=company.stockCode, corpName=company.corpName, chapters=chapters).model_dump()


_VIEWER_COMPACT_SECTION_KEEP = (
    "id",
    "headingPath",
    "status",
    "latestChange",
    "preview",
    "latest",  # 최신 본문 풀텍스트 (body / status / period / digest) — prose 렌더
    "latestPeriod",
    "firstPeriod",
    "periodCount",
    "timeline",  # 우 패널 시간축 (period 별 status 배열)
)


def _compactTextDocument(
    doc: dict[str, Any] | None,
    *,
    limit: int,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """경량 textDocument 변환 — 읽기 가능한 prose 본문 + 우 패널 history 데이터 보존.

    Keep: latest (풀 본문 + digest), timeline (시간축), headingPath, status,
    latestChange, latestPeriod, firstPeriod, periodCount, preview.
    Drop: views (period 별 풀텍스트 dict — `?period=X` 로 lazy fetch).
    Add: entries (kind=section|block_ref, order 보존) + tables (raw_markdown
         blocks 의 period→markdown dict) — 표 inline 렌더용.
    """
    if doc is None:
        return None
    sections = doc.get("sections") or []
    total = len(sections)
    sliced = sections[:limit] if limit > 0 else sections
    compactSections = [{key: section.get(key) for key in _VIEWER_COMPACT_SECTION_KEEP} for section in sliced]
    entries = doc.get("entries") or []
    # raw_markdown + finance 블록 → block id → {period: markdown}.
    # finance.data 는 columns/rows 구조이므로 period 별 [항목, value(억원)] 표로 변환.
    tables: dict[int, dict[str, str]] = {}
    for b in (blocks or []):
        kind = b.get("kind")
        bid = b.get("block")
        if bid is None:
            continue
        if kind == "raw_markdown":
            rm = b.get("rawMarkdown")
            if not isinstance(rm, dict):
                continue
            cleaned = {p: v for p, v in rm.items() if isinstance(v, str) and v.strip()}
            if cleaned:
                tables[int(bid)] = cleaned
        elif kind == "finance":
            data = b.get("data") or {}
            cols = data.get("columns") or []
            rows = data.get("rows") or []
            meta = b.get("meta") or {}
            scale_div = meta.get("scaleDivisor") or 1.0
            scale_lbl = meta.get("scale") or ""
            # period 별 단순 markdown 표 — | 항목 | 값(억원) |
            per_period: dict[str, str] = {}
            label_col = "항목" if "항목" in cols else (cols[1] if len(cols) > 1 else cols[0] if cols else "")
            periods = [c for c in cols if c not in {"snakeId", label_col}]
            unit_hint = f" ({scale_lbl})" if scale_lbl else ""
            for p in periods:
                lines = [f"| 항목 | 값{unit_hint} |", "| --- | --- |"]
                any_row = False
                for row in rows:
                    label = row.get(label_col)
                    val = row.get(p)
                    if val is None or label is None:
                        continue
                    try:
                        scaled = float(val) / scale_div
                        if abs(scaled) >= 100:
                            display = f"{scaled:,.0f}"
                        else:
                            display = f"{scaled:,.2f}"
                    except (TypeError, ValueError):
                        display = str(val)
                    lines.append(f"| {label} | {display} |")
                    any_row = True
                if any_row:
                    per_period[p] = "\n".join(lines)
            if per_period:
                tables[int(bid)] = per_period
    # td.periods 가 비어있으면 finance block meta.periods 로 보충 (IS/CF/BS/CIS/SCE
    # topic 은 finance block 만 있고 sections 0 이라 td.periods=[] 로 옴).
    periods = doc.get("periods")
    if not periods:
        derived: list[Any] = []
        seen_period: set[str] = set()
        for b in (blocks or []):
            meta = b.get("meta") or {}
            for pl in (meta.get("periods") or []):
                if isinstance(pl, str) and pl not in seen_period:
                    seen_period.add(pl)
                    # PeriodRef 와 호환되는 dict 형태 — frontend _periodLabel 이 label 키 우선.
                    derived.append({"label": pl})
        if derived:
            periods = derived
    return {
        "topic": doc.get("topic"),
        "mode": doc.get("mode"),
        "periods": periods,
        "latestPeriod": doc.get("latestPeriod"),
        "firstPeriod": doc.get("firstPeriod"),
        "sectionCount": doc.get("sectionCount", total),
        "updatedCount": doc.get("updatedCount"),
        "newCount": doc.get("newCount"),
        "staleCount": doc.get("staleCount"),
        "stableCount": doc.get("stableCount"),
        "totalSectionCount": total,
        "truncated": total > len(sliced),
        "sections": compactSections,
        "entries": entries,
        "tables": tables,
    }


def buildViewer(
    company: Company,
    topic: str,
    *,
    compact: bool = False,
    limit: int = 60,
    period: str | None = None,
) -> dict[str, Any]:
    """topic별 뷰어 블록과 텍스트 문서를 직렬화하여 반환한다.

    compact=True 면 frontend 가 안 쓰는 무거운 필드 (views/timeline/blocks/
    entries) 를 제거하고 sections 를 limit 개로 잘라낸다. payload 80%+ 감소.
    period 인자는 dartUrl 해상도 용도 — period 매칭 보고서 URL 반환 (None 이면 최신).
    """
    from dartlab.providers.dart.docs.viewer import (
        serializeViewerBlock,
        serializeViewerTextDocument,
        viewerBlocks,
        viewerTextDocument,
    )

    if not hasattr(company, "_viewer_cache"):
        company._viewer_cache = {}
    if topic in company._viewer_cache:
        blocks = company._viewer_cache[topic]
    else:
        blocks = viewerBlocks(company, topic)
        company._viewer_cache[topic] = blocks

    textDoc = serializeViewerTextDocument(viewerTextDocument(topic, blocks))
    dartUrl = _dartUrlForPeriod(company, period)
    topicLabel = _topicDartLabel(topic, safeTopicLabel(company, topic))
    if compact:
        serializedBlocks = [serializeViewerBlock(b) for b in blocks]
        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "topic": topic,
            "topicLabel": topicLabel,
            "period": None,
            "compact": True,
            "dartUrl": dartUrl,
            "textDocument": _compactTextDocument(textDoc, limit=limit, blocks=serializedBlocks),
        }

    return {
        "stockCode": company.stockCode,
        "corpName": company.corpName,
        "topic": topic,
        "topicLabel": topicLabel,
        "period": None,
        "dartUrl": dartUrl,
        "blocks": [serializeViewerBlock(block) for block in blocks],
        "textDocument": textDoc,
    }


def buildDiffSummary(company: Company, topic: str) -> dict[str, Any] | None:
    """topic의 기간 간 변경 요약(변경률, 추가/삭제 발췌)을 생성한다."""
    try:
        from dartlab.providers.docs.diff import sectionsDiff

        sec = company._docs.sections
        if sec is None:
            return None

        diffResult = sectionsDiff(sec)
        topic_summaries = [summary for summary in diffResult.summaries if summary.topic == topic]
        total_changed = sum(summary.changedCount for summary in topic_summaries)
        max_periods = max((summary.totalPeriods for summary in topic_summaries), default=0)
        change_rate = (
            round(total_changed / max(1, (max_periods - 1) * len(topic_summaries)), 3) if topic_summaries else 0.0
        )

        topic_entries = [entry for entry in diffResult.entries if entry.topic == topic]
        added: list[str] = []
        removed: list[str] = []
        latest_from: str | None = None
        latest_to: str | None = None

        if topic_entries:
            import difflib

            import polars as pl

            latest = max(topic_entries, key=lambda entry: entry.toPeriod)
            latest_from = latest.fromPeriod
            latest_to = latest.toPeriod

            filtered = sec.filter(pl.col("topic") == topic)
            for row in filtered.iter_rows(named=True):
                from_text = str(row.get(latest_from) or "").strip()
                to_text = str(row.get(latest_to) or "").strip()
                if not from_text and not to_text:
                    continue
                if from_text == to_text:
                    continue
                from_lines = from_text.splitlines()
                to_lines = to_text.splitlines()
                for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, from_lines, to_lines).get_opcodes():
                    if tag in ("insert", "replace"):
                        for line in to_lines[j1:j2]:
                            line = line.strip()
                            if line and len(added) < 3:
                                added.append(line[:120])
                    if tag in ("delete", "replace"):
                        for line in from_lines[i1:i2]:
                            line = line.strip()
                            if line and len(removed) < 3:
                                removed.append(line[:120])
                if len(added) >= 3 and len(removed) >= 3:
                    break

        return {
            "stockCode": company.stockCode,
            "corpName": company.corpName,
            "topic": topic,
            "changeRate": change_rate,
            "changedCount": total_changed,
            "totalPeriods": max_periods,
            "latestFrom": latest_from,
            "latestTo": latest_to,
            "added": added,
            "removed": removed,
        }
    except HANDLED_API_ERRORS:
        return None
