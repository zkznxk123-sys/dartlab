"""EDGAR 벌크 다운로드의 TTL/ETag 관리.

`data/edgar/_bulk/{tag}.freshness` 사이드카 파일로 각 벌크의 최근 체크 시각과
원격 ETag 저장. 같은 경로의 `{tag}.etag` 에 ETag만 별도 저장 (재다운로드 판정).

- `companyfacts.zip` → tag="companyfacts", TTL 24h
- `{Y}q{Q}.zip` → tag="quarterly_{Y}Q{Q}", TTL 영구 (분기 벌크는 한 번 다운로드 후 교체 없음)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass
class BulkFreshness:
    """벌크 파일 freshness 상태 스냅샷."""

    tag: str
    exists: bool
    etag: str | None
    lastChecked: datetime | None
    ageHours: float | None


def _bulkDir() -> Path:
    from dartlab import config as _cfg

    d = Path(_cfg.dataDir) / "edgar" / "_bulk"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _freshnessPath(tag: str) -> Path:
    return _bulkDir() / f"{tag}.freshness"


def _etagPath(tag: str) -> Path:
    return _bulkDir() / f"{tag}.etag"


def touchBulkFreshness(tag: str, *, etag: str | None = None) -> None:
    """다운로드 성공 직후 호출 — 현재 시각과 ETag 기록."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _freshnessPath(tag).write_text(now, encoding="utf-8")
    if etag:
        _etagPath(tag).write_text(etag, encoding="utf-8")


def readSavedEtag(tag: str) -> str | None:
    """저장된 ETag 읽기. 없으면 None."""
    p = _etagPath(tag)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def inspectBulkFreshness(tag: str) -> BulkFreshness:
    """freshness 스냅샷 반환."""
    p = _freshnessPath(tag)
    etag = readSavedEtag(tag)
    if not p.exists():
        return BulkFreshness(tag=tag, exists=False, etag=etag, lastChecked=None, ageHours=None)
    try:
        text = p.read_text(encoding="utf-8").strip()
        checked = datetime.fromisoformat(text)
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - checked).total_seconds() / 3600.0
        return BulkFreshness(tag=tag, exists=True, etag=etag, lastChecked=checked, ageHours=age)
    except (ValueError, OSError) as exc:
        _log.warning("freshness 파일 %s 파싱 실패: %s", p, exc)
        return BulkFreshness(tag=tag, exists=False, etag=etag, lastChecked=None, ageHours=None)


def isBulkFresh(tag: str, *, ttlHours: int = 24) -> bool:
    """TTL 내에 마지막 체크 기록이 있고 freshness 파일이 존재하면 True."""
    snap = inspectBulkFreshness(tag)
    if not snap.exists or snap.lastChecked is None:
        return False
    if snap.ageHours is None:
        return False
    return snap.ageHours < float(ttlHours)


def invalidateBulkFreshness(tag: str) -> None:
    """freshness + etag 파일 제거 (강제 재다운로드)."""
    for p in (_freshnessPath(tag), _etagPath(tag)):
        try:
            p.unlink(missing_ok=True)
        except OSError as exc:
            _log.warning("freshness 파일 %s 제거 실패: %s", p, exc)


__all__ = [
    "BulkFreshness",
    "inspectBulkFreshness",
    "invalidateBulkFreshness",
    "isBulkFresh",
    "readSavedEtag",
    "touchBulkFreshness",
]
