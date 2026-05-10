"""tool_storage — 큰 도구 결과 디스크 persist + preview inject."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartlab.ai import toolStorage as tool_storage
from dartlab.ai.toolStorage import (
    MAX_TOOL_RESULT_CHARS,
    PREVIEW_CHARS,
    buildPersistedContent,
    exceedsSizeCap,
    persistLargeResult,
)


@pytest.fixture
def isolated_results_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """저장 디렉토리를 tmp_path 로 격리 — 사용자 홈 오염 방지."""
    monkeypatch.setattr(tool_storage, "_DEFAULT_RESULTS_ROOT", tmp_path / "tool-results")
    return tmp_path / "tool-results"


@pytest.mark.unit
def test_exceeds_size_cap_threshold() -> None:
    assert exceedsSizeCap("x" * MAX_TOOL_RESULT_CHARS) is False
    assert exceedsSizeCap("x" * (MAX_TOOL_RESULT_CHARS + 1)) is True
    assert exceedsSizeCap("") is False


@pytest.mark.unit
def test_persist_large_result_creates_file(isolated_results_root: Path) -> None:
    content = "row\n" * 20000
    preview, file_path = persistLargeResult("RunPython", "call_abc123", content)

    target = Path(file_path)
    assert target.exists()
    assert target.parent == isolated_results_root
    assert target.read_text(encoding="utf-8") == content
    assert len(preview) == PREVIEW_CHARS
    assert preview == content[:PREVIEW_CHARS]


@pytest.mark.unit
def test_persist_sanitizes_unsafe_id(isolated_results_root: Path) -> None:
    _, file_path = persistLargeResult("RunPython", "call/../bad:id", "data")
    target = Path(file_path)
    assert target.parent == isolated_results_root
    # 파일명에 슬래시·콜론 같은 위험 문자 없음
    assert "/" not in target.name
    assert ":" not in target.name
    assert ".." not in target.name


@pytest.mark.unit
def test_persist_falls_back_to_tool_name_when_id_empty(isolated_results_root: Path) -> None:
    _, file_path = persistLargeResult("RunPython", "", "data")
    assert Path(file_path).name.startswith("RunPython")


@pytest.mark.unit
def test_persist_falls_back_to_default_when_both_empty(isolated_results_root: Path) -> None:
    _, file_path = persistLargeResult("", "", "data")
    assert Path(file_path).name == "result.txt"


@pytest.mark.unit
def test_build_persisted_content_format() -> None:
    out = buildPersistedContent("/tmp/x.txt", "hello", 60_000)
    assert "/tmp/x.txt" in out
    assert "hello" in out
    assert "59 KB" in out
    assert "Read" in out  # Read 도구 안내


@pytest.mark.unit
def test_build_persisted_content_min_kb() -> None:
    # 1 KB 미만이어도 0 KB 표시 안 함 (혼란 방지)
    out = buildPersistedContent("/tmp/x.txt", "h", 100)
    assert "0 KB" not in out
    assert "1 KB" in out


@pytest.mark.unit
def test_unicode_content_round_trip(isolated_results_root: Path) -> None:
    content = "삼성전자 매출액 — 304.7조원\n" * 5000
    preview, file_path = persistLargeResult("RunPython", "call_x", content)
    assert Path(file_path).read_text(encoding="utf-8") == content
    assert "삼성전자" in preview
