"""External sharing guidance messages.

Capabilities:
    - Builds Cloudflare/cloudflared and external sharing recovery guidance.

Args:
    Helpers accept platform, stderr, or share-mode context.

Returns:
    Korean user-facing guidance strings.

Example:
    >>> "cloudflared" in onCloudflaredMissing()
    True

Guide:
    Keep tunnel-specific copy here so general error handling remains small.

SeeAlso:
    ``messagingErrors`` and ``cli.commands.channel``.

Requires:
    Static cloudflared hint catalog from ``messagingCatalog``.

AIContext:
    Separates operational recovery copy from generic exception classification.

LLM Specifications:
    AntiPatterns: Do not start or stop tunnels here; return text only.
    OutputSchema: Korean guidance string.
    Prerequisites: Caller has detected a share/channel condition.
    Freshness: Installation commands may need review when supported platforms change.
    Dataflow: share error context -> hint matcher -> guidance string.
    TargetMarkets: Local desktop/server share workflows.
"""

from __future__ import annotations

from dartlab.core.messagingCatalog import CLOUDFLARED_ERROR_HINTS as _CLOUDFLARED_ERROR_HINTS


def onCloudflaredMissing(osName: str = "") -> str:
    """Return manual install guidance when cloudflared is missing.

    Args:
        osName: Platform name such as ``"Windows"``, ``"Darwin"``, or ``"Linux"``.

    Returns:
        Korean install guidance.

    Raises:
        None.

    Example:
        >>> "cloudflared" in onCloudflaredMissing("Windows")
        True
    """
    lines = ["\n  cloudflared 바이너리를 찾을 수 없습니다."]
    if osName == "Windows":
        lines.append("  설치(택1):")
        lines.append("    a) winget install --id Cloudflare.cloudflared -e")
        lines.append(
            "    b) https://github.com/cloudflare/cloudflared/releases 에서 cloudflared-windows-amd64.exe 다운로드"
        )
        lines.append("       → ~/.dartlab/bin/cloudflared.exe 로 저장")
    elif osName == "Darwin":
        lines.append("  설치(택1):")
        lines.append("    a) brew install cloudflared")
        lines.append("    b) https://github.com/cloudflare/cloudflared/releases 에서 darwin 빌드 다운로드")
    elif osName == "Linux":
        lines.append("  설치(택1):")
        lines.append("    a) https://pkg.cloudflare.com 의 apt/yum 저장소 등록")
        lines.append("    b) https://github.com/cloudflare/cloudflared/releases 에서 linux 빌드 다운로드")
    else:
        lines.append("  https://github.com/cloudflare/cloudflared/releases 에서 OS에 맞는 빌드를 받으세요")
    lines.append("\n  설치 후 다시 실행: dartlab channel --persistent")
    return "\n".join(lines)


def onCloudflareLoginRequired() -> str:
    """Return first-time Cloudflare authorization guidance.

    Args:
        None.

    Returns:
        Korean login guidance.

    Raises:
        None.

    Example:
        >>> "Cloudflare" in onCloudflareLoginRequired()
        True
    """
    return (
        "\n  영구 URL 모드는 Cloudflare 계정 인증이 1회 필요합니다.\n"
        "  잠시 후 브라우저가 자동으로 열립니다.\n"
        "  → Cloudflare 로그인 → 사용할 도메인(zone) 선택 → Authorize 클릭\n"
        "  (도메인이 없다면 https://dash.cloudflare.com 에서 무료로 도메인 1개를 추가하세요)\n"
        "  인증 후에는 다시 묻지 않습니다."
    )


def onTunnelStartFailed(stderrExcerpt: str) -> str:
    """Analyze cloudflared stderr and return recovery guidance.

    Args:
        stderrExcerpt: Recent stderr text from a failed tunnel process.

    Returns:
        Korean diagnostic guidance.

    Raises:
        None.

    Example:
        >>> "cloudflared" in onTunnelStartFailed("502 bad gateway")
        True
    """
    lines = ["\n  cloudflared 터널 시작에 실패했습니다."]
    matched = []
    for needle, hint in _CLOUDFLARED_ERROR_HINTS:
        if needle.lower() in stderrExcerpt.lower():
            matched.append(f"    • {hint}")
    if matched:
        lines.append("  추정 원인:")
        lines.extend(matched)
    else:
        lines.append("  원본 에러:")
        for line in stderrExcerpt.strip().splitlines()[-5:]:
            lines.append(f"    {line}")
    lines.append("\n  추가 점검:")
    lines.append("    • dartlab channel --persistent --dry-run 으로 단계 확인")
    lines.append("    • ~/.cloudflared/cert.pem 존재 확인")
    lines.append("    • cloudflared tunnel list 로 tunnel 상태 확인")
    return "\n".join(lines)


def onShareSecurityWarning(*, mode: str, hostname: str, readonly: bool) -> str:
    """Return the security summary shown when sharing starts.

    Args:
        mode: Share backend identifier.
        hostname: Public hostname shown to users.
        readonly: Whether write endpoints are disabled.

    Returns:
        Korean security summary.

    Raises:
        None.

    Example:
        >>> "권한" in onShareSecurityWarning(mode="cloudflare", hostname="x", readonly=True)
        True
    """
    mode_labels = {
        "cloudflare": "Quick Tunnel (임시 URL, 데모용)",
        "cloudflare-named": "Named Tunnel (영구 URL, 1인 SaaS 표준)",
        "tailscale": "Tailscale Funnel (본인/지인용 ts.net)",
        "ngrok": "ngrok",
        "ssh": "SSH (localhost.run)",
    }
    label = mode_labels.get(mode, mode)
    rw = "읽기 전용 (POST 차단)" if readonly else "읽기/쓰기 (POST /api/ask 허용)"
    return (
        f"\n  ── 외부 공유 보안 요약 ──\n"
        f"  모드        : {label}\n"
        f"  호스트      : {hostname}\n"
        f"  권한        : {rw}\n"
        f"  방어 계층   : 토큰 + 화이트리스트 + Rate Limit + 감사 로그 + Kill Switch\n"
        f"  감사 로그   : ~/.dartlab/audit.jsonl\n"
        f"  종료        : Ctrl+C (포그라운드) / cloudflared service uninstall (서비스 모드)\n"
        f"  주의        : 토큰이 들어간 URL은 노출 = 접근 허용. 토큰 회수는 서버 재시작.\n"
    )


__all__ = [
    "onCloudflareLoginRequired",
    "onCloudflaredMissing",
    "onShareSecurityWarning",
    "onTunnelStartFailed",
]
