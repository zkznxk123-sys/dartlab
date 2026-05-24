"""자격증명 lifecycle 추적 + 만료 임계 알람 (T2-4).

DART API key (90 일 lifecycle, 사용자 갱신 필요) + OAuth token (자동 refresh
가능) 의 *만료 임계 점검*. 임계 도달 시 logEvent 알람 + INCIDENTS 자동 항목
(T1-3 통합 후속).

API:
    recordIssuance(key, issuedAt, lifetimeDays) -> None
    checkLifecycle(thresholdDays=14) -> list[CredentialAlert]
    daysUntilExpiry(key) -> int | None

저장: `data/_credentials/lifecycle.json` (gitignored, 로컬 추적).

CLAUDE.md `feedback_no_extras_install` 정합 — keyring optional, base 부담 0.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path


def _defaultLifecycleFile() -> Path:
    """기본 lifecycle 저장 경로 — DARTLAB_CREDENTIAL_DIR env override 가능."""
    custom = os.getenv("DARTLAB_CREDENTIAL_DIR")
    if custom:
        return Path(custom) / "lifecycle.json"
    return Path.cwd() / "data" / "_credentials" / "lifecycle.json"


@dataclass
class CredentialAlert:
    """단일 자격증명 만료 임계 알람."""

    key: str
    issuedAt: str
    expiresAt: str
    daysRemaining: int
    severity: str  # "ok" / "warning" / "critical" / "expired"


def _loadLifecycle(path: Path | None = None) -> dict:
    path = path or _defaultLifecycleFile()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _saveLifecycle(data: dict, path: Path | None = None) -> None:
    path = path or _defaultLifecycleFile()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def recordIssuance(
    key: str,
    *,
    issuedAt: str | None = None,
    lifetimeDays: int = 90,
    path: Path | None = None,
) -> None:
    """자격증명 발급 시점 기록.

    Args:
        key: 자격증명 식별자 (예: "DART_API_KEY").
        issuedAt: ISO datetime. None 이면 현재 시각.
        lifetimeDays: 발급 후 만료까지 일 수. DART API 기본 90.
        path: lifecycle 파일 override (테스트용).
    """
    issued = issuedAt or dt.datetime.now(dt.UTC).isoformat()
    issuedDt = dt.datetime.fromisoformat(issued.replace("Z", "+00:00"))
    expires = (issuedDt + dt.timedelta(days=lifetimeDays)).isoformat()

    data = _loadLifecycle(path)
    data[key] = {
        "issuedAt": issued,
        "expiresAt": expires,
        "lifetimeDays": lifetimeDays,
        "recordedAt": dt.datetime.now(dt.UTC).isoformat(),
    }
    _saveLifecycle(data, path)


def daysUntilExpiry(key: str, *, path: Path | None = None) -> int | None:
    """key 의 만료까지 남은 일 수 — 기록 없으면 None."""
    data = _loadLifecycle(path)
    entry = data.get(key)
    if not entry:
        return None
    expires = dt.datetime.fromisoformat(entry["expiresAt"].replace("Z", "+00:00"))
    delta = expires - dt.datetime.now(dt.UTC)
    return int(delta.total_seconds() / 86400)


def checkLifecycle(*, thresholdDays: int = 14, path: Path | None = None) -> list[CredentialAlert]:
    """모든 등록 자격증명의 만료 임계 점검.

    Args:
        thresholdDays: warning 임계 (기본 14일).
    Returns:
        severity 가 ok 아닌 CredentialAlert 리스트.
    """
    data = _loadLifecycle(path)
    alerts: list[CredentialAlert] = []
    for key, entry in data.items():
        try:
            expires = dt.datetime.fromisoformat(entry["expiresAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        days = int((expires - dt.datetime.now(dt.UTC)).total_seconds() / 86400)
        if days < 0:
            severity = "expired"
        elif days < 3:
            severity = "critical"
        elif days < thresholdDays:
            severity = "warning"
        else:
            severity = "ok"

        if severity != "ok":
            alerts.append(
                CredentialAlert(
                    key=key,
                    issuedAt=entry.get("issuedAt", ""),
                    expiresAt=entry.get("expiresAt", ""),
                    daysRemaining=days,
                    severity=severity,
                )
            )
    return alerts


__all__ = ["CredentialAlert", "recordIssuance", "daysUntilExpiry", "checkLifecycle"]
