"""패키지에 포함된 sections 학습 산출물 로더."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path

import polars as pl

_PROFILE_PACKAGE = "dartlab.providers.dart.docs.sections.profileData"


@contextmanager
def packagedArtifactPath(name: str) -> Iterator[Path]:
    """패키지 리소스를 filesystem path로 노출.

    Args:
        name: 인자.

    Raises:
        없음.

    Example:
        >>> packagedArtifactPath(...)

    Returns:
        <TODO: return desc> (Iterator[Path])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
        - functools
        - importlib
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    ref = files(_PROFILE_PACKAGE) / name
    with as_file(ref) as path:
        yield path


_KNOWN_CHAPTERS: frozenset[str] = frozenset({"chapterII"})


@lru_cache(maxsize=4)
def loadProjectionRules(chapter: str) -> dict[str, list[str]]:
    """장(chapter)별 섹션 투영 규칙 JSON을 로드한다.

    2026-04-19 사고 class 방어: 알려진 chapter 의 JSON 이 누락되면 loud-fail.
    미등록 chapter 이름에 대해서는 기존처럼 빈 dict 리턴 (유효한 "규칙 없음" 상태).

    Args:
        chapter: 인자.

    Raises:
        없음.

    Example:
        >>> loadProjectionRules(...)

    Returns:
        <TODO: return desc> (dict[str, list[str]])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
        - functools
        - importlib
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    filename = f"projectionRules.{chapter}.json"
    try:
        ref = files(_PROFILE_PACKAGE) / filename
        return json.loads(ref.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        if chapter in _KNOWN_CHAPTERS:
            raise FileNotFoundError(
                f"필수 번들 리소스 누락: {_PROFILE_PACKAGE}/{filename} ({e})\n"
                f"  → pip install -U --force-reinstall dartlab"
            ) from e
        return {}


@lru_cache(maxsize=1)
def loadSectionProfileTable() -> pl.DataFrame | None:
    """패키지에 포함된 sectionProfileTable parquet을 DataFrame으로 로드한다.

    필수 번들 리소스 — 파일 누락은 packaging 사고로 간주해 loud-fail.
    Parquet 로드는 비용 큼 — 호출당 재로드 방지를 위해 @lru_cache(1).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> loadSectionProfileTable(...)

    Returns:
        <TODO: return desc> (pl.DataFrame | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
        - functools
        - importlib
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    try:
        with packagedArtifactPath("sectionProfileTable.parquet") as path:
            from dartlab.frame.dataLoader import readParquetSafe

            return readParquetSafe(path)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: {_PROFILE_PACKAGE}/sectionProfileTable.parquet ({e})\n"
            f"  → pip install -U --force-reinstall dartlab"
        ) from e
