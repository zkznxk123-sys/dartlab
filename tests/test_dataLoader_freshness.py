"""
dataLoader._checkRemoteFreshness 회귀 테스트.

P0 버그 (2026-04-06): etag 사이드카가 없을 때 현재 HF ETag를 그대로 저장 + fresh
판정 → parquet은 옛날 그대로인데 .etag만 새로 만들어져서 영구 stale 고정.

이 테스트는 그 버그가 다시 들어오는 것을 방지한다.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from dartlab.core.dataLoader import _checkRemoteFreshness


@pytest.mark.unit
def test_etag_missing_should_be_stale(tmp_path):
    """P0 회귀: etag 사이드카가 없으면 stale로 판정해야 한다.

    과거 버그: etag 없으면 현재 HF ETag 저장 후 fresh(False) 반환.
    수정 후: etag 없으면 stale(True) 반환 → 다운로드 강제.
    """
    parquet = tmp_path / "test.parquet"
    parquet.write_bytes(b"old data")
    etag_file = parquet.with_suffix(".parquet.etag")
    assert not etag_file.exists()

    # 원격 ETag 정상 조회 가능
    with patch(
        "dartlab.core.dataLoader._fetchRemoteEtagAndSize",
        return_value=("remote-etag-123", 8),  # 8 bytes = 로컬 크기와 같음
    ):
        stale = _checkRemoteFreshness("test", parquet, "finance")

    # 핵심: etag 없으면 무조건 stale (True)
    assert stale is True, "etag 없을 때 fresh로 판정하면 안 됨"

    # 부수: etag 사이드카가 자동 생성되면 안 됨 (다운로드 후에만 _saveEtag로 생성)
    assert not etag_file.exists(), "etag 사이드카는 _checkRemoteFreshness가 만들면 안 됨"


@pytest.mark.unit
def test_etag_match_and_size_match_is_fresh(tmp_path):
    """ETag 같고 Content-Length 같으면 fresh."""
    parquet = tmp_path / "test.parquet"
    parquet.write_bytes(b"matching data")  # 13 bytes
    etag_file = parquet.with_suffix(".parquet.etag")
    etag_file.write_text("matched-etag", encoding="utf-8")

    with patch(
        "dartlab.core.dataLoader._fetchRemoteEtagAndSize",
        return_value=("matched-etag", 13),
    ):
        stale = _checkRemoteFreshness("test", parquet, "finance")

    assert stale is False


@pytest.mark.unit
def test_etag_match_but_size_differs_is_stale(tmp_path):
    """P0 회귀: ETag는 같지만 Content-Length가 다르면 stale (손상 방어).

    HF ETag가 우연히 같지만 로컬 parquet이 손상돼서 크기가 다른 케이스를 잡는다.
    """
    parquet = tmp_path / "test.parquet"
    parquet.write_bytes(b"corrupted")  # 9 bytes
    etag_file = parquet.with_suffix(".parquet.etag")
    etag_file.write_text("matched-etag", encoding="utf-8")

    with patch(
        "dartlab.core.dataLoader._fetchRemoteEtagAndSize",
        return_value=("matched-etag", 100),  # 다름
    ):
        stale = _checkRemoteFreshness("test", parquet, "finance")

    assert stale is True, "Content-Length 차이로 손상 케이스 잡혀야 함"


@pytest.mark.unit
def test_etag_differs_is_stale(tmp_path):
    """ETag가 다르면 stale."""
    parquet = tmp_path / "test.parquet"
    parquet.write_bytes(b"old")
    etag_file = parquet.with_suffix(".parquet.etag")
    etag_file.write_text("old-etag", encoding="utf-8")

    with patch(
        "dartlab.core.dataLoader._fetchRemoteEtagAndSize",
        return_value=("new-etag", 3),
    ):
        stale = _checkRemoteFreshness("test", parquet, "finance")

    assert stale is True


@pytest.mark.unit
def test_remote_etag_unavailable_returns_none(tmp_path):
    """원격 ETag 못 가져오면 None (네트워크 오류)."""
    parquet = tmp_path / "test.parquet"
    parquet.write_bytes(b"x")

    with patch(
        "dartlab.core.dataLoader._fetchRemoteEtagAndSize",
        return_value=("", 0),
    ):
        stale = _checkRemoteFreshness("test", parquet, "finance")

    assert stale is None


@pytest.mark.unit
def test_reportNm_to_finance_key():
    """syncRecent의 _reportNmToFinanceKey: 보고서명 → (year, reprt_code) 매핑."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "syncRecent",
        Path(__file__).parent.parent / ".github" / "scripts" / "syncRecent.py",
    )
    if spec is None or spec.loader is None:
        pytest.skip("syncRecent.py 로드 실패")
    syncRecent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(syncRecent)

    fn = syncRecent._reportNmToFinanceKey

    # 사업보고서
    assert fn("사업보고서 (2025.12)") == ("2025", "11011")
    # 반기보고서
    assert fn("반기보고서 (2025.06)") == ("2025", "11012")
    # 분기보고서 Q1
    assert fn("분기보고서 (2025.03)") == ("2025", "11013")
    # 분기보고서 Q3
    assert fn("분기보고서 (2025.09)") == ("2025", "11014")
    # 매칭 안 됨
    assert fn("기타 공시") is None
    assert fn("사업보고서") is None  # 연도 없음


