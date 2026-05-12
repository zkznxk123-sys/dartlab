from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path

import polars as pl

_ARTIFACT_PACKAGE = "dartlab.providers.edgar.docs.sections.artifactData"


@contextmanager
def packagedArtifactPath(name: str) -> Iterator[Path]:
    """패키지 내 artifact 파일 경로를 yield 하는 context manager.

    Args:
        name: artifact 파일명 (예: ``"canonicalRows.parquet"``).

    Yields:
        실제 Path (zip 추출 후 임시 경로일 수 있음).

    Raises:
        FileNotFoundError: 패키지 내 부재.

    Example:
        >>> with packagedArtifactPath("canonicalRows.parquet") as p:
        ...     df = pl.read_parquet(p)

    Returns:
        <TODO: return desc> (Iterator[Path])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
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
    ref = files(_ARTIFACT_PACKAGE) / name
    with as_file(ref) as path:
        yield path


def _outputDir() -> Path:
    return Path(__file__).resolve().parents[6] / "experiments" / "057_edgarSectionMap" / "output"


def loadCanonicalRows() -> pl.DataFrame | None:
    """canonical sections rows (packaged artifact) 를 DataFrame 으로 로드.

    Returns:
        canonical rows DataFrame 또는 None (artifact 부재).

    Raises:
        없음.

    Example:
        >>> loadCanonicalRows()

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
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
        with packagedArtifactPath("canonicalRows.parquet") as path:
            return pl.read_parquet(path)
    except FileNotFoundError:
        path = _outputDir() / "canonicalRows.parquet"
        if not path.exists():
            return None
        return pl.read_parquet(path)


def loadCoverageSnapshot() -> dict[str, object] | None:
    """mapping coverage snapshot JSON 로드.

    Returns:
        coverage dict 또는 None.

    Raises:
        없음.

    Example:
        >>> loadCoverageSnapshot()

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
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
        ref = files(_ARTIFACT_PACKAGE) / "mappingCoverage.latest.json"
        return json.loads(ref.read_text(encoding="utf-8"))
    except FileNotFoundError:
        path = _outputDir() / "mappingCoverage.latest.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


def loadTopicDrafts() -> dict[str, object] | None:
    """form 별 topic draft 정의 JSON 로드.

    Returns:
        topic drafts dict 또는 None.

    Raises:
        없음.

    Example:
        >>> loadTopicDrafts()

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - contextlib
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
        ref = files(_ARTIFACT_PACKAGE) / "formTopicDrafts.json"
        return json.loads(ref.read_text(encoding="utf-8"))
    except FileNotFoundError:
        path = _outputDir() / "formTopicDrafts.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
