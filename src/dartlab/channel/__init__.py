"""DartLab Channel — 외부 공유 엔진.

dartlab channel 명령으로 PC dartlab을 외부에서 접근 가능한 영구 URL로 공개한다.
Microsoft DevTunnels을 기술 백엔드로 사용 (VS Code Remote Tunnels와 동일 인프라).

상세: ops/channel.md
"""

from __future__ import annotations

from dartlab.channel.devtunnel import DevTunnelSetupError, setup_devtunnel

__all__ = ["DevTunnelSetupError", "setup_devtunnel"]
