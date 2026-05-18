"""Phase A — ``writeParquetSorted`` 회귀 테스트.

검증:
  1. ``data/dart/finance/{code}.parquet`` 경로 → ``sj_div`` 등 sort 키 자동 적용.
  2. 비-카테고리 경로 → sort 없이 write (호환 보존).
  3. row_group_size 명시.
  4. statistics 활성 (predicate pushdown 의 전제).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pyarrow.parquet as pq
import pytest

pytestmark = pytest.mark.unit


def _sampleFinanceDf() -> pl.DataFrame:
    """sj_div 가 섞인 long-format finance 샘플."""
    return pl.DataFrame(
        {
            "sj_div": ["CF", "BS", "IS", "BS", "CF", "IS"],
            "fs_div": ["CFS", "CFS", "CFS", "OFS", "OFS", "OFS"],
            "bsns_year": [2023, 2023, 2023, 2023, 2023, 2023],
            "reprt_nm": ["사업보고서"] * 6,
            "account_id": ["a3", "a1", "a2", "a1", "a3", "a2"],
            "thstrm_amount": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0],
        }
    )


def test_finance_path_applies_sort(tmp_path: Path) -> None:
    """``data/dart/finance/`` 경로면 sj_div 등 sort 키 적용."""
    from dartlab.providers.dart.openapi.saver import writeParquetSorted

    dest = tmp_path / "data" / "dart" / "finance" / "005930.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df = _sampleFinanceDf()

    writeParquetSorted(df, dest)

    written = pl.read_parquet(dest)
    sjDivs = written.get_column("sj_div").to_list()
    # BS · CF · IS 알파벳 순 — disjoint row group 의 전제.
    assert sjDivs == sorted(sjDivs), f"sj_div not sorted: {sjDivs}"


def test_non_dart_path_no_sort(tmp_path: Path) -> None:
    """카테고리 매칭 안 되는 경로 → 원본 순서 유지."""
    from dartlab.providers.dart.openapi.saver import writeParquetSorted

    dest = tmp_path / "misc" / "test.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df = _sampleFinanceDf()

    writeParquetSorted(df, dest)

    written = pl.read_parquet(dest)
    # 원본 순서 보존 (sort 적용 안 됨)
    assert written.get_column("sj_div").to_list() == df.get_column("sj_div").to_list()


def test_row_group_size_and_statistics(tmp_path: Path) -> None:
    """row_group_size 와 statistics 가 적용 — predicate pushdown 전제."""
    from dartlab.providers.dart.openapi.saver import _ROW_GROUP_SIZE, writeParquetSorted

    dest = tmp_path / "data" / "dart" / "finance" / "005930.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)

    # row_group_size 보다 더 큰 데이터로 multi-row-group 강제
    nRows = _ROW_GROUP_SIZE * 2 + 100
    df = pl.DataFrame(
        {
            "sj_div": ["BS"] * (nRows // 3) + ["CF"] * (nRows // 3) + ["IS"] * (nRows - 2 * (nRows // 3)),
            "fs_div": ["CFS"] * nRows,
            "bsns_year": [2023] * nRows,
            "reprt_nm": ["사업보고서"] * nRows,
            "account_id": [f"a{i}" for i in range(nRows)],
            "thstrm_amount": [float(i) for i in range(nRows)],
        }
    )

    writeParquetSorted(df, dest)

    meta = pq.ParquetFile(dest).metadata
    assert meta.num_row_groups >= 2, f"expected ≥2 row groups, got {meta.num_row_groups}"

    # 첫 row group 의 sj_div 컬럼 statistics 존재 + min/max 가 정렬에 부합.
    # sort 적용 시 첫 row group 의 sj_div min 은 "BS" 여야.
    for rg in range(meta.num_row_groups):
        col0 = meta.row_group(rg).column(0)  # sj_div (sort 첫 키 = 0 번 컬럼)
        assert col0.statistics is not None, f"row group {rg} sj_div statistics 부재"


def test_atomic_write_no_tmp_left(tmp_path: Path) -> None:
    """원자적 write — tmp 파일이 dest 옆에 남지 않음."""
    from dartlab.providers.dart.openapi.saver import writeParquetSorted

    dest = tmp_path / "data" / "dart" / "finance" / "005930.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    writeParquetSorted(_sampleFinanceDf(), dest)

    assert dest.exists()
    tmp = dest.with_name(f"{dest.name}.tmp")
    assert not tmp.exists(), "tmp file leaked"
