"""관세청 무역통계 엔진 타입 정의 (FRED/ECOS 타입 미러)."""

from __future__ import annotations

from dataclasses import dataclass

# ── 예외 ──


class CustomsError(Exception):
    """관세청 무역통계 API 기본 예외."""


class RateLimitError(CustomsError):
    """API 요청 한도 초과."""


# ── 데이터 타입 ──


@dataclass(frozen=True)
class CatalogEntry:
    """관세청 품목(HS) 카탈로그 정의 — FRED CatalogEntry 와 동일 필드.

    id 는 HS 코드(2/4/6자리 문자열), label·group·frequency·unit·description 은
    macro 빌드 매니페스트가 그대로 소비한다 (소스 간 균질).
    """

    id: str  # HS 코드 (예 "8542")
    label: str
    group: str
    frequency: str  # "Monthly"
    unit: str  # "USD"
    description: str
