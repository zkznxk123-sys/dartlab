"""`dartlab channel` — 외부 공유 채널 (DevTunnels 기본).

Microsoft DevTunnels을 이용해 PC dartlab을 외부 어디서나 접근 가능한 URL로 공개.
VS Code Remote Tunnels의 기반 기술과 동일 인프라.

사용법:
    dartlab channel              # devtunnel 자동 (winget 설치 + GitHub 인증 + 영구 URL)
    dartlab channel --port 9000  # 포트 변경
    dartlab channel --reset      # 저장된 tunnel 삭제 후 재생성

자동화 흐름:
    1. devtunnel CLI 자동 설치 (없으면 winget)
    2. GitHub 인증 (1회만, 브라우저 자동 오픈)
    3. tunnel 자동 생성 또는 재사용 (영구 URL)
    4. anonymous access 자동 등록 (폰에서 인증 없이 접근)
    5. host 백그라운드 시작
    6. dartlab 서버 시작 (미들웨어 비활성)
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

# dartlab 컬러 팔레트
from dartlab.cli.brand import CLR, CLR_ACCENT, CLR_MUTED

_PR = CLR
_AC = CLR_ACCENT
_TM = CLR_MUTED
_TX = "#cdd6f4"

_CONFIG_PATH = Path.home() / ".dartlab" / "channel.json"


def configure_parser(subparsers) -> None:
    """channel 서브커맨드 등록."""
    parser = subparsers.add_parser(
        "channel",
        help="외부 공유 채널 (DevTunnels 기본)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8400,
        help="포트 번호 (기본: 8400)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="바인딩 호스트 (기본: 0.0.0.0)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="모든 사용자 확인을 자동 승인",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="저장된 devtunnel state 삭제 후 새로 생성",
    )
    # 메시징 봇
    parser.add_argument("--telegram", metavar="TOKEN", help="Telegram 봇 토큰")
    parser.add_argument("--slack", metavar="BOT_TOKEN", help="Slack 봇 토큰")
    parser.add_argument("--slack-app-token", metavar="APP_TOKEN", help="Slack 앱 토큰")
    parser.add_argument("--discord", metavar="TOKEN", help="Discord 봇 토큰")
    parser.set_defaults(handler=run)


# ── QR ──────────────────────────────────────────────────────────────────


def _ensure_qrcode() -> bool:
    """qrcode 패키지가 없으면 설치 여부를 묻는다."""
    try:
        import qrcode  # noqa: F401

        return True
    except ImportError:
        pass

    print("\n  QR 코드 출력에 qrcode 패키지가 필요합니다.")
    try:
        answer = input("  설치하시겠습니까? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if answer not in ("", "y", "yes"):
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "qrcode"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  qrcode 설치 실패. QR 코드 없이 계속합니다.", file=sys.stderr)
        return False
    print("  설치 완료!")
    return True


def _render_qr(url: str) -> str:
    """URL을 QR 코드 ASCII로 렌더링."""
    import qrcode  # type: ignore[import-untyped]

    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()


# ── 출력 패널 ────────────────────────────────────────────────────────────


def _print_channel_info(*, tunnel_url: str, has_qr: bool) -> None:
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    from dartlab.cli.services.output import get_console

    console = get_console()

    info = Table.grid(padding=(0, 2))
    info.add_column(style=f"bold {_TM}", justify="right")
    info.add_column(style=f"bold {_TX}")

    info.add_row("URL", tunnel_url)
    info.add_row("Backend", "Microsoft DevTunnels (영구)")
    info.add_row("미들웨어", "비활성 — 토큰 없이 직접 접근")

    group_items = []
    if has_qr:
        try:
            qr_text = _render_qr(tunnel_url)
            group_items.append(Text.from_ansi(qr_text))
        except (ImportError, OSError):
            pass
    group_items.append(info)

    guide = Text()
    guide.append("\n폰 사용법:\n", style=f"bold {_AC}")
    guide.append("  1. 폰 Chrome에 위 URL 입력 (또는 QR 스캔)\n", style=_TM)
    guide.append("  2. anti-phishing 페이지가 뜨면 Continue 클릭\n", style=_TM)
    guide.append("  3. 끝.\n", style=_TM)
    group_items.append(guide)

    footer = Text()
    footer.append("\nCtrl+C", style=f"bold {_TX}")
    footer.append(" 로 종료", style=_TM)
    group_items.append(footer)

    panel = Panel(
        Group(*group_items),
        title="[bold]DartLab Channel[/]",
        border_style=_PR,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


# ── 메시징 어댑터 ────────────────────────────────────────────────────────


def _start_messaging_adapters(args) -> list:
    """CLI 인자에 따라 메시징 어댑터를 백그라운드로 시작한다."""
    import threading

    adapters = []

    if getattr(args, "telegram", None):
        from dartlab.channel.adapters import create_adapter

        adapter = create_adapter("telegram", token=args.telegram)
        adapters.append(adapter)
        t = threading.Thread(target=_run_adapter, args=(adapter,), daemon=True)
        t.start()
        print("  Telegram 봇 시작됨")

    if getattr(args, "slack", None):
        app_token = getattr(args, "slack_app_token", None)
        if not app_token:
            print("  Slack은 --slack-app-token 이 필요합니다 (Socket Mode)", file=sys.stderr)
        else:
            from dartlab.channel.adapters import create_adapter

            adapter = create_adapter("slack", bot_token=args.slack, app_token=app_token)
            adapters.append(adapter)
            t = threading.Thread(target=_run_adapter, args=(adapter,), daemon=True)
            t.start()
            print("  Slack 봇 시작됨")

    if getattr(args, "discord", None):
        from dartlab.channel.adapters import create_adapter

        adapter = create_adapter("discord", token=args.discord)
        adapters.append(adapter)
        t = threading.Thread(target=_run_adapter, args=(adapter,), daemon=True)
        t.start()
        print("  Discord 봇 시작됨")

    return adapters


def _run_adapter(adapter) -> None:
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(adapter.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


# ── 메인 ────────────────────────────────────────────────────────────────


def run(args) -> int:
    """DevTunnels으로 dartlab을 외부에 공개한다."""
    port = args.port
    host = args.host

    # --reset: 저장된 devtunnel state 삭제
    if args.reset:
        state_file = Path.home() / ".dartlab" / "devtunnel-state.json"
        if state_file.exists():
            state_file.unlink()
            print("  저장된 devtunnel state 삭제됨.")
        else:
            print("  저장된 state가 없습니다.")
        return 0

    # 서버 의존성 체크
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print("\n  [오류] 서버 패키지가 설치되지 않았습니다.")
        print("  설치: pip install --upgrade dartlab\n")
        return 1

    # CORS 전체 허용 (devtunnel URL 등 외부 origin 통과)
    os.environ["DARTLAB_CHANNEL"] = "1"

    # DevTunnels 셋업
    print("\n  Channel 시작 — Microsoft DevTunnels")
    try:
        from dartlab.channel.devtunnel import DevTunnelSetupError, setup_devtunnel
    except (ImportError, ModuleNotFoundError) as exc:
        print(f"\n  DevTunnel 모듈 로드 실패: {exc}", file=sys.stderr)
        return 1

    try:
        tunnel_url, host_proc = setup_devtunnel(port=port, auto_yes=args.yes)
    except DevTunnelSetupError as exc:
        print(f"\n  DevTunnels 셋업 실패: {exc}", file=sys.stderr)
        return 1

    print(f"\n  ✓ Channel 활성: {tunnel_url}")

    # 포트 확보
    from dartlab.server import ensure_port

    status = ensure_port(port)
    if status == "failed":
        return 1

    # ── 접속 정보 출력 ──
    has_qr = _ensure_qrcode()
    _print_channel_info(tunnel_url=tunnel_url, has_qr=has_qr)

    # 메시징 어댑터 시작 (백그라운드)
    adapters = _start_messaging_adapters(args)

    # 서버 시작 (미들웨어 비활성 — DARTLAB_TUNNEL 안 켬)
    from dartlab.server import run_server

    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        pass
    finally:
        for adapter in adapters:
            print(f"\n  {adapter.name} 어댑터 종료 중...")
        print("\n  Channel 종료 중...")
        try:
            if host_proc and host_proc.poll() is None:
                host_proc.terminate()
        except (OSError, AttributeError):
            pass
        print("  종료 완료.")

    return 0
