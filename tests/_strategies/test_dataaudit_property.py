"""core/dataAudit hypothesis property — T6-1 (9/10)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestDataAuditProperty:
    """dataAudit.recordLineage / readLineage 의 property 4."""

    @given(
        source=st.text(min_size=1, max_size=30),
        version=st.text(min_size=1, max_size=20),
        rowCount=st.integers(min_value=0, max_value=10**9),
    )
    def test_record_lineage_round_trip(self, source: str, version: str, rowCount: int) -> None:
        from dartlab.core.dataAudit import readLineage, recordLineage

        with tempfile.TemporaryDirectory() as tmp:
            baseDir = Path(tmp)
            recordLineage(source=source, version=version, rowCount=rowCount, baseDir=baseDir)
            records = readLineage(sinceDays=1, baseDir=baseDir)
            assert any(r.get("source") == source for r in records)

    def test_read_lineage_empty_dir(self) -> None:
        from dartlab.core.dataAudit import readLineage

        with tempfile.TemporaryDirectory() as tmp:
            assert readLineage(baseDir=Path(tmp)) == []

    @given(n=st.integers(min_value=1, max_value=20))
    def test_record_lineage_multiple_appends(self, n: int) -> None:
        from dartlab.core.dataAudit import readLineage, recordLineage

        with tempfile.TemporaryDirectory() as tmp:
            baseDir = Path(tmp)
            for i in range(n):
                recordLineage(source=f"source-{i}", baseDir=baseDir)
            records = readLineage(baseDir=baseDir)
            assert len(records) >= n

    def test_read_lineage_source_filter(self) -> None:
        from dartlab.core.dataAudit import readLineage, recordLineage

        with tempfile.TemporaryDirectory() as tmp:
            baseDir = Path(tmp)
            recordLineage(source="A", baseDir=baseDir)
            recordLineage(source="B", baseDir=baseDir)
            filtered = readLineage(source="A", baseDir=baseDir)
            assert all(r.get("source") == "A" for r in filtered)
