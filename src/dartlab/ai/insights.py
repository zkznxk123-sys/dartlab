"""Compatibility surface for historical insight helpers."""

from __future__ import annotations


def pastInsight(*_args, **_kwargs):
    return {"ok": False, "error": "pastInsight is not yet connected to Ask Workbench Kernel"}


def sectorInsights(*_args, **_kwargs):
    return {"ok": False, "error": "sectorInsights is not yet connected to Ask Workbench Kernel"}
