"""agent.runAgent trace dump (~/.dartlab/ai_trace/) + 7 일 retention 단위 테스트.

마스터 플랜 트랙 2 PR-O4 동행. KPI 관측 인프라 — trace 메모리 휘발 회귀 (박제 5/10) →
세션 종료마다 JSON dump 활성 (환경변수 enable).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from dartlab.ai.agent import runAgent
from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import ProviderTurn

pytestmark = pytest.mark.unit


class _ScriptedProvider:
    class _Cfg:
        provider = "scripted"
        model = "scripted-model"

    def __init__(self, turns: list[ProviderTurn]) -> None:
        self.config = self._Cfg()
        self._turns = list(turns)
        self._index = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self._index >= len(self._turns):
            return ProviderTurn(content="", toolCalls=[], raw=None)
        t = self._turns[self._index]
        self._index += 1
        return t


def _collect(stream: Iterable[TraceEvent]) -> list[TraceEvent]:
    return list(stream)


def test_trace_dump_disabled_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """기본 OFF — 환경변수 미설정 시 dump 파일 생성 0."""
    monkeypatch.delenv("DARTLAB_AI_TRACE_DUMP", raising=False)
    monkeypatch.setenv("DARTLAB_AI_TRACE_DIR", str(tmp_path))

    provider = _ScriptedProvider([ProviderTurn(content="ok", toolCalls=[], raw=None)])
    _collect(runAgent("hi", provider=provider, toolNames=()))

    files = list(tmp_path.glob("*.json"))
    assert files == [], "기본 OFF 상태에서 dump 파일 생성 금지"


def test_trace_dump_enabled_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수 ON 시 trace JSON dump."""
    monkeypatch.setenv("DARTLAB_AI_TRACE_DUMP", "1")
    monkeypatch.setenv("DARTLAB_AI_TRACE_DIR", str(tmp_path))

    provider = _ScriptedProvider([ProviderTurn(content="hello", toolCalls=[], raw=None)])
    _collect(runAgent("hi", provider=provider, toolNames=()))

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["question"] == "hi"
    assert data["provider"] == "scripted"
    assert data["model"] == "scripted-model"
    kinds = [e["kind"] for e in data["events"]]
    assert "chunk" in kinds
    assert "done" in kinds
    assert "turn_timing" in kinds  # PR-O2 timing event 도 누적


def test_trace_dump_prune_retention(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """7 일 retention rotate — mtime 가 8 일 전 파일은 정리."""
    from dartlab.ai.agent import _pruneOldTraces

    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    old_file.write_text("{}", encoding="utf-8")
    new_file.write_text("{}", encoding="utf-8")
    # 8 일 전 mtime
    old_ts = time.time() - 8 * 86400
    os.utime(old_file, (old_ts, old_ts))

    _pruneOldTraces(tmp_path, retentionDays=7)

    assert not old_file.exists()
    assert new_file.exists()


def test_trace_dump_default_dir_is_home_dartlab(monkeypatch: pytest.MonkeyPatch) -> None:
    """기본 디렉토리는 ``~/.dartlab/ai_trace/``."""
    from dartlab.ai.agent import _resolveTraceDir

    monkeypatch.delenv("DARTLAB_AI_TRACE_DIR", raising=False)
    resolved = _resolveTraceDir()
    assert resolved.name == "ai_trace"
    assert resolved.parent.name == ".dartlab"
    assert resolved.parent.parent == Path.home()


def test_trace_dump_env_override_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DARTLAB_AI_TRACE_DIR override 작동."""
    from dartlab.ai.agent import _resolveTraceDir

    monkeypatch.setenv("DARTLAB_AI_TRACE_DIR", str(tmp_path))
    assert _resolveTraceDir() == tmp_path
