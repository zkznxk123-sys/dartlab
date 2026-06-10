"""router 모듈 mirror smoke — 모델 빌드/로드/예측/canon 의 graceful 계약."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.search import router

    assert router is not None


def test_build_router_model_shape() -> None:
    """buildRouterModel — v/events/route/canon 구조."""
    from dartlab.providers.dart.search.router import ROUTER_VERSION, buildRouterModel

    m = buildRouterModel({"dividend": {"router": ["배당 얼마 줘?"], "canon": ["배당금"]}})
    assert m["v"] == ROUTER_VERSION
    assert m["events"]["dividend"]["canon"] == ["배당금"]
    assert m["events"]["dividend"]["route"]


def test_load_router_model_graceful(tmp_path: Path) -> None:
    """부재·파손·버전 불일치 → None (크래시 없음)."""
    from dartlab.providers.dart.search.router import loadRouterModel

    assert loadRouterModel(tmp_path) is None  # 부재
    (tmp_path / "router.json").write_text("{broken", encoding="utf-8")
    assert loadRouterModel(tmp_path) is None  # 파손
    (tmp_path / "router.json").write_text(json.dumps({"v": 99, "events": {}}), encoding="utf-8")
    assert loadRouterModel(tmp_path) is None  # 버전 불일치


def test_route_canon_none_model() -> None:
    """모델 None → 빈 리스트 (always-safe)."""
    from dartlab.providers.dart.search.router import routeCanon

    assert routeCanon(None, "배당") == []
