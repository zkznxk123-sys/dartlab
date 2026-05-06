"""streaming 응답 빌더 NaN/Inf sanitize."""

from __future__ import annotations

import math

import pytest

from dartlab.server.streaming import _sanitizeNanInf


@pytest.mark.unit
def test_sanitize_nan_to_none() -> None:
    assert _sanitizeNanInf({"v": float("nan")}) == {"v": None}


@pytest.mark.unit
def test_sanitize_inf_to_none() -> None:
    assert _sanitizeNanInf({"v": float("inf")}) == {"v": None}
    assert _sanitizeNanInf({"v": float("-inf")}) == {"v": None}


@pytest.mark.unit
def test_sanitize_preserves_finite() -> None:
    obj = {"v": 1.5, "n": 0, "s": "ok"}
    assert _sanitizeNanInf(obj) == obj


@pytest.mark.unit
def test_sanitize_recursive_dict_list() -> None:
    obj = {
        "refs": [
            {"id": "v1", "payload": {"value": float("nan"), "name": "자산총계"}},
            {"id": "v2", "payload": {"value": 100, "ratio": math.inf}},
        ],
        "verification": {"ok": True, "stat": float("nan")},
    }
    cleaned = _sanitizeNanInf(obj)
    assert cleaned["refs"][0]["payload"]["value"] is None
    assert cleaned["refs"][0]["payload"]["name"] == "자산총계"
    assert cleaned["refs"][1]["payload"]["value"] == 100
    assert cleaned["refs"][1]["payload"]["ratio"] is None
    assert cleaned["verification"]["stat"] is None
