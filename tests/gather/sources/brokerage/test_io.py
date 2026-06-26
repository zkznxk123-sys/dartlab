"""brokerage.io 단위 테스트 — 월별 파티션 write + report_id dedup + round-trip (네트워크 0)."""

from __future__ import annotations

import pytest

from dartlab.gather.sources.brokerage.io import loadLocal, writeMonthly
from dartlab.gather.sources.brokerage.schema import ReportMeta, toDataFrame

pytestmark = pytest.mark.unit


def test_write_partitions_by_month(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    items = [
        ReportMeta("nh", "NH투자", "A", "u1", "2026-06-26", ticker="005930"),
        ReportMeta("nh", "NH투자", "B", "u2", "2026-05-15"),
    ]
    changed = writeMonthly(toDataFrame(items))
    assert set(changed) == {"202606.parquet", "202605.parquet"}
    assert loadLocal().height == 2


def test_dedup_on_rerun(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    items = [ReportMeta("nh", "NH투자", "A", "u1", "2026-06-26")]
    writeMonthly(toDataFrame(items))
    writeMonthly(toDataFrame(items))  # 재수집 — 같은 report_id
    assert loadLocal().height == 1


def test_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DARTLAB_DATA_DIR", str(tmp_path))
    assert writeMonthly(toDataFrame([])) == []
    assert loadLocal().height == 0
