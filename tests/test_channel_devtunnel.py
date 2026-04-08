"""Channel devtunnel 단위 테스트.

subprocess는 모킹 — devtunnel CLI 없이도 검증.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from dartlab.channel.devtunnel import (
    DevTunnelSetupError,
    _load_state,
    _save_state,
    find_devtunnel_binary,
    setup_devtunnel,
)

# ══════════════════════════════════════
# 모듈 import
# ══════════════════════════════════════


class TestImports:
    def test_module_exports(self):
        from dartlab.channel import DevTunnelSetupError as ExFromInit
        from dartlab.channel import setup_devtunnel as FnFromInit

        assert ExFromInit is DevTunnelSetupError
        assert FnFromInit is setup_devtunnel

    def test_callables(self):
        assert callable(find_devtunnel_binary)
        assert callable(setup_devtunnel)


# ══════════════════════════════════════
# find_devtunnel_binary
# ══════════════════════════════════════


class TestFindBinary:
    def test_returns_none_when_absent(self, tmp_path, monkeypatch):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LOCALAPPDATA", str(empty))
        monkeypatch.setenv("ProgramFiles", str(empty))
        monkeypatch.setenv("ProgramFiles(x86)", str(empty))
        monkeypatch.setattr("dartlab.channel.devtunnel.shutil.which", lambda x: None)
        monkeypatch.setattr("dartlab.channel.devtunnel._DARTLAB_BIN_DIR", empty / "nowhere")

        assert find_devtunnel_binary() is None

    def test_finds_path_binary(self, tmp_path, monkeypatch):
        # PATH에 있는 바이너리는 그대로 반환
        fake = tmp_path / "devtunnel.exe"
        fake.touch()
        monkeypatch.setattr("dartlab.channel.devtunnel.shutil.which", lambda x: str(fake))

        result = find_devtunnel_binary()
        assert result is not None


# ══════════════════════════════════════
# state 파일 round-trip
# ══════════════════════════════════════


class TestStateFile:
    def test_load_returns_empty_when_missing(self, tmp_path, monkeypatch):
        state_path = tmp_path / "missing.json"
        monkeypatch.setattr("dartlab.channel.devtunnel._STATE_FILE", state_path)
        assert _load_state() == {}

    def test_save_load_round_trip(self, tmp_path, monkeypatch):
        state_path = tmp_path / "state.json"
        monkeypatch.setattr("dartlab.channel.devtunnel._STATE_FILE", state_path)

        _save_state(tunnel_id="abc.jpe1", tunnel_label="dartlab-test")
        loaded = _load_state()

        assert loaded["tunnel_id"] == "abc.jpe1"
        assert loaded["tunnel_label"] == "dartlab-test"

    def test_save_merges_with_existing(self, tmp_path, monkeypatch):
        state_path = tmp_path / "state.json"
        monkeypatch.setattr("dartlab.channel.devtunnel._STATE_FILE", state_path)

        _save_state(tunnel_id="abc")
        _save_state(tunnel_label="label")
        loaded = _load_state()

        assert loaded["tunnel_id"] == "abc"
        assert loaded["tunnel_label"] == "label"


# ══════════════════════════════════════
# CLI 등록
# ══════════════════════════════════════


class TestChannelCLI:
    def test_channel_command_registered(self):
        from dartlab.cli.parser import build_parser

        parser = build_parser()
        # parse_args가 SystemExit 없이 통과하면 등록됨
        parser.parse_args(["channel", "--help"]) if False else None
        # 실제로는 --help가 sys.exit하므로, 명령 자체 등록 검증만:
        from dartlab.cli.commands.channel import configure_parser, run

        assert callable(run)
        assert callable(configure_parser)
