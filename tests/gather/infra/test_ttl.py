"""dartlab.gather.infra.ttl mirror 슬롯 + env override 검증 (G+ P-Q4).

룰 7 (src↔tests 1:1 mirror) 만족 + 환경변수 동작 확인.
"""

from __future__ import annotations

import importlib
import os

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.infra.ttl`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.infra.ttl")


def test_default_ttl_values() -> None:
    """env 미설정 시 default 값 동작."""
    from dartlab.gather.infra.ttl import (
        TTL_DEFAULT,
        TTL_FLOW,
        TTL_LISTING,
        TTL_MACRO,
        TTL_PRICE,
        TTL_SECTOR,
    )

    assert TTL_PRICE == 300  # 5분
    assert TTL_FLOW == 3600  # 1시간
    assert TTL_MACRO == 6 * 3600  # 6시간
    assert TTL_SECTOR == 24 * 3600  # 24시간
    assert TTL_LISTING == 86400  # 24시간 (listing)
    assert TTL_DEFAULT == 3600  # 1시간


def test_envInt_override_valid() -> None:
    """DARTLAB_TTL_PRICE=60 같은 명시적 env 값이 default 를 override 한다."""
    from dartlab.gather.infra.ttl import _envInt

    os.environ["DARTLAB_TTL_TEST_VALID"] = "60"
    try:
        assert _envInt("DARTLAB_TTL_TEST_VALID", 300) == 60
    finally:
        del os.environ["DARTLAB_TTL_TEST_VALID"]


def test_envInt_override_zero() -> None:
    """DARTLAB_TTL_*=0 — 캐시 즉시 expire 의도."""
    from dartlab.gather.infra.ttl import _envInt

    os.environ["DARTLAB_TTL_TEST_ZERO"] = "0"
    try:
        assert _envInt("DARTLAB_TTL_TEST_ZERO", 300) == 0
    finally:
        del os.environ["DARTLAB_TTL_TEST_ZERO"]


def test_envInt_invalid_falls_back() -> None:
    """비정수 env 값은 silent default fallback."""
    from dartlab.gather.infra.ttl import _envInt

    os.environ["DARTLAB_TTL_TEST_INVALID"] = "abc"
    try:
        assert _envInt("DARTLAB_TTL_TEST_INVALID", 300) == 300
    finally:
        del os.environ["DARTLAB_TTL_TEST_INVALID"]


def test_envInt_missing_returns_default() -> None:
    """env 미설정 시 default."""
    from dartlab.gather.infra.ttl import _envInt

    if "DARTLAB_TTL_TEST_MISSING" in os.environ:
        del os.environ["DARTLAB_TTL_TEST_MISSING"]
    assert _envInt("DARTLAB_TTL_TEST_MISSING", 999) == 999


def test_listing_ttl_consumed_by_3_modules() -> None:
    """krx/listing/{registry,dartList,krxList}.py 가 TTL_LISTING 사용 — SSOT 정합."""
    from dartlab.gather.krx.listing import dartList, krxList, registry

    assert registry.CACHE_TTL == 86400
    assert dartList.CACHE_TTL == 86400
    assert krxList.CACHE_TTL == 86400
