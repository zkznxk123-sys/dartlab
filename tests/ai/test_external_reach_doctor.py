"""ExternalReachDoctor — read-only route doctor tests."""

from __future__ import annotations

import pytest

from dartlab.ai.tools import externalReachDoctor as mod
from dartlab.ai.tools import registry

pytestmark = pytest.mark.unit


def test_external_reach_doctor_selects_first_ok_backend(monkeypatch):
    monkeypatch.setattr(
        mod,
        "_probeDartlabWebSearch",
        lambda: mod.BackendProbe("warn", "blocked", fixHint="use fallback"),
    )
    monkeypatch.setattr(mod, "_probeDdgHtml", lambda timeout: mod.BackendProbe("ok", "ddg ok"))
    monkeypatch.setattr(mod, "_probeExaMcporter", lambda timeout: mod.BackendProbe("off", "missing"))
    monkeypatch.setattr(mod, "_probeJinaReader", lambda timeout: mod.BackendProbe("ok", "jina ok"))
    monkeypatch.setattr(mod, "_probeGhCli", lambda timeout: mod.BackendProbe("warn", "gh login missing"))
    monkeypatch.setattr(mod, "_probeGithubApi", lambda timeout: mod.BackendProbe("ok", "api ok"))
    monkeypatch.setattr(mod, "_probeGitLsRemote", lambda timeout: mod.BackendProbe("ok", "git ok"))

    result = mod.externalReachDoctor(timeoutSec=3)

    assert result.ok is True
    channels = result.data["channels"]
    assert channels["externalSearch"]["activeBackend"] == "ddgHtml"
    assert channels["externalSearch"]["status"] == "ok"
    assert channels["githubRead"]["activeBackend"] == "githubApi"
    assert channels["webRead"]["activeBackend"] == "jinaReader"


def test_external_reach_doctor_skip_network_keeps_command_probes(monkeypatch):
    calls: list[str] = []

    def fake_run(cmd, *, timeout):
        calls.append(cmd[0])
        if cmd[0] == "gh":
            return "ok", "logged in"
        if cmd[0] == "git":
            return "ok", "abc\tHEAD"
        return "missing", ""

    monkeypatch.setattr(mod, "_runCommand", fake_run)

    result = mod.externalReachDoctor(skipNetwork=True)

    channels = result.data["channels"]
    assert channels["externalSearch"]["activeBackend"] is None
    assert channels["webRead"]["activeBackend"] is None
    assert channels["githubRead"]["activeBackend"] == "ghCli"
    assert calls == ["mcporter", "gh", "git"]


def test_external_reach_doctor_command_allowlist_blocks_write_like_commands():
    with pytest.raises(ValueError):
        mod._assertAllowedCommand(["gh", "auth", "login"])

    blocked_tokens = {"install", "login", "configure", "cookie", "cookies", "write"}
    flattened = " ".join(" ".join(cmd).lower() for cmd in mod.ALLOWED_COMMAND_PROBES)
    assert blocked_tokens.isdisjoint(set(flattened.split()))


def test_external_reach_doctor_registered_as_canonical_tool(monkeypatch):
    monkeypatch.setattr(mod, "_runCommand", lambda cmd, *, timeout: ("missing", ""))

    assert "ExternalReachDoctor" in registry.CANONICAL_TOOL_NAMES
    payload = registry.executeTool("external_reach_doctor", {"skipNetwork": True, "timeoutSec": 1})
    assert "ExternalReachDoctor" in {spec["name"] for spec in registry.toolSpecs()}
    assert payload["data"]["policy"]["readOnly"] is True
