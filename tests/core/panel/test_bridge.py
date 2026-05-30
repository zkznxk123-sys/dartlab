"""core/panel bridge (S3) mirror — disclosureKey 어휘 load/seed/write (데이터 경량).

``core/panel/bridge.py`` 의 ``loadBridge``(lru_cache read)/``seedBridgeTier1``/``writeBridge``.
loadBridge 는 7-col 스키마 보장(파일 없으면 빈 스키마). seed/write 는 부작용(parquet)이라
mirror 는 호출 안 하고 공개표면 존재만 확인(파괴적 write 회피).
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.core.panel import BRIDGE_SCHEMA, loadBridge, seedBridgeTier1, writeBridge

pytestmark = pytest.mark.unit


def test_load_bridge_returns_schema_columns() -> None:
    """loadBridge → BRIDGE_SCHEMA 7-col (파일 없으면 빈 스키마)."""
    df = loadBridge()
    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) == set(BRIDGE_SCHEMA.keys())


def test_seed_and_write_public_callables() -> None:
    """seedBridgeTier1 / writeBridge 공개표면 존재 (파괴적 write 미호출)."""
    assert callable(seedBridgeTier1)
    assert callable(writeBridge)
