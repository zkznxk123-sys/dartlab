"""skillId 별 usageCount / successRate / avgValueRefs 집계.

stat 저장: ~/.dartlab/ai_memory/skill_stats.jsonl (append-only).
조회: getSkillStats(skillId) — 누적 통계 반환.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_STATS_PATH = Path.home() / ".dartlab" / "ai_memory" / "skill_stats.jsonl"


@dataclass
class SkillStats:
    skillId: str
    usageCount: int = 0
    successCount: int = 0
    valueRefSum: int = 0

    @property
    def successRate(self) -> float:
        return self.successCount / self.usageCount if self.usageCount else 0.0

    @property
    def avgValueRefs(self) -> float:
        return self.valueRefSum / self.usageCount if self.usageCount else 0.0


def _ensureDir() -> None:
    _STATS_PATH.parent.mkdir(parents=True, exist_ok=True)


def recordOutcome(skillId: str, *, ok: bool, valueRefs: int = 0) -> None:
    if not skillId:
        return
    _ensureDir()
    row = {"skillId": skillId, "ok": bool(ok), "valueRefs": int(valueRefs)}
    with _STATS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def getSkillStats(skillId: str) -> SkillStats:
    stats = SkillStats(skillId=skillId)
    if not _STATS_PATH.exists():
        return stats
    with _STATS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("skillId") != skillId:
                continue
            stats.usageCount += 1
            if row.get("ok"):
                stats.successCount += 1
            stats.valueRefSum += int(row.get("valueRefs") or 0)
    return stats


def allStats() -> dict[str, SkillStats]:
    result: dict[str, SkillStats] = {}
    if not _STATS_PATH.exists():
        return result
    with _STATS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = row.get("skillId") or ""
            if not sid:
                continue
            stats = result.setdefault(sid, SkillStats(skillId=sid))
            stats.usageCount += 1
            if row.get("ok"):
                stats.successCount += 1
            stats.valueRefSum += int(row.get("valueRefs") or 0)
    return result


def setStatsPathForTesting(path: Path) -> None:
    """테스트 전용 — stats 경로 redirect."""
    global _STATS_PATH
    _STATS_PATH = path
