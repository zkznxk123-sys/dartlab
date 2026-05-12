"""dataLoader.downloadAll allow_patterns 회귀 테스트.

P0 버그 (2026-04): `allow_patterns="dart/scan/**/*.parquet"` 가 huggingface_hub
내부 fnmatch 에서 루트 파일(finance.parquet 등)을 제외시켜 다운로드 누락 →
scan 프리빌드 불완전 → `scan('account', ...)` 가 종목별 fallback 으로 빠져
부분 결과(2행)를 전수인 양 반환하는 심각한 오동작.

이 테스트는 그 버그가 다시 들어오는 것을 방지한다.
"""

from __future__ import annotations

import pytest
from huggingface_hub.utils import filter_repo_objects

_EXPECTED_SCAN_FILES = [
    "dart/scan/finance.parquet",
    "dart/scan/changes.parquet",
    "dart/scan/sharesOutstanding.parquet",
    "dart/scan/report/auditOpinion.parquet",
    "dart/scan/report/employee.parquet",
    "dart/scan/report/majorHolder.parquet",
]


@pytest.mark.unit
def test_fnmatch_double_star_excludes_root_files():
    """huggingface_hub 의 fnmatch 는 `**` 가 특수문자가 아니다 — 중간 디렉토리
    최소 1단계를 강제한다. 이 전제가 깨지면 (예: huggingface_hub 가 glob 시맨틱
    으로 바뀌면) 테스트는 실패하고 개선 로직을 재검토해야 한다."""
    matched = set(filter_repo_objects(_EXPECTED_SCAN_FILES, allow_patterns="dart/scan/**/*.parquet"))
    root_files = {f for f in _EXPECTED_SCAN_FILES if "/" not in f.removeprefix("dart/scan/")}
    assert root_files.isdisjoint(matched), (
        f"`**/*.parquet` 단일 패턴이 루트 파일을 매칭함 ({matched & root_files}). "
        f"fnmatch 시맨틱 변경 의심 — 더 간단한 패턴으로 회귀 가능."
    )


@pytest.mark.unit
def test_scan_allow_patterns_matches_root_and_nested():
    """현재 수정안: 두 패턴 리스트가 루트 + 하위 폴더 모두 매칭해야 한다."""
    patterns = ["dart/scan/*.parquet", "dart/scan/**/*.parquet"]
    matched = set(filter_repo_objects(_EXPECTED_SCAN_FILES, allow_patterns=patterns))
    missing = set(_EXPECTED_SCAN_FILES) - matched
    assert not missing, f"allow_patterns 누락: {missing}"


@pytest.mark.unit
def test_downloadAll_scan_uses_list_pattern(tmp_path, monkeypatch):
    """downloadAll 이 scan 카테고리에 대해 리스트 패턴을 전달하는지 검증.

    snapshot_download 를 모킹해 실제 네트워크 없이 호출 인자만 확인한다.
    """
    from unittest.mock import patch

    from dartlab import config
    from dartlab.frame import dataLoader

    monkeypatch.setattr(config, "dataDir", str(tmp_path))
    scanDir = tmp_path / "dart" / "scan"
    scanDir.mkdir(parents=True, exist_ok=True)
    fakeFinance = scanDir / "finance.parquet"
    fakeFinance.write_bytes(b"fake")

    with patch("huggingface_hub.snapshot_download", return_value=None) as mockDl:
        dataLoader.downloadAll("scan")

    calls = mockDl.call_args_list
    assert calls, "snapshot_download 가 호출되지 않았다"
    passed = calls[0].kwargs.get("allow_patterns")
    assert isinstance(passed, list), f"scan 은 리스트 패턴이어야 함 (실제: {type(passed).__name__})"
    assert "dart/scan/*.parquet" in passed, f"루트 매칭 패턴 누락: {passed}"
    assert "dart/scan/**/*.parquet" in passed, f"하위 폴더 매칭 패턴 누락: {passed}"


@pytest.mark.unit
def test_downloadAll_scan_raises_on_missing_finance(tmp_path, monkeypatch):
    """§2 회귀: downloadAll("scan") 이 finance.parquet 없이 조용히 끝나지 않는다.

    `allow_patterns` 회귀 등으로 루트 파일이 누락되면 RuntimeError 를 raise 해
    상위 fallback 경로가 부분 결과를 반환하지 못하게 막는다.
    """
    from unittest.mock import patch

    from dartlab import config
    from dartlab.frame import dataLoader

    monkeypatch.setattr(config, "dataDir", str(tmp_path))
    # 실제 HF 호출 차단 + report/ 만 생성 (루트 finance.parquet 은 의도적으로 누락)
    scanDir = tmp_path / "dart" / "scan"
    (scanDir / "report").mkdir(parents=True, exist_ok=True)
    (scanDir / "report" / "dummy.parquet").write_bytes(b"x")

    with patch("huggingface_hub.snapshot_download", return_value=None):
        with pytest.raises(RuntimeError, match="scan 프리빌드 다운로드가 불완전"):
            dataLoader.downloadAll("scan")
