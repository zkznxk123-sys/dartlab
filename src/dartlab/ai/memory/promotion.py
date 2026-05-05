"""Status 승격 후보 추출.

unverified → observed: 운영자 confirm 필수 (자동 승격 안 함).
observed → auditP: 통계 + audit 도구 통과 시 자동 시그널.
auditP → official: audit + 운영자 sign-off (CLI).

본 모듈은 '시그널 + 후보 목록' 만 제공. 실제 status frontmatter 갱신은 별도 CLI 가 수행.
"""

from __future__ import annotations

from dataclasses import dataclass

from .stats import allStats

# 임계값 — observed 진입 (운영자 confirm 대상)
_OBSERVED_MIN_USAGE = 5
_OBSERVED_MIN_SUCCESS_RATE = 0.7

# 임계값 — auditP 자동 진입
_AUDITP_MIN_USAGE = 20
_AUDITP_MIN_SUCCESS_RATE = 0.85
_AUDITP_MIN_VALUE_REFS = 1.0


@dataclass
class PromotionCandidate:
    skillId: str
    fromStatus: str
    toStatus: str
    reason: str
    requiresConfirm: bool


def recordSkillUsage(skillId: str, *, ok: bool, valueRefs: int = 0) -> None:
    """편의 wrapper — stats.recordOutcome 호출."""
    from .stats import recordOutcome

    recordOutcome(skillId, ok=ok, valueRefs=valueRefs)


def promotionCandidates(currentStatuses: dict[str, str]) -> list[PromotionCandidate]:
    """skillId → 현재 status 매핑을 받아 승격 후보 반환.

    currentStatuses 는 호출자가 spec frontmatter 에서 추출.
    """
    candidates: list[PromotionCandidate] = []
    stats_map = allStats()

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
