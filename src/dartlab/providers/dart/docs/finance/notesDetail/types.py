"""주석 세부항목 타입 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

# NOTES_KEYWORDS 단일 진실의 원천: core/mappers/notesMapper.py
from dartlab.core.mappers.notesMapper import NOTES_KEYWORDS  # noqa: F401


@dataclass
class NotesItem:
    """주석 테이블의 한 행."""

    name: str
    values: list[str]


@dataclass
class NotesPeriod:
    """주석 테이블의 한 기간 블록."""

    pattern: str
    period: str
    headers: list[str]
    items: list[NotesItem]


@dataclass
class NotesDetailResult:
    """주석 세부항목 분석 결과."""

    corpName: str | None
    keyword: str
    nYears: int = 0
    unit: float = 1.0
    tables: dict[str, list[NotesPeriod]] | None = None
    tableDf: pl.DataFrame | None = None
