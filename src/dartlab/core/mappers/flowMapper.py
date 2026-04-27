"""FlowMapper — _EVENT_ACCOUNTS 읽기 전용 래퍼.

기존 flow.py의 _EVENT_ACCOUNTS(14 항목)를
MapperEngine 인터페이스로 래핑한다. 원본 코드 수정 0줄.

flow 계정 분류: event(비정기) vs regular(매 분기).
event 계정은 4분기 strict 합산 대신 있는 분기만 합산.
"""

from __future__ import annotations

from dartlab.core.mappers.engine import BaseMapper, MapperStats


class FlowMapper(BaseMapper):
    """_EVENT_ACCOUNTS (이벤트성 계정 분류) 래퍼."""

    @property
    def name(self) -> str:
        return "flow"

    def _eventAccounts(self) -> frozenset:
        from dartlab.core.utils.flow import _EVENT_ACCOUNTS

        return _EVENT_ACCOUNTS

    def lookup(self, key: str) -> dict | None:
        """계정명으로 flow 유형 조회.

        event: 비정기 계정 (배당, 자사주 등) — 부분 합산 허용.
        regular: 매 분기 발생 — 4분기 strict 합산.
        """
        events = self._eventAccounts()
        if key in events:
            return {"account": key, "flowType": "event"}
        return {"account": key, "flowType": "regular"}

    def isEvent(self, key: str) -> bool:
        """이벤트성 계정인지 판별."""
        return key in self._eventAccounts()

    def stats(self) -> MapperStats:
        events = self._eventAccounts()
        return MapperStats(
            name=self.name,
            totalEntries=len(events),
            mappedEntries=len(events),
            coverage=1.0,
            lastUpdated="",
        )

    def allKeys(self) -> list[str]:
        return sorted(self._eventAccounts())

    def eventAccounts(self) -> list[str]:
        """이벤트성 계정 목록."""
        return sorted(self._eventAccounts())