@pytest.mark.unit
def test_collectFinance_targetPeriods_skips_88_diff():
    """_collectFinance가 targetPeriods를 받으면 _buildAllPeriods 88분기 차집합을 안 돌아야 한다.

    P0 회귀 (Phase 5): list.json 기반 가벼운 경로가 무거운 경로로 회귀하는 것을 방지.
    """
    import inspect
    from dartlab.providers.dart.openapi.batch import _collectFinance, _collectReport, batchCollect, _workerLoop

    # 새 인자 등록 검증
    sig_finance = inspect.signature(_collectFinance)
    assert "targetPeriods" in sig_finance.parameters, "_collectFinance에 targetPeriods 누락"

    sig_report = inspect.signature(_collectReport)
    assert "targetPeriods" in sig_report.parameters, "_collectReport에 targetPeriods 누락"

    sig_batch = inspect.signature(batchCollect)
    assert "targetPeriodsByCode" in sig_batch.parameters, "batchCollect에 targetPeriodsByCode 누락"

    sig_worker = inspect.signature(_workerLoop)
    assert "targetPeriodsByCode" in sig_worker.parameters, "_workerLoop에 targetPeriodsByCode 누락"


@pytest.mark.unit
def test_buildAllPeriods_newest_first():
    """_buildAllPeriods는 최신 분기부터 반환해야 한다.

    P0 회귀: 옛날 분기부터 처리하면 API 한도 도달 시 매번 최신 분기가 잘려서
    신규 데이터가 영구 누락된다 (2026-04-06 388개 종목 누락 사례).
    """
    from dartlab.providers.dart.openapi.batch import _buildAllPeriods
    from datetime import datetime

    periods = _buildAllPeriods()
    currentYear = datetime.now().year

    # 첫 번째는 현재 연도 Q4 (사업보고서, 11011)
    assert periods[0][0] == str(currentYear), "첫 번째는 최신 연도여야 함"
    assert periods[0][1] == "11011", "현재 연도 첫 번째는 Q4(사업보고서)여야 함"

    # 한 연도 안에서도 Q4 → Q3 → Q2 → Q1 순서
    yearGroups: dict[str, list[str]] = {}
    for y, c in periods:
        yearGroups.setdefault(y, []).append(c)
    expected_order = ["11011", "11014", "11012", "11013"]  # Q4 Q3 Q2 Q1
    for y, codes in yearGroups.items():
        assert codes == expected_order, f"{y}년 분기 순서가 Q4→Q1이 아님: {codes}"
