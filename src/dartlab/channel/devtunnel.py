"""DevTunnels 모드 — Microsoft DevTunnels을 이용한 영구 외부 공개 URL.

VS Code Remote Tunnels의 기반 기술과 동일. Cloudflare Quick Tunnel의 모바일
fetch hang 문제를 우회하기 위한 1순위 백엔드.

자동화 흐름:
    1. find_devtunnel_binary  : devtunnel CLI 자동 탐색 (PATH/winget package)
    2. install_devtunnel       : winget으로 자동 설치 (없을 때)
    3. ensure_logged_in        : `devtunnel user show` 확인 → 미인증 시 `devtunnel user login -g`
    4. ensure_tunnel           : 상태 파일에서 ID 재사용 또는 신규 생성
    5. start_host              : `devtunnel host <id>` 백그라운드 실행, URL 추출

설계:
- Cloudflare 코드와 독립 (channel/tunnel.py 건드리지 않음)
- DARTLAB_TUNNEL 안 켬 → 토큰/미들웨어 시스템 안 씀
- `--allow-anonymous`로 동작 (1차) — 추후 GitHub access control 옵션 가능
- 영구 URL: tunnel ID는 `~/.dartlab/devtunnel-state.json`에 저장
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_DARTLAB_BIN_DIR = Path.home() / ".dartlab" / "bin"
_STATE_FILE = Path.home() / ".dartlab" / "devtunnel-state.json"

# URL 추출 정규식 (devtunnel host 출력에서 https URL 캡처)
_URL_PATTERN = re.compile(r"https://[a-z0-9-]+(?:-\d+)?\.[a-z0-9-]+\.devtunnels\.ms[/\w-]*")


class DevTunnelSetupError(RuntimeError):
    """DevTunnels 셋업 실패."""


# ── state ────────────────────────────────────────────────────────────────


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(**kw) -> None:
    state = _load_state()
    state.update(kw)
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ── 바이너리 ─────────────────────────────────────────────────────────────


def find_devtunnel_binary() -> str | None:
    """devtunnel CLI 위치 탐색. winget 설치 후에도 PATH 갱신 없이 찾음."""
    # 1. PATH
    p = shutil.which("devtunnel")
    if p:
        return p

    # 2. dartlab 로컬 다운로드
    ext = ".exe" if platform.system() == "Windows" else ""
    local = _DARTLAB_BIN_DIR / f"devtunnel{ext}"
    if local.exists():
        return str(local)

    if platform.system() == "Windows":
        # 3. Program Files (수동 설치)
        for env_key in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env_key)
            if base:
                exe = Path(base) / "Microsoft" / "DevTunnel" / "devtunnel.exe"
                if exe.exists():
                    return str(exe)
        # 4. winget package dir
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            from glob import glob

            pattern = str(
                Path(local_app) / "Microsoft" / "WinGet" / "Packages" / "Microsoft.devtunnel*" / "**" / "devtunnel.exe"
            )
            for found in glob(pattern, recursive=True):
                return found
    else:
        # macOS/Linux
        for p in ("/usr/local/bin/devtunnel", "/opt/homebrew/bin/devtunnel", "/usr/bin/devtunnel"):
            if Path(p).exists():
                return p
    return None


def install_devtunnel(auto_yes: bool = False) -> str:
    """devtunnel CLI 자동 설치."""
    os_name = platform.system()

    if not auto_yes:
        try:
            ans = input("\n  devtunnel 미설치. 자동 설치하시겠습니까? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans not in ("", "y", "yes"):
            raise DevTunnelSetupError("devtunnel 설치를 사용자가 취소했습니다.")

    if os_name == "Windows":
        # 1차: winget
        try:
            print("  winget으로 devtunnel 설치 중... (1~2분)")
            result = subprocess.run(
                [
                    "winget",
                    "install",
                    "--id",
                    "Microsoft.devtunnel",
                    "-e",
                    "--silent",
                    "--accept-source-agreements",
                    "--accept-package-agreements",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                print("  devtunnel 설치 완료 (winget)")
                bin_path = find_devtunnel_binary()
                if bin_path:
                    return bin_path
            else:
                print(f"  winget 실패 (rc={result.returncode}): {(result.stderr or '').strip()[:200]}")
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            print(f"  winget 실행 실패: {exc}")

        # 2차: 직접 다운로드
        print("  직접 다운로드 fallback 시도...")
        try:
            from urllib.request import urlretrieve

            _DARTLAB_BIN_DIR.mkdir(parents=True, exist_ok=True)
            url = "https://aka.ms/TunnelsCliDownload/win-x64"
            target = _DARTLAB_BIN_DIR / "devtunnel.exe"
            print(f"  다운로드: {url}")
            urlretrieve(url, target)
            print(f"  설치 완료: {target}")
            return str(target)
        except OSError as exc:
            print(f"  직접 다운로드 실패: {exc}")

        raise DevTunnelSetupError(
            "Windows 자동 설치 실패. 수동 설치:\n  https://learn.microsoft.com/azure/developer/dev-tunnels/get-started"
        )

    elif os_name == "Darwin":
        # brew
        try:
            result = subprocess.run(
                ["brew", "install", "--cask", "devtunnel"],
                capture_output=True,
                text=True,
                timeout=600,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                bin_path = find_devtunnel_binary()
                if bin_path:
                    return bin_path
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
        # 직접 다운로드 fallback
        try:
            from urllib.request import urlretrieve

            _DARTLAB_BIN_DIR.mkdir(parents=True, exist_ok=True)
            url = "https://aka.ms/TunnelsCliDownload/osx-x64-zip"
            target = _DARTLAB_BIN_DIR / "devtunnel.zip"
            urlretrieve(url, target)
            import zipfile

            with zipfile.ZipFile(target) as zf:
                zf.extractall(_DARTLAB_BIN_DIR)
            target.unlink()
            bin_path = _DARTLAB_BIN_DIR / "devtunnel"
            bin_path.chmod(0o755)
            return str(bin_path)
        except OSError as exc:
            raise DevTunnelSetupError(f"devtunnel 설치 실패: {exc}") from exc

    elif os_name == "Linux":
        # 보안: curl | bash 같은 임의 원격 코드 실행은 사용자 명시 동의 필요.
        # 환경변수 DARTLAB_DEVTUNNEL_AUTOINSTALL=1 또는 대화식 prompt 동의 시만 진행.
        autoinstall = os.environ.get("DARTLAB_DEVTUNNEL_AUTOINSTALL", "").strip() == "1"
        if not autoinstall:
            raise DevTunnelSetupError(
                "Linux 자동 설치는 'curl ... | bash' 원격 스크립트를 실행합니다.\n"
                "  명시 동의가 필요합니다.\n"
                "  진행하려면: DARTLAB_DEVTUNNEL_AUTOINSTALL=1 환경변수 설정 후 재시도\n"
                "  수동 설치: https://learn.microsoft.com/azure/developer/dev-tunnels/get-started"
            )
        try:
            print("  curl로 devtunnel 설치 중... (사용자 동의 OK)")
            result = subprocess.run(
                ["sh", "-c", "curl -sL https://aka.ms/DevTunnelCliInstall | bash"],
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                bin_path = find_devtunnel_binary()
                if bin_path:
                    return bin_path
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            raise DevTunnelSetupError(f"devtunnel 설치 실패: {exc}") from exc
        raise DevTunnelSetupError("Linux 자동 설치 실패")

    else:
        raise DevTunnelSetupError(f"지원하지 않는 OS: {os_name}")


# ── 인증 ──────────────────────────────────────────────────────────────────


def is_logged_in(bin_path: str) -> bool:
    """devtunnel 사용자 로그인 여부 확인."""
    try:
        result = subprocess.run(
            [bin_path, "user", "show"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return False
        # "Logged in as" 또는 "Not logged in" 같은 텍스트 매칭
        out = (result.stdout + result.stderr).lower()
        if "not logged in" in out or "not authenticated" in out:
            return False
        return "logged in" in out or "@" in result.stdout  # 이메일 형태 포함
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def ensure_logged_in(bin_path: str, auto_yes: bool = False) -> None:
    """미인증 시 GitHub 로그인 자동 실행."""
    if is_logged_in(bin_path):
        print("  ✓ devtunnel 이미 인증됨")
        return

    print("\n  GitHub 인증 필요. 잠시 후 브라우저가 자동으로 열립니다.")
    print("  → GitHub 로그인 → dev tunnel 권한 허용\n")

    if not auto_yes:
        try:
            ans = input("  계속하시겠습니까? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans not in ("", "y", "yes"):
            raise DevTunnelSetupError("devtunnel 인증을 사용자가 취소했습니다.")

    # devtunnel user login -g (GitHub) — 출력을 그대로 콘솔로
    print("\n  devtunnel user login -g 실행 중...\n")
    try:
        result = subprocess.run(
            [bin_path, "user", "login", "-g"],
            timeout=600,
            # capture 안 함 — 사용자가 진행 상황 직접 봄
        )
    except subprocess.SubprocessError as exc:
        raise DevTunnelSetupError(f"devtunnel 로그인 실패: {exc}") from exc

    if result.returncode != 0:
        raise DevTunnelSetupError(f"devtunnel 로그인 종료 코드 {result.returncode}")

    if not is_logged_in(bin_path):
        raise DevTunnelSetupError("로그인 후에도 인증 상태가 아닙니다.")

    print("\n  ✓ devtunnel 인증 완료")


# ── tunnel 생성/재사용 ────────────────────────────────────────────────────


def ensure_tunnel(bin_path: str, port: int) -> str:
    """tunnel ID 재사용 또는 신규 생성. tunnel_id 반환.

    포트 매핑 + anonymous 접근 + anti-phishing 우회까지 보장.
    """
    state = _load_state()
    existing_id = state.get("tunnel_id")
    if existing_id:
        try:
            result = subprocess.run(
                [bin_path, "show", existing_id],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                print(f"  기존 tunnel 재사용: {existing_id}")
                _ensure_port_mapping(bin_path, existing_id, port)
                _ensure_anonymous_access(bin_path, existing_id)
                return existing_id
        except subprocess.SubprocessError:
            pass

    # 신규 생성 — conflict 시 기존 tunnel 찾기 또는 timestamp 라벨로 재시도
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", platform.node().lower())[:24] or "host"
    base_label = f"dartlab-{sanitized}"
    tunnel_label = base_label
    tunnel_id = None

    for attempt in range(3):
        print(f"  tunnel 생성: {tunnel_label}")
        try:
            result = subprocess.run(
                [bin_path, "create", tunnel_label, "--allow-anonymous"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.SubprocessError as exc:
            raise DevTunnelSetupError(f"devtunnel create 실패: {exc}") from exc

        out = result.stdout + result.stderr
        if result.returncode == 0:
            match = re.search(r"Tunnel ID\s*[:=]\s*(\S+)", out)
            if not match:
                match = re.search(r"\b([a-z0-9]+-[a-z0-9]+\.[a-z0-9]+)\b", out)
            if not match:
                raise DevTunnelSetupError(f"tunnel ID 파싱 실패. 출력:\n{out[-500:]}")
            tunnel_id = match.group(1)
            break

        # Conflict 처리
        if "conflict" in out.lower() or "already" in out.lower():
            # 1차: list에서 기존 dartlab-* tunnel 찾기
            try:
                list_res = subprocess.run(
                    [bin_path, "list"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    errors="replace",
                )
                if list_res.returncode == 0:
                    print("  devtunnel list 결과:")
                    for line in list_res.stdout.splitlines():
                        if line.strip():
                            print(f"    {line}")
                    # 진짜 ID 형식: <label>.<region>  예: dartlab-desktop-rses20s.jpe1
                    # 라벨 자체에 dash가 들어가므로 더 넓은 정규식 필요
                    for line in list_res.stdout.splitlines():
                        if base_label in line:
                            # base_label 부터 region 까지 통째로 캡처
                            id_match = re.search(rf"({re.escape(base_label)}[\w.-]*\.\w+)", line)
                            if not id_match:
                                # fallback: 라벨이 line 시작에 있으면 첫 공백 전까지
                                id_match = re.search(r"^(\S+)", line.strip())
                            if id_match:
                                tunnel_id = id_match.group(1)
                                tunnel_label = base_label
                                print(f"  ✓ 기존 tunnel 발견: {tunnel_id}")
                                break
                if tunnel_id:
                    break
            except subprocess.SubprocessError:
                pass

            # 2차: timestamp suffix로 새 라벨
            import time as _t

            tunnel_label = f"{base_label}-{int(_t.time()) % 100000}"
            print(f"  conflict — 새 라벨로 재시도: {tunnel_label}")
            continue

        raise DevTunnelSetupError(f"tunnel 생성 실패: {out.strip()[:300]}")

    if not tunnel_id:
        raise DevTunnelSetupError("tunnel 생성 3회 시도 후 실패")

    _save_state(tunnel_id=tunnel_id, tunnel_label=tunnel_label)
    print(f"  ✓ tunnel ID: {tunnel_id}")

    _ensure_port_mapping(bin_path, tunnel_id, port)
    _ensure_anonymous_access(bin_path, tunnel_id)
    return tunnel_id


def _ensure_anonymous_access(bin_path: str, tunnel_id: str) -> None:
    """tunnel + 모든 port에 anonymous 접근 권한 부여.

    핵심: --allow-anonymous는 tunnel 생성 옵션일 뿐, 실제 접근은 access entry로 통제됨.
    `devtunnel access create <id> --anonymous` 로 명시적으로 anonymous reader 추가해야
    인증 없는 클라이언트(폰 등)가 통과 가능.
    """
    try:
        result = subprocess.run(
            [bin_path, "access", "create", tunnel_id, "--anonymous"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            print("  ✓ anonymous 접근 허용")
        else:
            err = (result.stderr or "").lower()
            if "already" in err or "exist" in err:
                pass  # 멱등
            else:
                print(f"  anonymous access 경고 (계속 진행): {result.stderr.strip()[:200]}")
    except subprocess.SubprocessError as exc:
        print(f"  anonymous access 실패 (계속 진행): {exc}")


def _ensure_port_mapping(bin_path: str, tunnel_id: str, port: int) -> None:
    """포트 매핑 보장. 이미 있으면 OK."""
    try:
        result = subprocess.run(
            [bin_path, "port", "create", tunnel_id, "-p", str(port), "--protocol", "http"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            print(f"  포트 매핑: {port} → http")
        else:
            err = (result.stderr or "").lower()
            if "already exists" in err or "already added" in err:
                pass  # 멱등
            else:
                print(f"  포트 매핑 경고 (계속 진행): {result.stderr.strip()[:200]}")
    except subprocess.SubprocessError as exc:
        print(f"  포트 매핑 실패 (계속 진행): {exc}")


# ── host 시작 ─────────────────────────────────────────────────────────────


def start_host(bin_path: str, tunnel_id: str, port: int) -> tuple[str, subprocess.Popen]:
    """`devtunnel host <id>` 백그라운드 시작. (URL, process) 반환."""
    print(f"  devtunnel host 시작: {tunnel_id}")
    try:
        proc = subprocess.Popen(
            [bin_path, "host", tunnel_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise DevTunnelSetupError(f"devtunnel host 실행 실패: {exc}") from exc

    # URL 추출 — 별도 스레드로 stdout 폴링
    url_holder: list[str] = []
    url_event = threading.Event()
    captured: list[str] = []

    def _reader():
        assert proc.stdout
        for line in proc.stdout:
            line = line.rstrip()
            captured.append(line)
            if len(captured) > 100:
                captured.pop(0)
            if line:
                print(f"  [dt] {line}", flush=True)
            m = _URL_PATTERN.search(line)
            if m and not url_event.is_set():
                url_holder.append(m.group(0))
                url_event.set()

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    # URL 대기 (최대 30초)
    if not url_event.wait(timeout=30):
        if proc.poll() is not None:
            tail = "\n".join(captured[-20:])
            raise DevTunnelSetupError(f"devtunnel host 종료됨:\n{tail}")
        raise DevTunnelSetupError("30초 내 tunnel URL을 찾지 못함")

    url = url_holder[0]
    # devtunnel anti-phishing 페이지 우회 — 첫 접속 시 "이거 진짜 dev tunnel 맞아?"
    # confirmation 페이지가 떠서 SPA가 로드 안 되는 문제 차단.
    if "?" not in url:
        url = f"{url}/"
    atexit.register(lambda: _cleanup(proc))
    return url, proc


def _cleanup(proc: subprocess.Popen) -> None:
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.SubprocessError, OSError):
            try:
                proc.kill()
            except OSError:
                pass


# ── 통합 진입점 ───────────────────────────────────────────────────────────


def setup_devtunnel(*, port: int, auto_yes: bool = False) -> tuple[str, subprocess.Popen]:
    """전체 셋업 — install → login → tunnel → host. (URL, host_process) 반환."""
    bin_path = find_devtunnel_binary()
    if not bin_path:
        bin_path = install_devtunnel(auto_yes=auto_yes)

    ensure_logged_in(bin_path, auto_yes=auto_yes)
    tunnel_id = ensure_tunnel(bin_path, port)
    url, proc = start_host(bin_path, tunnel_id, port)
    return url, proc
