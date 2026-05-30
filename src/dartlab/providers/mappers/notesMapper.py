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

from dartlab.core.mapperEngine import BaseMapper, MapperStats

_STRUCTURE_PATH = Path(__file__).resolve().parent / "mapperData" / "notesStructure.json"


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
        """매퍼 이름 — ``"notes"`` 고정 식별자 (registry/diff 비교용).

        Returns:
            항상 ``"notes"``.

        Example:
            >>> NotesMapper().name
            'notes'

        Raises:
            없음.
        """
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
        """캐시 무효화 — scanner 갱신 후 호출.

        Example:
            >>> m = NotesMapper(); m.reload()  # 다음 lookup 시 JSON 재로드

        Raises:
            없음 — 다음 조회 시점에 lazy 재로드.
        """
        self._cache = None

    def lookup(self, key: str) -> dict | None:
        """항목명으로 구조 정보 조회. 정확 매칭 실패 시 공백 제거 후 재시도.

        Args:
            key: 항목명 (정규화 전/후 모두 허용).

        Returns:
            {"name", "type": "amount"|"rate"|"text", "category", "foreignCurrency": bool,
             "frequency": float(0~1), "skip": bool}. 미등록 항목은 None.

        Example:
            >>> NotesMapper().lookup("재고자산")  # doctest: +SKIP
            {'name': '재고자산', 'type': 'amount', 'category': '재고자산', ...}

        Raises:
            없음 — 미등록 시 None 반환.
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
        """금액 항목인지 판별. 매핑 없으면 True (기본=금액).

        Args:
            itemName: 항목명.

        Returns:
            type 이 "amount" 또는 미등록이면 True. rate/text 면 False.

        Example:
            >>> NotesMapper().isAmount("미등록항목")
            True

        Raises:
            없음.
        """
        info = self.lookup(itemName)
        if info is None:
            return True  # 미등록 항목은 금액으로 간주
        return info.get("type") == "amount"

    def resolveAlias(self, itemName: str) -> str:
        """항목명을 canonical 로 정규화. 매핑 없으면 원본 반환.

        공백 제거 후 alias dict 조회. canonical 이 ``_skip_*`` 면 제거 대상 신호.

        Args:
            itemName: 항목명 (variant 가능).

        Returns:
            canonical 항목명. alias 미등록이면 입력 원본.

        Example:
            >>> NotesMapper().resolveAlias("재고자산계")  # doctest: +SKIP
            '재고자산'

        Raises:
            없음.
        """
        import re

        normalized = re.sub(r"\s+", "", itemName)
        aliases = self._aliases()
        return aliases.get(normalized, itemName)

    def isSkip(self, itemName: str) -> bool:
        """파싱에서 제외할 항목인지.

        ``_skip_`` alias 또는 등록 항목의 skip 플래그(rate/text)로 판정.

        Args:
            itemName: 항목명.

        Returns:
            제외 대상이면 True. 미등록이면 False.

        Example:
            >>> NotesMapper().isSkip("미등록항목")
            False

        Raises:
            없음.
        """
        # alias에서 _skip_ 으로 시작하면 제거
        resolved = self.resolveAlias(itemName)
        if resolved.startswith("_skip_"):
            return True
        info = self.lookup(itemName)
        if info is None:
            return False
        return info.get("skip", False)

    def hasForeignCurrency(self, itemName: str) -> bool:
        """외화 혼합 항목인지.

        Args:
            itemName: 항목명.

        Returns:
            등록 항목의 foreignCurrency 플래그. 미등록이면 False.

        Example:
            >>> NotesMapper().hasForeignCurrency("미등록항목")
            False

        Raises:
            없음.
        """
        info = self.lookup(itemName)
        if info is None:
            return False
        return info.get("foreignCurrency", False)

    def category(self, itemName: str) -> str | None:
        """항목의 카테고리 (inventory, borrowings, ...).

        Args:
            itemName: 항목명.

        Returns:
            카테고리 문자열. 미등록·카테고리 부재면 None.

        Example:
            >>> NotesMapper().category("재고자산")  # doctest: +SKIP
            '재고자산'

        Raises:
            없음.
        """
        info = self.lookup(itemName)
        return info.get("category") if info else None

    def stats(self) -> MapperStats:
        """매퍼 통계 — 총 항목 수 / 금액 항목 비율 (coverage) / 마지막 스캔 시각.

        Returns:
            MapperStats(name, totalEntries, mappedEntries=금액항목수, coverage, lastUpdated).

        Example:
            >>> NotesMapper().stats().name
            'notes'

        Raises:
            없음 — 빈 매퍼면 coverage 0.0.
        """
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
        """등록된 항목 키 list — items dict 키 순서 유지.

        Returns:
            등록 항목명 전체 list.

        Example:
            >>> isinstance(NotesMapper().allKeys(), list)
            True

        Raises:
            없음.
        """
        return list(self._items().keys())

    def byCategory(self, cat: str) -> list[str]:
        """특정 카테고리의 항목 목록.

        Args:
            cat: 카테고리 키 (inventory, borrowings, ...).

        Returns:
            해당 카테고리 항목명 list. 매칭 없으면 빈 list.

        Example:
            >>> NotesMapper().byCategory("재고자산")  # doctest: +SKIP
            ['재고자산', '제품및상품', ...]

        Raises:
            없음.
        """
        return [k for k, v in self._items().items() if v.get("category") == cat]

    def unmapped(self) -> list[str]:
        """type 이 지정되지 않은 항목.

        Returns:
            type 키 부재 항목명 list (스캔 미분류 잔여).

        Example:
            >>> isinstance(NotesMapper().unmapped(), list)
            True

        Raises:
            없음.
        """
        return [k for k, v in self._items().items() if "type" not in v]
