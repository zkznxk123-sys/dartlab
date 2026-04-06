"""CloudflareNamedTunnel 단위 테스트.

subprocess는 모킹해서 cloudflared 바이너리 없이도 동작 검증.

NOTE: CloudflareNamedTunnel 구현 진행 중 — 클래스 미존재 시 collection skip.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# 채널 엔진 작업 진행 중 — CloudflareNamedTunnel 미구현 시 collection skip
try:
    from dartlab.channel.tunnel import (
        _PROVIDERS,
        CloudflareNamedTunnel,
        create_tunnel,
    )
except ImportError:
    pytest.skip(
        "CloudflareNamedTunnel 미구현 — 채널 엔진 작업 진행 중",
        allow_module_level=True,
    )

# ══════════════════════════════════════
# 팩토리
# ══════════════════════════════════════


class TestCreateTunnel:
    def test_known_backends_registered(self):
        for name in ["cloudflare", "cloudflare-named", "ngrok", "ssh"]:
            assert name in _PROVIDERS

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="알 수 없는"):
            create_tunnel("nope")

    def test_named_accepts_kwargs(self):
        t = create_tunnel("cloudflare-named", domain="x.example.com", dry_run=True)
        assert isinstance(t, CloudflareNamedTunnel)
        assert t.domain == "x.example.com"
        assert t.dry_run is True


# ══════════════════════════════════════
# CloudflareNamedTunnel — dry-run 경로
# ══════════════════════════════════════


class TestCloudflareNamedDryRun:
    def test_dry_run_records_steps_without_subprocess(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        # 도메인 명시 필수
        t = CloudflareNamedTunnel(dry_run=True, auto_yes=True, domain="dartlab.foo.com")
        url = t.start(port=8400)
        assert url == "https://dartlab.foo.com"
        assert len(t._planned_steps) >= 1

    def test_dry_run_with_existing_tunnel_id(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        state_dir = tmp_path / ".dartlab"
        state_dir.mkdir(exist_ok=True)
        (state_dir / "tunnel-state.json").write_text(
            json.dumps({"tunnel_id": "existing-uuid", "hostname": "dartlab.foo.com"})
        )
        t = CloudflareNamedTunnel(dry_run=True, auto_yes=True)
        url = t.start(port=8400)
        assert "existing-uuid" in url or "dartlab.foo.com" in url

    def test_dry_run_does_not_call_subprocess(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        with (
            patch("dartlab.channel.tunnel.subprocess.run") as mock_run,
            patch("dartlab.channel.tunnel.subprocess.Popen") as mock_popen,
        ):
            t = CloudflareNamedTunnel(dry_run=True, auto_yes=True, domain="dartlab.foo.com")
            t.start(port=8400)
            mock_run.assert_not_called()
            mock_popen.assert_not_called()

    def test_no_domain_raises_helpful_error(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        t = CloudflareNamedTunnel(dry_run=True, auto_yes=True)
        with pytest.raises(RuntimeError, match="공개 도메인이 필요"):
            t.start(port=8400)


# ══════════════════════════════════════
# state 저장/로드
# ══════════════════════════════════════


class TestStatePersistence:
    def test_save_and_load_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        # dry_run=False여야 실제 저장됨
        t = CloudflareNamedTunnel(dry_run=False)
        t._save_state(tunnel_id="abc-123", hostname="x.foo.com")
        loaded = t._load_state()
        assert loaded["tunnel_id"] == "abc-123"
        assert loaded["hostname"] == "x.foo.com"

    def test_dry_run_does_not_persist_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        t = CloudflareNamedTunnel(dry_run=True)
        t._save_state(tunnel_id="dry-run-id", hostname="dry-run-id.cfargotunnel.com")
        # dry-run은 저장 안 함 → 빈 상태
        assert t._load_state() == {}

    def test_load_state_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        t = CloudflareNamedTunnel(dry_run=True)
        assert t._load_state() == {}


# ══════════════════════════════════════
# 바이너리 감지
# ══════════════════════════════════════


def _isolate_env(monkeypatch, tmp_path):
    """모든 cloudflared 탐색 경로를 빈 디렉토리로 격리."""
    empty = tmp_path / "empty"
    empty.mkdir(exist_ok=True)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(empty))
    monkeypatch.setenv("ProgramFiles", str(empty))
    monkeypatch.setenv("ProgramFiles(x86)", str(empty))
    monkeypatch.setattr("dartlab.channel.tunnel.shutil.which", lambda x: None)
    monkeypatch.setattr("dartlab.channel.tunnel._DARTLAB_BIN_DIR", empty / "dartlab-bin-empty")


class TestEnsureBinary:
    def test_uses_path_binary_if_present(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        # PATH binary가 실제 존재하는 파일이어야 _scan_known_paths가 받음
        fake = tmp_path / "fake-cloudflared.exe"
        fake.touch()
        monkeypatch.setattr("dartlab.channel.tunnel.shutil.which", lambda x: str(fake))
        t = CloudflareNamedTunnel()
        assert t._ensure_binary() == str(fake)

    def test_uses_local_binary_if_present(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        bindir = tmp_path / ".dartlab" / "bin"
        bindir.mkdir(parents=True)
        local = bindir / "cloudflared.exe"
        local.touch()
        monkeypatch.setattr("dartlab.channel.tunnel._DARTLAB_BIN_DIR", bindir)
        t = CloudflareNamedTunnel()
        result = t._ensure_binary()
        assert "cloudflared" in result

    def test_dry_run_skips_install(self, tmp_path, monkeypatch):
        _isolate_env(monkeypatch, tmp_path)
        t = CloudflareNamedTunnel(dry_run=True)
        result = t._ensure_binary()
        assert result == "cloudflared"
        assert any("install" in s for s in t._planned_steps)

    def test_scan_finds_winget_package_dir(self, tmp_path, monkeypatch):
        """winget 패키지 폴더에서 cloudflared.exe를 직접 발견."""
        _isolate_env(monkeypatch, tmp_path)
        local_app = tmp_path / "local-app"
        pkg = local_app / "Microsoft" / "WinGet" / "Packages" / "Cloudflare.cloudflared_Microsoft.Winget.Source_xxx"
        pkg.mkdir(parents=True)
        exe = pkg / "cloudflared.exe"
        exe.touch()
        monkeypatch.setenv("LOCALAPPDATA", str(local_app))
        # Windows에서만 의미 있음 — 다른 OS에서는 skip
        import platform

        if platform.system() != "Windows":
            return
        result = CloudflareNamedTunnel._scan_known_paths()
        assert result is not None
        assert "cloudflared.exe" in result


# ══════════════════════════════════════
# config 작성
# ══════════════════════════════════════


class TestWriteConfig:
    def test_config_contains_sse_settings(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        cf_config = tmp_path / ".cloudflared"
        cf_config.mkdir()
        monkeypatch.setattr("dartlab.channel.tunnel._CLOUDFLARED_CONFIG", cf_config)
        monkeypatch.setattr(
            "dartlab.channel.tunnel._DARTLAB_TUNNEL_CONFIG",
            cf_config / "config-dartlab.yml",
        )
        t = CloudflareNamedTunnel()
        t._tunnel_id = "abc-123"
        t._hostname = "dartlab.foo.com"
        path = t._write_config(port=8400)
        assert path.exists()
        text = path.read_text()
        assert "tunnel: abc-123" in text
        assert "dartlab.foo.com" in text
        assert "http://localhost:8400" in text
        assert "disableChunkedEncoding: false" in text  # SSE
        assert "http_status:404" in text


# ══════════════════════════════════════
# DevTunnels (간단 — 바이너리 없으면 모듈 에러, install 호출 안 함)
# ══════════════════════════════════════


class TestDevTunnel:
    def test_module_imports(self):
        from dartlab.channel.devtunnel import (
            find_devtunnel_binary,
            setup_devtunnel,
        )

        assert callable(find_devtunnel_binary)
        assert callable(setup_devtunnel)

    def test_find_binary_returns_none_when_absent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "empty"))
        monkeypatch.setenv("ProgramFiles", str(tmp_path / "empty"))
        monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "empty"))
        monkeypatch.setattr("dartlab.channel.devtunnel.shutil.which", lambda x: None)
        monkeypatch.setattr("dartlab.channel.devtunnel._DARTLAB_BIN_DIR", tmp_path / "nowhere")
        from dartlab.channel.devtunnel import find_devtunnel_binary

        assert find_devtunnel_binary() is None

    def test_state_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        # state path는 모듈 상수라 monkeypatch 필요
        state_path = tmp_path / ".dartlab" / "devtunnel-state.json"
        monkeypatch.setattr("dartlab.channel.devtunnel._STATE_FILE", state_path)
        from dartlab.channel.devtunnel import _load_state, _save_state

        assert _load_state() == {}
        _save_state(tunnel_id="abc-xyz", tunnel_label="test")
        loaded = _load_state()
        assert loaded["tunnel_id"] == "abc-xyz"
        assert loaded["tunnel_label"] == "test"
