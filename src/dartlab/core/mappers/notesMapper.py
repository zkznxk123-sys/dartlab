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


def _loadKeywords() -> dict[str, list[str]]:
    """notesStructure.json에서 keywords 로드.

    번들 필수 리소스 — 누락 시 loud-fail (2026-04-19 사고 class).
    """
    if not _STRUCTURE_PATH.exists():
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: {_STRUCTURE_PATH}\n  → pip install -U --force-reinstall dartlab"
        )
    data = json.loads(_STRUCTURE_PATH.read_text(encoding="utf-8"))
    return data.get("keywords", {})


# 코드에 데이터 0줄 — JSON이 단일 진실의 원천
NOTES_KEYWORDS: dict[str, list[str]] = _loadKeywords()


class NotesMapper(BaseMapper):
    """notes 항목 구조 매퍼."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _STRUCTURE_PATH
        self._cache: dict | None = None

    @property
    def name(self) -> str:
        """name — TODO 한국어 동작 설명."""
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

    def _aliases(self) -> dict[str, str]:
        return self._data().get("aliases", {})

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

    def resolveAlias(self, itemName: str) -> str:
        """항목명을 canonical로 정규화. 매핑 없으면 원본 반환.

        alias에서 _skip_* 로 시작하면 제거 대상.
        """
        import re

        normalized = re.sub(r"\s+", "", itemName)
        aliases = self._aliases()
        return aliases.get(normalized, itemName)

    def isSkip(self, itemName: str) -> bool:
        """파싱에서 제외할 항목인지."""
        # alias에서 _skip_ 으로 시작하면 제거
        resolved = self.resolveAlias(itemName)
        if resolved.startswith("_skip_"):
            return True
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
        """stats — TODO 한국어 동작 설명."""
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
        """allKeys — TODO 한국어 동작 설명."""
        return list(self._items().keys())

    def byCategory(self, cat: str) -> list[str]:
        """특정 카테고리의 항목 목록."""
        return [k for k, v in self._items().items() if v.get("category") == cat]

    def unmapped(self) -> list[str]:
        """type이 지정되지 않은 항목."""
        return [k for k, v in self._items().items() if "type" not in v]
