"""guide share readiness + hint 함수 단위 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from dartlab.guide.hints import (
    onCloudflaredMissing,
    onCloudflareLoginRequired,
    onShareSecurityWarning,
    onTunnelStartFailed,
)
from dartlab.guide.readiness import ReadyStatus, _checkShare

# ══════════════════════════════════════
# checkShare
# ══════════════════════════════════════


class TestCheckShare:
    def test_returns_result_with_share_feature(self):
        result = _checkShare()
        assert result.feature == "share"
        assert result.status in (ReadyStatus.READY, ReadyStatus.PARTIAL, ReadyStatus.NOT_READY)

    def test_persistent_mode_checks_cloudflared(self, tmp_path, monkeypatch):
        # cloudflared 없는 상태로 강제
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr("shutil.which", lambda x: None)
        result = _checkShare(persistent=True)
        kinds = [i.kind for i in result.issues]
        # cloudflared 또는 cf_login 경고 존재
        assert any("cloudflared" in k or "cf_login" in k for k in kinds)

    def test_basic_mode_no_cloudflared_check(self, tmp_path, monkeypatch):
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr("shutil.which", lambda x: None)
        result = _checkShare(persistent=False)
        kinds = [i.kind for i in result.issues]
        assert not any("cloudflared" in k for k in kinds)


# ══════════════════════════════════════
# hint 함수
# ══════════════════════════════════════


class TestHints:
    def test_cloudflared_missing_windows(self):
        msg = onCloudflaredMissing("Windows")
        assert "winget" in msg
        assert "cloudflared" in msg
        assert "dartlab channel --persistent" in msg

    def test_cloudflared_missing_mac(self):
        msg = onCloudflaredMissing("Darwin")
        assert "brew" in msg

    def test_cloudflared_missing_linux(self):
        msg = onCloudflaredMissing("Linux")
        assert "cloudflared" in msg

    def test_cloudflared_missing_unknown_os(self):
        msg = onCloudflaredMissing("")
        assert "github.com" in msg.lower()

    def test_login_required_includes_browser_guide(self):
        msg = onCloudflareLoginRequired()
        assert "브라우저" in msg
        assert "Authorize" in msg
        assert "도메인" in msg

    def test_tunnel_start_failed_maps_known_codes(self):
        msg = onTunnelStartFailed("Error 1033: DNS issue")
        assert "DNS" in msg
        msg2 = onTunnelStartFailed("502 Bad Gateway")
        assert "로컬 서버" in msg2 or "502" in msg2

    def test_tunnel_start_failed_unknown_falls_back(self):
        msg = onTunnelStartFailed("some random unparseable garbage")
        assert "원본 에러" in msg or "추가 점검" in msg

    def test_security_warning_persistent(self):
        msg = onShareSecurityWarning(
            mode="cloudflare-named",
            hostname="dartlab.foo.com",
            readonly=True,
        )
        assert "Named Tunnel" in msg
        assert "dartlab.foo.com" in msg
        assert "읽기 전용" in msg
        assert "audit.jsonl" in msg

    def test_security_warning_quick_readwrite(self):
        msg = onShareSecurityWarning(
            mode="cloudflare",
            hostname="abc.trycloudflare.com",
            readonly=False,
        )
        assert "Quick" in msg
        assert "읽기/쓰기" in msg


# ══════════════════════════════════════
# desk handleError 통합
# ══════════════════════════════════════


class TestDeskHandleError:
    def test_share_feature_routes_through_hints(self):
        from dartlab.guide.desk import GuideDesk

        desk = GuideDesk()
        err = RuntimeError("cloudflared not found in PATH")
        msg = desk.handleError(err, feature="share")
        assert "cloudflared" in msg or "설치" in msg

    def test_tunnel_keyword_in_error_routes_to_share(self):
        from dartlab.guide.desk import GuideDesk

        desk = GuideDesk()
        err = RuntimeError("tunnel error 1033")
        msg = desk.handleError(err)
        # 1033 매핑 또는 일반 fallback 둘 중 하나
        assert "DNS" in msg or "1033" in msg or "원본" in msg or "터널" in msg
