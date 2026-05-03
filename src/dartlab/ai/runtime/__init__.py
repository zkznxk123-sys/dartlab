"""Compatibility runtime helpers for legacy runtime imports."""

from pathlib import Path

_BACKUP_RUNTIME = Path(__file__).resolve().parents[2] / "ai_backup" / "runtime"
if _BACKUP_RUNTIME.exists():
    __path__.append(str(_BACKUP_RUNTIME))
