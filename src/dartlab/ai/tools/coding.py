"""Compatibility wrapper for the coding runtime."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[2] / "ai_backup" / "tools" / "coding.py"
_SPEC = importlib.util.spec_from_file_location("_dartlab_ai_backup_tools_coding", _SOURCE)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"coding runtime source를 불러올 수 없습니다: {_SOURCE}")

_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

for _name, _value in _MODULE.__dict__.items():
    if _name not in {"__builtins__", "__cached__", "__file__", "__loader__", "__name__", "__package__", "__spec__"}:
        globals()[_name] = _value

__all__ = [name for name in globals() if not name.startswith("__")]
