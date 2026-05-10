"""Status 승격 후보 추출.

unverified → observed: 운영자 confirm 필수 (자동 승격 안 함).
observed → auditP: 통계 + audit 도구 통과 시 자동 시그널.
auditP → official: audit + 운영자 sign-off (CLI).

본 모듈은 '시그널 + 후보 목록' 만 제공. 실제 status frontmatter 갱신은 별도 CLI 가 수행.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .stats import SkillStats, allStats, recordOutcome

# 임계값 — observed 진입 (운영자 confirm 대상)
_OBSERVED_MIN_USAGE = 5
_OBSERVED_MIN_SUCCESS_RATE = 0.7

# 임계값 — auditP 자동 진입
_AUDITP_MIN_USAGE = 20
_AUDITP_MIN_SUCCESS_RATE = 0.85
_AUDITP_MIN_VALUE_REFS = 1.0


@dataclass(frozen=True)
class PromotionCandidate:
    """승격 후보 — attribute + dict-like access 둘 다 지원 (호환)."""

    skillId: str
    fromStatus: str
    toStatus: str
    reason: str
    requiresConfirm: bool

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def recordSkillUsage(
    skillId: str,
    *,
    success: bool | None = None,
    ok: bool | None = None,
    valueRefs: int = 0,
) -> SkillStats:
    """편의 wrapper — stats.recordOutcome 호출 + 누적 통계 반환.

    `success` (새) 와 `ok` (옛) 둘 다 허용. 둘 다 미지정 시 False.
    """
    final_ok = success if success is not None else (ok if ok is not None else False)
    return recordOutcome(skillId, ok=bool(final_ok), valueRefs=valueRefs)


def _resolveCurrentStatuses(skillIds: list[str]) -> dict[str, str]:
    """skill 의 현재 status 를 dartlab.skills.getSkill 로 조회.

    skill 이 spec 에 없거나 import 실패 시 unverified 로 가정.
    """
    statuses: dict[str, str] = {}
    try:
        from dartlab.skills import getSkill
    except ImportError:
        return {sid: "unverified" for sid in skillIds}
    for sid in skillIds:
        try:
            spec = getSkill(sid)
            statuses[sid] = getattr(spec, "status", "unverified") or "unverified"
        except Exception:  # noqa: BLE001
            statuses[sid] = "unverified"
    return statuses


def promotionCandidates(currentStatuses: dict[str, str] | None = None) -> list[PromotionCandidate]:
    """승격 후보 반환.

    currentStatuses 미지정 시 dartlab.skills.getSkill 로 자동 조회.
    반환된 PromotionCandidate 는 attribute (cand.fromStatus) 와 dict-like
    (cand["fromStatus"]) 두 접근 모두 지원.
    """
    stats_map = allStats()
    if currentStatuses is None:
        currentStatuses = _resolveCurrentStatuses(list(stats_map.keys()))

    candidates: list[PromotionCandidate] = []
    for sid, stats in stats_map.items():
        cur = currentStatuses.get(sid, "unverified")
        if cur == "unverified":
            if stats.usageCount >= _OBSERVED_MIN_USAGE and stats.successRate >= _OBSERVED_MIN_SUCCESS_RATE:
                candidates.append(
                    PromotionCandidate(
                        skillId=sid,
                        fromStatus="unverified",
                        toStatus="observed",
                        reason=f"usage={stats.usageCount} successRate={stats.successRate:.2f}",
                        requiresConfirm=True,
                    )
                )
        elif cur == "observed":
            if (
                stats.usageCount >= _AUDITP_MIN_USAGE
                and stats.successRate >= _AUDITP_MIN_SUCCESS_RATE
                and stats.avgValueRefs >= _AUDITP_MIN_VALUE_REFS
            ):
                candidates.append(
                    PromotionCandidate(
                        skillId=sid,
                        fromStatus="observed",
                        toStatus="auditP",
                        reason=(
                            f"usage={stats.usageCount} successRate={stats.successRate:.2f} "
                            f"avgValueRefs={stats.avgValueRefs:.2f}"
                        ),
                        requiresConfirm=False,
                    )
                )
    return candidates


__all__ = ["PromotionCandidate", "promotionCandidates", "recordSkillUsage"]
