"""MapperEngine — dartlab 매퍼 통합 엔진.

기존 매퍼 데이터(accountMappings, TOPIC_KEYWORDS, SNAKEID_ALIASES,
_EVENT_ACCOUNTS)를 읽기 전용으로 래핑하여 통합 인터페이스를 제공한다.

원본 코드를 건드리지 않는다. 매퍼 엔진이 기존 데이터를 참조만 하고,
검증 완료 후 순차적으로 레거시를 교체한다.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MapperStats:
    """매퍼 통계."""

    name: str
    totalEntries: int
    mappedEntries: int
    coverage: float  # 0.0 ~ 1.0
    lastUpdated: str = ""

    def __repr__(self) -> str:
        pct = f"{self.coverage * 100:.1f}%"
        return f"<{self.name}: {self.mappedEntries}/{self.totalEntries} ({pct})>"


class BaseMapper(ABC):
    """모든 매퍼의 공통 인터페이스."""

    @property
    @abstractmethod
    def name(self) -> str:
        """매퍼 이름."""

    @abstractmethod
    def lookup(self, key: str) -> dict | None:
        """키로 매핑 조회. 없으면 None."""

    @abstractmethod
    def stats(self) -> MapperStats:
        """매퍼 통계."""

    def contains(self, key: str) -> bool:
        """키 존재 여부."""
        return self.lookup(key) is not None

    @abstractmethod
    def allKeys(self) -> list[str]:
        """등록된 모든 키."""

    def missing(self, candidates: list[str]) -> list[str]:
        """후보 중 매핑 안 된 항목."""
        return [k for k in candidates if not self.contains(k)]


@dataclass
class MapperSnapshot:
    """분기별 스냅샷 메타."""

    quarter: str  # e.g. "2026Q2"
    mapper: str
    stats: MapperStats
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MapperEngine:
    """매퍼 통합 엔진 — 등록된 매퍼에 통합 접근."""

    def __init__(self) -> None:
        self._mappers: dict[str, BaseMapper] = {}
        self._historyDir: Path | None = None

    def register(self, mapper: BaseMapper) -> None:
        """매퍼 등록."""
        self._mappers[mapper.name] = mapper

    def get(self, name: str) -> BaseMapper | None:
        """이름으로 매퍼 조회."""
        return self._mappers.get(name)

    @property
    def mappers(self) -> dict[str, BaseMapper]:
        """등록된 모든 매퍼."""
        return dict(self._mappers)

    def allStats(self) -> list[MapperStats]:
        """모든 매퍼 통계."""
        return [m.stats() for m in self._mappers.values()]

    def summary(self) -> str:
        """전체 매퍼 요약."""
        lines = ["[MapperEngine]"]
        for s in self.allStats():
            lines.append(f"  {s}")
        return "\n".join(lines)

    # ── 스냅샷 ──

    def setHistoryDir(self, path: Path) -> None:
        """이력 디렉토리 설정."""
        self._historyDir = path

    def snapshot(self, quarter: str) -> list[MapperSnapshot]:
        """분기 스냅샷 저장."""
        if self._historyDir is None:
            return []

        qdir = self._historyDir / quarter
        qdir.mkdir(parents=True, exist_ok=True)

        snapshots = []
        for name, mapper in self._mappers.items():
            s = MapperSnapshot(quarter=quarter, mapper=name, stats=mapper.stats())
            snapshots.append(s)

        # 메타 저장
        meta = {
            "quarter": quarter,
            "timestamp": datetime.now().isoformat(),
            "mappers": {s.mapper: {"coverage": s.stats.coverage, "total": s.stats.totalEntries} for s in snapshots},
        }
        (qdir / "snapshot.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshots

    def diff(self, q1: str, q2: str) -> dict[str, Any]:
        """두 분기 스냅샷 비교."""
        if self._historyDir is None:
            return {}

        f1 = self._historyDir / q1 / "snapshot.json"
        f2 = self._historyDir / q2 / "snapshot.json"
        if not f1.exists() or not f2.exists():
            return {"error": f"snapshot not found: {q1} or {q2}"}

        d1 = json.loads(f1.read_text(encoding="utf-8"))
        d2 = json.loads(f2.read_text(encoding="utf-8"))

        result: dict[str, Any] = {}
        allNames = set(d1.get("mappers", {})) | set(d2.get("mappers", {}))
        for name in sorted(allNames):
            m1 = d1.get("mappers", {}).get(name, {})
            m2 = d2.get("mappers", {}).get(name, {})
            result[name] = {
                "coverage": {"before": m1.get("coverage", 0), "after": m2.get("coverage", 0)},
                "total": {"before": m1.get("total", 0), "after": m2.get("total", 0)},
            }
        return result
