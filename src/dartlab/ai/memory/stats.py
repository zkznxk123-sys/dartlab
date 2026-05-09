"""skillId 별 usageCount / successRate / avgValueRefs 집계.

저장: ~/.dartlab/ai_memory/skill_stats.jsonl (append-only). 또는 환경변수
DARTLAB_SKILL_STATS_PATH 로 redirect.
조회: getSkillStats(skillId) / loadStats() — 누적 통계.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_STATS_PATH = Path.home() / ".dartlab" / "ai_memory" / "skill_stats.jsonl"


@dataclass
class SkillStats:
    skillId: str
    usageCount: int = 0
    successCount: int = 0
    valueRefSum: int = 0
    lastUsedTs: str = ""

    @property
    def successRate(self) -> float:
        return self.successCount / self.usageCount if self.usageCount else 0.0

    @property
    def avgValueRefs(self) -> float:
        return self.valueRefSum / self.usageCount if self.usageCount else 0.0

    @property
    def valueRefCount(self) -> int:
        """alias — 외부 API 가 valueRefCount 명을 사용."""
        return self.valueRefSum


def _resolveStatsPath() -> Path:
    """env var 가 있으면 우선 — 테스트/외부 도구 redirect."""
    env_path = os.environ.get("DARTLAB_SKILL_STATS_PATH")
    if env_path:
        return Path(env_path)
    return _STATS_PATH


def _ensureDir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _accumulate(stats: SkillStats, row: dict) -> None:
    stats.usageCount += 1
    if row.get("ok"):
        stats.successCount += 1
    stats.valueRefSum += int(row.get("valueRefs") or 0)
    ts = row.get("ts")
    if ts and (not stats.lastUsedTs or str(ts) > stats.lastUsedTs):
        stats.lastUsedTs = str(ts)


def recordOutcome(skillId: str, *, ok: bool, valueRefs: int = 0) -> SkillStats:
    """outcome 1 건 append + 누적 통계 반환."""
    if not skillId:
        return SkillStats(skillId="")
    path = _resolveStatsPath()
    _ensureDir(path)
    ts = datetime.now(timezone.utc).isoformat()
    row = {"skillId": skillId, "ok": bool(ok), "valueRefs": int(valueRefs), "ts": ts}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return getSkillStats(skillId)


def getSkillStats(skillId: str) -> SkillStats:
    stats = SkillStats(skillId=skillId)
    path = _resolveStatsPath()
    if not path.exists():
        return stats
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("skillId") != skillId:
                continue
            _accumulate(stats, row)
    return stats


def allStats() -> dict[str, SkillStats]:
    result: dict[str, SkillStats] = {}
    path = _resolveStatsPath()
    if not path.exists():
        return result
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = row.get("skillId") or ""
            if not sid:
                continue
            stats = result.setdefault(sid, SkillStats(skillId=sid))
            _accumulate(stats, row)
    return result


def loadStats() -> dict[str, SkillStats]:
    """allStats alias — 외부 API 호환."""
    return allStats()


def setStatsPathForTesting(path: Path) -> None:
    """레거시 호환 — env var 권장."""
    global _STATS_PATH
    _STATS_PATH = path


__all__ = [
    "SkillStats",
    "allStats",
    "getSkillStats",
    "loadStats",
    "recordOutcome",
    "setStatsPathForTesting",
]
