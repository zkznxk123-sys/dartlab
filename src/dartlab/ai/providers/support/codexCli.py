"""Codex CLI introspection and execution helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

_CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
_DEFAULT_CODEX_MODELS = [
    "gpt-5.5",
    "gpt-5.5-codex",
    "gpt-5.4",
    "gpt-5.4-codex",
    "gpt-5.3",
    "gpt-5.3-codex",
    "gpt-5.2",
    "gpt-5.2-codex",
    "gpt-5.1",
    "gpt-5.1-codex",
    "gpt-5.1-codex-mini",
    "o3",
    "o4-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
]
_CODING_KEYWORDS = (
    "코드",
    "코딩",
    "구현",
    "수정",
    "패치",
    "리팩터링",
    "버그",
    "테스트",
    "파일",
    "함수",
    "클래스",
    "모듈",
    "컴포넌트",
    "diff",
    "patch",
    "fix",
    "implement",
    "refactor",
    "edit",
    "write code",
    "update file",
)
_CODE_FILE_HINT = re.compile(r"\.(py|svelte|js|ts|tsx|jsx|json|toml|md|yml|yaml|css|html)\b", re.IGNORECASE)


def codexPath() -> str | None:
    """Resolve Codex CLI executable."""
    return shutil.which("codex")


def _runCodexMetaCommand(*args: str, timeout: int = 10) -> tuple[int, str, str] | None:
    exe = codexPath()
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return None
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def loadCodexConfig() -> dict[str, Any]:
    """loadCodexConfig — TODO 한국어 동작 설명."""
    if not _CODEX_CONFIG_PATH.exists():
        return {}
    try:
        with _CODEX_CONFIG_PATH.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def getCodexConfiguredModel() -> str | None:
    """getCodexConfiguredModel — TODO 한국어 동작 설명."""
    data = loadCodexConfig()
    root_model = data.get("model")
    if isinstance(root_model, str) and root_model.strip():
        return root_model.strip()

    profile_name = data.get("profile") or data.get("default_profile")
    profiles = data.get("profiles")
    if isinstance(profile_name, str) and isinstance(profiles, dict):
        profile = profiles.get(profile_name)
        if isinstance(profile, dict):
            profile_model = profile.get("model")
            if isinstance(profile_model, str) and profile_model.strip():
                return profile_model.strip()

    if isinstance(profiles, dict):
        for profile in profiles.values():
            if isinstance(profile, dict):
                profile_model = profile.get("model")
                if isinstance(profile_model, str) and profile_model.strip():
                    return profile_model.strip()

    return None


def getCodexModelCatalog() -> list[str]:
    """getCodexModelCatalog — TODO 한국어 동작 설명."""
    models: list[str] = []
    configured = getCodexConfiguredModel()
    if configured:
        models.append(configured)

    models.extend(_DEFAULT_CODEX_MODELS)

    if not models:
        models.append("gpt-4.1")

    seen: set[str] = set()
    unique: list[str] = []
    for model in models:
        if model and model not in seen:
            seen.add(model)
            unique.append(model)
    return unique


def _extractCommands(helpText: str) -> list[str]:
    helpText = helpText if isinstance(helpText, str) else str(helpText)
    commands: list[str] = []
    in_commands = False
    for line in helpText.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("Commands:"):
            in_commands = True
            continue
        if not in_commands:
            continue
        if stripped.startswith("Arguments:") or stripped.startswith("Options:"):
            break
        if not line.startswith("  "):
            continue
        token = stripped.split()[0]
        if token:
            commands.append(token)
    return commands


def _extractSandboxModes(helpText: str) -> list[str]:
    helpText = helpText if isinstance(helpText, str) else str(helpText)
    match = re.search(r"possible values:\s*([^\]]+)", helpText)
    if not match:
        return []
    values = match.group(1)
    return [value.strip() for value in values.split(",") if value.strip()]


def _parseLoginStatus(stdout: str, stderr: str, returncode: int) -> tuple[bool, str | None, str | None]:
    text = (stdout or stderr or "").strip()
    lowered = text.lower()

    if returncode != 0:
        return False, None, text or None

    authenticated = "logged in" in lowered or "authenticated" in lowered
    auth_mode = None
    if "chatgpt" in lowered:
        auth_mode = "chatgpt"
    elif "api key" in lowered or "api-key" in lowered:
        auth_mode = "api_key"

    return authenticated, auth_mode, text or None


def inspectCodexCli() -> dict[str, Any]:
    """inspectCodexCli — TODO 한국어 동작 설명."""
    result: dict[str, Any] = {
        "installed": False,
        "version": None,
        "configuredModel": getCodexConfiguredModel(),
        "authenticated": False,
        "authMode": None,
        "loginStatus": None,
        "commands": [],
        "execCommands": [],
        "sandboxModes": [],
        "supportsLogin": False,
        "supportsLogout": False,
        "supportsJson": False,
        "supportsWorkspaceWrite": False,
        "supportsDangerFullAccess": False,
        "supportsMcp": False,
        "supportsReview": False,
        "supportsApply": False,
    }

    version_info = _runCodexMetaCommand("--version")
    if version_info is None:
        return result

    returncode, stdout, _stderr = version_info
    if returncode != 0:
        return result

    result["installed"] = True
    result["version"] = stdout or None

    root_help = _runCodexMetaCommand("--help")
    if root_help is not None and root_help[0] == 0:
        helpText = root_help[1]
        commands = _extractCommands(helpText)
        result["commands"] = commands
        result["supportsLogin"] = "login" in commands
        result["supportsLogout"] = "logout" in commands
        result["supportsMcp"] = "mcp" in commands
        result["supportsReview"] = "review" in commands
        result["supportsApply"] = "apply" in commands

    login_status = _runCodexMetaCommand("login", "status")
    if login_status is not None:
        authenticated, auth_mode, status_text = _parseLoginStatus(*login_status[1:], login_status[0])
        result["authenticated"] = authenticated
        result["authMode"] = auth_mode
        result["loginStatus"] = status_text

    exec_help = _runCodexMetaCommand("exec", "--help")
    if exec_help is not None and exec_help[0] == 0:
        helpText = exec_help[1]
        result["execCommands"] = _extractCommands(helpText)
        sandbox_modes = _extractSandboxModes(helpText)
        result["sandboxModes"] = sandbox_modes
        result["supportsWorkspaceWrite"] = "workspace-write" in sandbox_modes
        result["supportsDangerFullAccess"] = "danger-full-access" in sandbox_modes
        result["supportsJson"] = "--json" in helpText

    return result


def logoutCodexCli(timeout: int = 15) -> None:
    """logoutCodexCli — TODO 한국어 동작 설명."""
    info = inspectCodexCli()
    if not info.get("installed"):
        raise FileNotFoundError("Codex CLI가 설치되어 있지 않습니다.")

    result = _runCodexMetaCommand("logout", timeout=timeout)
    if result is None:
        raise RuntimeError("Codex CLI 로그아웃 명령을 실행할 수 없습니다.")

    returncode, _stdout, stderr = result
    if returncode != 0:
        raise RuntimeError(stderr or "Codex CLI 로그아웃에 실패했습니다.")


def inferCodexSandbox(messages: list[dict[str, str]], override: str | None = None) -> str:
    """inferCodexSandbox — TODO 한국어 동작 설명."""
    info = inspectCodexCli()
    sandbox_modes = set(info.get("sandboxModes") or [])

    requested = override or os.environ.get("DARTLAB_CODEX_SANDBOX")
    if requested and (not sandbox_modes or requested in sandbox_modes):
        return requested

    userText = "\n".join(m.get("content", "") for m in messages if m.get("role") == "user")
    if _looksLikeCodeTask(userText) and "workspace-write" in sandbox_modes:
        return "workspace-write"
    return "read-only"


def _looksLikeCodeTask(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in _CODING_KEYWORDS):
        return True
    return bool(_CODE_FILE_HINT.search(text))


def buildCodexExecCommand(*, model: str | None = None, sandbox: str = "read-only") -> list[str]:
    """buildCodexExecCommand — TODO 한국어 동작 설명."""
    exe = codexPath() or "codex"
    cmd = [exe, "exec", "-", "--json", "--skip-git-repo-check", "--sandbox", sandbox]
    if model:
        cmd.extend(["--model", model])
    return cmd


def parseCodexJsonl(output: str) -> tuple[str, dict[str, int] | None]:
    """parseCodexJsonl — TODO 한국어 동작 설명."""
    answer = ""
    usage: dict[str, int] = {}

    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        eventType = event.get("type", "")
        if eventType == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                answer = item.get("text", "")
        elif eventType == "turn.completed":
            turn_usage = event.get("usage", {})
            if turn_usage:
                usage["prompt_tokens"] = turn_usage.get("input_tokens")
                usage["completion_tokens"] = turn_usage.get("output_tokens")
                prompt_tokens = usage.get("prompt_tokens") or 0
                completion_tokens = usage.get("completion_tokens") or 0
                if prompt_tokens or completion_tokens:
                    usage["total_tokens"] = prompt_tokens + completion_tokens

    return answer, usage or None


def runCodexExec(
    prompt: str,
    *,
    model: str | None = None,
    sandbox: str = "read-only",
    cwd: str | None = None,
    timeout: int = 300,
) -> tuple[str, dict[str, int] | None]:
    """runCodexExec — TODO 한국어 동작 설명."""
    cmd = buildCodexExecCommand(model=model, sandbox=sandbox)

    try:
        result = subprocess.run(
            cmd,
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            shell=False,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"Codex CLI 응답 시간 초과 ({timeout}초)") from exc

    if result.returncode != 0:
        raw_err = result.stderr or b""
        stderr = raw_err.decode("utf-8", errors="replace").strip() if isinstance(raw_err, bytes) else raw_err.strip()
        raise RuntimeError(f"Codex CLI 오류 (exit {result.returncode}):\n{stderr}")

    raw_out = result.stdout or b""
    stdout = raw_out.decode("utf-8", errors="replace") if isinstance(raw_out, bytes) else raw_out
    answer, usage = parseCodexJsonl(stdout)
    if not answer:
        raise RuntimeError("Codex CLI에서 응답을 추출할 수 없습니다.")
    return answer, usage
