"""_registry 의 dataclass 타입 — _CalcEntry / _AxisEntry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class _CalcEntry:
    """개별 calc* 함수 메타."""

    fn: str
    module: str
    blockKey: str
    label: str


@dataclass(frozen=True)
class _AxisEntry:
    """분석 축 메타."""

    section: str
    partId: str
    description: str
    example: str
    calcs: tuple[_CalcEntry, ...] = field(default_factory=tuple)
