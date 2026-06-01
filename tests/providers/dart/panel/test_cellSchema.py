"""panel cellSchema mirror — 셀 artifact 14-col 계약 + pivot index (데이터 0).

``cellSchema.py`` 의 ``CELL_SCHEMA``/``CELL_PIVOT_INDEX``. 메인 PANEL_SCHEMA(14-col blob)와
별개 평행 계약임을 검증 (label 은 정체성 아님 — pivot index 제외).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_cell_schema_columns() -> None:
    """CELL_SCHEMA = 14-col, ACONTEXT 분해 컬럼(ctxYear/ctxFlow/ctxQuarter/ctxMode) 포함."""
    from dartlab.providers.dart.panel.cellSchema import CELL_SCHEMA

    assert len(CELL_SCHEMA) == 14
    for col in ("acode", "ctxYear", "ctxFlow", "ctxQuarter", "ctxMode", "axisPath", "valueRaw", "label"):
        assert col in CELL_SCHEMA
    assert CELL_SCHEMA["ctxYear"] == pl.Int32
    assert CELL_SCHEMA["valueRaw"] == pl.Utf8  # 불변 원본 (숫자화 안 함)


def test_cell_pivot_index_excludes_label() -> None:
    """pivot index = acode@axisPath 정체성 — label 제외(주석번호 변동으로 정체성 아님)."""
    from dartlab.providers.dart.panel.cellSchema import CELL_PIVOT_INDEX

    assert CELL_PIVOT_INDEX == ["statement", "acode", "axisPath", "scope"]
    assert "label" not in CELL_PIVOT_INDEX


def test_cell_schema_constructs_dataframe() -> None:
    """CELL_SCHEMA 로 빈 DataFrame 생성 가능 (계약 유효성)."""
    from dartlab.providers.dart.panel.cellSchema import CELL_SCHEMA

    df = pl.DataFrame(schema=CELL_SCHEMA)
    assert df.height == 0
    assert list(df.columns) == list(CELL_SCHEMA.keys())
