"""dataAudit — sync / prebuild 단계 data lineage 추적 (T7-2).

데이터 거버넌스 KPI 의 핵심: *어떤 데이터가 언제 어느 source 에서 다운로드됐는지*
추적 가능한 audit trail. HF dataset version + sync workflow 진입 시점에 자동 호출.

저장 위치: ``data/_lineage/{date}.jsonl`` (gitignored, 로컬 디버그용).
HF dataset metadata 동기화는 후속 (T7-5 와 통합).

API:
    recordLineage(source, version, downloadedAt, hash) -> Path  # 단일 항목
    appendLineage(record) -> Path  # dict 형식
    readLineage(since, source) -> list[dict]

Example::

    from dartlab.core.dataAudit import recordLineage
    recordLineage(
        source="DART OpenAPI list",
        version="2026-05-23",
        downloadedAt="2026-05-23T17:00:00Z",
        recordHash="sha256:abc123...",
    )

스키마 (jsonl 한 줄):
    {
        "recordedAt": ISO,
        "source": str,
        "version": str,
        "downloadedAt": ISO,
        "recordHash": str,
        "rowCount": int (optional),
        "extra": dict (optional)
    }
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


def _defaultLineageDir() -> Path:
    """기본 lineage 저장 디렉터리.

    ``DARTLAB_LINEAGE_DIR`` env override 가능. 기본 ``data/_lineage/`` (cwd 기준).
    """
    custom = os.getenv("DARTLAB_LINEAGE_DIR")
    if custom:
        return Path(custom)
    return Path.cwd() / "data" / "_lineage"


def _todayFile(baseDir: Path | None = None) -> Path:
    """오늘 날짜 jsonl 파일 경로."""
    baseDir = baseDir or _defaultLineageDir()
    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    return baseDir / f"{today}.jsonl"


def appendLineage(record: dict[str, Any], *, baseDir: Path | None = None) -> Path:
    """단일 lineage 항목을 오늘자 jsonl 에 append.

    Args:
        record: lineage dict (source / version / downloadedAt 등).
        baseDir: 저장 root override (테스트용).
    Returns:
        쓰여진 jsonl 파일 경로.
    """
    record = {"recordedAt": dt.datetime.now(dt.UTC).isoformat(), **record}
    filePath = _todayFile(baseDir)
    filePath.parent.mkdir(parents=True, exist_ok=True)
    with filePath.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return filePath


def recordLineage(
    source: str,
    *,
    version: str = "",
    downloadedAt: str = "",
    recordHash: str = "",
    rowCount: int | None = None,
    extra: dict[str, Any] | None = None,
    baseDir: Path | None = None,
) -> Path:
    """data lineage 단일 항목 기록 — 사용자 친화 wrapper (T10-4).

    Capabilities:
        sync workflow / prebuild 단계 진입 시 *어떤 source 의 어떤 version* 이
        언제 다운로드됐는지 jsonl line append. T7-2 (데이터 거버넌스) 의 단일
        진입점.

    Args:
        source: 데이터 source 식별자 (예: "DART OpenAPI list", "FRED FEDFUNDS").
        version: 데이터 버전 (날짜 또는 semver).
        downloadedAt: ISO datetime. 빈 문자열이면 현재 시각.
        recordHash: sha256 등 무결성 hash.
        rowCount: 행 수 (선택).
        extra: 추가 메타 dict (선택).
        baseDir: 저장 root override (테스트용).

    Returns:
        쓰여진 jsonl 파일 Path (오늘자).

    Example:
        >>> recordLineage(
        ...     source="DART OpenAPI",
        ...     version="2026-05-23",
        ...     downloadedAt="2026-05-23T17:00:00Z",
        ...     recordHash="sha256:abc",
        ...     rowCount=4123,
        ... )

    Guide:
        sync workflow 안 `.github/scripts/sync/*.py` 의 `main()` 진입 시점에
        호출. prebuild 는 본 함수 호출 금지 (offline guard 정합).

    SeeAlso:
        appendLineage: dict 직접 append.
        readLineage: 조회.
        dataDriftCheck (T7-5): drift 검출.

    Requires:
        data/_lineage/ 쓰기 권한. DARTLAB_LINEAGE_DIR env override 가능.

    AIContext:
        T7-2 (데이터 거버넌스 KPI) 가중 25 percent 의 핵심 신호. metrics workflow
        T1-2 가 시계열로 수집.

    Raises:
        OSError: 디스크 쓰기 실패.
    """
    record: dict[str, Any] = {
        "source": source,
        "version": version,
        "downloadedAt": downloadedAt or dt.datetime.now(dt.UTC).isoformat(),
        "recordHash": recordHash,
    }
    if rowCount is not None:
        record["rowCount"] = rowCount
    if extra:
        record["extra"] = dict(extra)
    return appendLineage(record, baseDir=baseDir)


def readLineage(
    *,
    sinceDays: int = 30,
    source: str | None = None,
    baseDir: Path | None = None,
) -> list[dict[str, Any]]:
    """저장된 lineage 조회 — 최근 N 일 + source 필터 옵션.

    Args:
        sinceDays: rolling window 일 수.
        source: 특정 source 만 (None 이면 전체).
        baseDir: 저장 root override.
    Returns:
        시간 순서 (recordedAt asc) 정렬된 dict 리스트.
    """
    baseDir = baseDir or _defaultLineageDir()
    if not baseDir.is_dir():
        return []
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=sinceDays)
    records: list[dict[str, Any]] = []
    for jsonlFile in sorted(baseDir.glob("*.jsonl")):
        try:
            with jsonlFile.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    try:
                        recorded = dt.datetime.fromisoformat(rec["recordedAt"].replace("Z", "+00:00"))
                    except (KeyError, ValueError):
                        continue
                    if recorded < cutoff:
                        continue
                    if source and rec.get("source") != source:
                        continue
                    records.append(rec)
        except OSError:
            continue
    records.sort(key=lambda r: r.get("recordedAt", ""))
    return records


__all__ = ["appendLineage", "recordLineage", "readLineage"]
