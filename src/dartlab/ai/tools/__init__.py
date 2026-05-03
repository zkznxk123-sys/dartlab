"""Compatibility exports for tool runtimes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_BACKUP_TOOLS = Path(__file__).resolve().parents[2] / "ai_backup" / "tools"
if _BACKUP_TOOLS.exists():
    __path__.append(str(_BACKUP_TOOLS))

_BACKUP_INIT = _BACKUP_TOOLS / "__init__.py"
if _BACKUP_INIT.exists():
    _spec = importlib.util.spec_from_file_location("_dartlab_ai_backup_tools", _BACKUP_INIT)
    if _spec is not None and _spec.loader is not None:
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_spec.name] = _module
        _spec.loader.exec_module(_module)
        for _name, _value in _module.__dict__.items():
            if _name not in {
                "__builtins__",
                "__cached__",
                "__file__",
                "__loader__",
                "__name__",
                "__package__",
                "__path__",
                "__spec__",
            }:
                globals()[_name] = _value

from . import coding as coding

__all__ = [name for name in globals() if not name.startswith("__")]
