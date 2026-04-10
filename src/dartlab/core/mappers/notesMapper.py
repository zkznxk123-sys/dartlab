"""NotesMapper — notes 항목 구조 매퍼.

notesStructure.json을 읽어서 notes 항목의 유형(amount/rate/text),
외화 혼합 여부, 빈도, 카테고리 등을 제공한다.

Scanner가 2,700종목을 스캔해서 notesStructure.json을 생성/갱신하고,
이 매퍼가 그 데이터를 소비한다.

기존 pipeline.py의 하드코딩 heuristic을 데이터로 대체하는 것이 목표.
"""

from __future__ import annotations

import json
from pathlib import Path

from dartlab.core.mappers.engine import BaseMapper, MapperStats

_STRUCTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "notesStructure.json"

# notes 키워드 → 검색 별칭 (types.py에서 L0로 이동 — import direction 준수)
NOTES_KEYWORDS: dict[str, list[str]] = {
    "재고자산": ["재고자산"],
    "주당이익": ["주당이익", "주당순이익"],
    "충당부채": ["충당부채"],
    "차입금": ["차입금"],
    "매출채권": ["매출채권"],
    "리스": ["리스"],
    "투자부동산": ["투자부동산"],
    "무형자산": ["무형자산"],
    "법인세": ["법인세"],
    "특수관계자": ["특수관계자"],
    "약정사항": ["약정사항"],
    "금융자산": ["금융자산"],
    "공정가치": ["공정가치"],
    "이익잉여금": ["이익잉여금"],
    "금융부채": ["금융부채"],
    "기타포괄손익": ["기타포괄손익"],
    "사채": ["사채"],
    "종업원급여": ["종업원급여"],
    "퇴직급여": ["퇴직급여"],
    "확정급여": ["확정급여"],
    "재무위험": ["재무위험"],
    "우발부채": ["우발부채"],
    "담보": ["담보"],
}


class NotesMapper(BaseMapper):
    """notes 항목 구조 매퍼."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _STRUCTURE_PATH
        self._cache: dict | None = None

    @property
    def name(self) -> str:
        return "notes"

    def _data(self) -> dict:
        if self._cache is not None:
            return self._cache
        if self._path.exists():
            self._cache = json.loads(self._path.read_text(encoding="utf-8"))
        else:
            self._cache = {"_metadata": {}, "items": {}}
        return self._cache

    def _items(self) -> dict[str, dict]:
        return self._data().get("items", {})

    def reload(self) -> None:
        """캐시 무효화 — scanner 갱신 후 호출."""
        self._cache = None

    def lookup(self, key: str) -> dict | None:
        """항목명으로 구조 정보 조회.

        Returns:
            {"type": "amount"|"rate"|"text",
             "category": "inventory"|"borrowings"|...,
             "foreignCurrency": bool,
             "frequency": float,  # 0.0~1.0 (전체 종목 중 출현 비율)
             "skip": bool}  # True면 파싱에서 제외
        """
        items = self._items()
        if key in items:
            return {"name": key, **items[key]}

        # 정규화: 공백 제거 후 재시도
        import re

        normalized = re.sub(r"\s+", "", key)
        if normalized in items:
            return {"name": normalized, **items[normalized]}

        return None

    def isAmount(self, itemName: str) -> bool:
        """금액 항목인지 판별. 매핑 없으면 True (기본=금액)."""
        info = self.lookup(itemName)
        if info is None:
            return True  # 미등록 항목은 금액으로 간주
        return info.get("type") == "amount"

    def isSkip(self, itemName: str) -> bool:
        """파싱에서 제외할 항목인지."""
        info = self.lookup(itemName)
        if info is None:
            return False
        return info.get("skip", False)

    def hasForeignCurrency(self, itemName: str) -> bool:
        """외화 혼합 항목인지."""
        info = self.lookup(itemName)
        if info is None:
            return False
        return info.get("foreignCurrency", False)

    def category(self, itemName: str) -> str | None:
        """항목의 카테고리 (inventory, borrowings, ...)."""
        info = self.lookup(itemName)
        return info.get("category") if info else None

    def stats(self) -> MapperStats:
        items = self._items()
        meta = self._data().get("_metadata", {})
        amountItems = sum(1 for v in items.values() if v.get("type") == "amount")
        return MapperStats(
            name=self.name,
            totalEntries=len(items),
            mappedEntries=amountItems,
            coverage=amountItems / len(items) if items else 0.0,
            lastUpdated=meta.get("lastScan", ""),
        )

    def allKeys(self) -> list[str]:
        return list(self._items().keys())

    def byCategory(self, cat: str) -> list[str]:
        """특정 카테고리의 항목 목록."""
        return [k for k, v in self._items().items() if v.get("category") == cat]

    def unmapped(self) -> list[str]:
        """type이 지정되지 않은 항목."""
        return [k for k, v in self._items().items() if "type" not in v]
