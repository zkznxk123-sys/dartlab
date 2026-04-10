"""Notes Scanner — 종목별 notes 구조 패턴 스캔.

2,700종목의 docs parquet에서 notes 항목의 구조 패턴을 추출하여
notesStructure.json을 갱신한다.

사용법::

    from dartlab.core.mappers.scanner import scanNotes, scanAll

    # 단일 종목 스캔
    result = scanNotes("005930")

    # 전체 종목 스캔 → notesStructure.json 갱신
    stats = scanAll(limit=100)  # 테스트용 100종목
    stats = scanAll()           # 전체 (~2,700종목, 수십 분)
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from dartlab.core.mappers.common import normalizeName

log = logging.getLogger(__name__)

_STRUCTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "notesStructure.json"

# 비금액 패턴 — pipeline.py의 _NON_AMOUNT_PATTERNS + 추가 발견 패턴
_RATE_PATTERNS = re.compile(
    r"(연이자율|이자율|할인율|수익률|배당률|증가율|성장률|비율|%)",
    re.IGNORECASE,
)

_TEXT_PATTERNS = re.compile(
    r"(기술$|설명$|기술:$|에\s*대한\s*(기술|설명)|내용$|사유$|비고$)",
    re.IGNORECASE,
)

# 외화 관련 항목명 패턴
_FOREIGN_NAME_PATTERNS = re.compile(
    r"(외화|USD|JPY|EUR|GBP|CNY|HKD|달러|엔화|위안)",
    re.IGNORECASE,
)


def _classifyType(name: str, values: list[str]) -> str:
    """항목명 + 값에서 유형 자동 분류."""
    if _RATE_PATTERNS.search(name):
        return "rate"
    if _TEXT_PATTERNS.search(name):
        return "text"
    # 값에서 % 문자가 지배적이면 rate
    pct_count = sum(1 for v in values if "%" in str(v))
    if pct_count > len(values) * 0.5 and values:
        return "rate"
    return "amount"


def _hasForeignInName(name: str) -> bool:
    """항목명에 외화 관련 키워드가 있는지."""
    return bool(_FOREIGN_NAME_PATTERNS.search(name))


def scanNotes(stockCode: str) -> dict[str, dict[str, Any]]:
    """단일 종목의 notes 구조 패턴 추출.

    Returns:
        {항목명: {"type": ..., "category": ..., "foreignCurrency": bool, "values_sample": [...]}}
    """
    try:
        from dartlab.core.dataLoader import loadData
        from dartlab.core.notesExtractor import extractNotesContent, findNumberedSection
        from dartlab.core.reportSelector import selectReport
        from dartlab.core.tableParser import parseNotesTable
        from dartlab.core.mappers.notesMapper import NOTES_KEYWORDS
    except ImportError:
        return {}

    try:
        df = loadData(stockCode)
    except (FileNotFoundError, OSError, ValueError):
        return {}

    years = sorted(df["year"].unique().to_list(), reverse=True)[:3]  # 최근 3년만
    items: dict[str, dict[str, Any]] = {}

    for keyword, aliases in NOTES_KEYWORDS.items():
        for year in years:
            try:
                report = selectReport(df, year, reportKind="annual")
            except (KeyError, TypeError, ValueError):
                continue
            if report is None:
                continue

            contents = extractNotesContent(report)
            if not contents:
                continue

            section = None
            for kw in aliases:
                section = findNumberedSection(contents, kw)
                if section is not None:
                    break
            if section is None:
                continue

            try:
                parsed = parseNotesTable(section)
            except (IndexError, KeyError, TypeError, ValueError):
                continue
            if not parsed:
                continue

            for block in parsed:
                for item in block.get("items", []):
                    name = normalizeName(item["name"])
                    if not name:
                        continue
                    values = item.get("values", [])
                    itemType = _classifyType(name, values)
                    foreign = _hasForeignInName(name)

                    if name not in items:
                        items[name] = {
                            "type": itemType,
                            "category": keyword,
                            "foreignCurrency": foreign,
                            "count": 0,
                        }
                    items[name]["count"] += 1
            break  # 첫 연도만 (구조 파악 목적)

    return items


def scanAll(
    limit: int | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    """전체 종목 notes 구조 스캔 → notesStructure.json 갱신.

    Args:
        limit: 스캔 종목 수 제한 (None=전체)
        output: 결과 저장 경로 (None=기본 경로)

    Returns:
        {"scanned": int, "newItems": int, "updatedItems": int, "totalItems": int}
    """
    outPath = output or _STRUCTURE_PATH

    # 기존 구조 로드
    existing: dict[str, Any] = {"_metadata": {}, "items": {}}
    if outPath.exists():
        existing = json.loads(outPath.read_text(encoding="utf-8"))

    existingItems = existing.get("items", {})

    # 종목 목록 가져오기
    try:
        from dartlab.core.dataConfig import DATA_RELEASES

        dataDir = Path(DATA_RELEASES["docs"]["localDir"])
    except (ImportError, KeyError):
        log.warning("데이터 디렉토리 없음 — 스캔 불가")
        return {"scanned": 0, "newItems": 0, "updatedItems": 0, "totalItems": len(existingItems)}

    if not dataDir.exists():
        log.warning("docs 디렉토리 없음: %s", dataDir)
        return {"scanned": 0, "newItems": 0, "updatedItems": 0, "totalItems": len(existingItems)}

    stockCodes = sorted(
        p.stem for p in dataDir.glob("*.parquet") if len(p.stem) == 6 and p.stem.isdigit()
    )
    if limit:
        stockCodes = stockCodes[:limit]

    log.info("notes 구조 스캔 시작: %d종목", len(stockCodes))

    # 종목별 항목 출현 카운트
    globalCounts: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"type": "amount", "category": "", "foreignCurrency": False, "companyCount": 0}
    )

    scanned = 0
    for i, code in enumerate(stockCodes):
        try:
            items = scanNotes(code)
        except (MemoryError, OSError):
            log.warning("스캔 실패 (메모리): %s", code)
            continue

        for name, info in items.items():
            entry = globalCounts[name]
            entry["companyCount"] += 1
            # 유형은 다수결
            if info["type"] != "amount":
                entry["type"] = info["type"]
            if info["foreignCurrency"]:
                entry["foreignCurrency"] = True
            if info["category"] and not entry["category"]:
                entry["category"] = info["category"]

        scanned += 1
        if (i + 1) % 100 == 0:
            log.info("  스캔 진행: %d/%d", i + 1, len(stockCodes))

        # 메모리 안전: 500종목마다 gc
        if (i + 1) % 500 == 0:
            import gc

            gc.collect()

    # 기존 + 신규 병합
    newCount = 0
    updatedCount = 0
    for name, info in globalCounts.items():
        freq = info["companyCount"] / scanned if scanned > 0 else 0.0
        entry = {
            "type": info["type"],
            "category": info["category"],
            "foreignCurrency": info["foreignCurrency"],
            "frequency": round(freq, 4),
            "skip": info["type"] in ("rate", "text"),
        }
        if name in existingItems:
            # 기존 항목 — frequency만 갱신, type은 기존 유지 (수동 보정 보존)
            existingItems[name]["frequency"] = entry["frequency"]
            if existingItems[name].get("category") == "":
                existingItems[name]["category"] = entry["category"]
            updatedCount += 1
        else:
            existingItems[name] = entry
            newCount += 1

    # 저장
    result = {
        "_metadata": {
            "version": "1.0.0",
            "lastScan": datetime.now().strftime("%Y-%m-%d"),
            "companiesScanned": scanned,
            "description": "notes 항목 구조 매퍼 — Scanner 자동 생성",
        },
        "items": dict(sorted(existingItems.items())),
    }
    outPath.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    stats = {
        "scanned": scanned,
        "newItems": newCount,
        "updatedItems": updatedCount,
        "totalItems": len(existingItems),
    }
    log.info("스캔 완료: %s", stats)
    return stats
