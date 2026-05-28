"""[ft] optional-dependencies 그룹 + 문서 검증 — 마스터 플랜 v2 트랙 8 PR-T4.

pyproject.toml 의 ft extra 가 정의돼 있고 transformers / peft / trl / datasets / accelerate
6 패키지 등록 확인. 기본 install 에 영향 0 (Phase 3 gate).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _readPyproject() -> dict:
    p = Path(__file__).resolve().parents[3] / "pyproject.toml"
    return tomllib.loads(p.read_text(encoding="utf-8"))


def test_ft_extra_defined() -> None:
    data = _readPyproject()
    extras = data.get("project", {}).get("optional-dependencies", {})
    assert "ft" in extras, "ft optional-dependencies 그룹 누락"


def test_ft_extra_includes_transformers() -> None:
    data = _readPyproject()
    ft = data["project"]["optional-dependencies"]["ft"]
    pkgs = [p.split(";")[0].split(">")[0].split("<")[0].strip() for p in ft]
    assert "transformers" in pkgs


def test_ft_extra_includes_peft_trl() -> None:
    data = _readPyproject()
    ft = data["project"]["optional-dependencies"]["ft"]
    pkgs = [p.split(";")[0].split(">")[0].split("<")[0].strip() for p in ft]
    assert "peft" in pkgs
    assert "trl" in pkgs


def test_ft_extra_includes_datasets_accelerate() -> None:
    data = _readPyproject()
    ft = data["project"]["optional-dependencies"]["ft"]
    pkgs = [p.split(";")[0].split(">")[0].split("<")[0].strip() for p in ft]
    assert "datasets" in pkgs
    assert "accelerate" in pkgs


def test_ft_extra_emscripten_guard() -> None:
    """emscripten 환경 (Pyodide) 에서 차단 — sys_platform marker."""
    data = _readPyproject()
    ft = data["project"]["optional-dependencies"]["ft"]
    transformers_line = next(p for p in ft if p.startswith("transformers"))
    assert "sys_platform != 'emscripten'" in transformers_line


def test_bitsandbytes_linux_only() -> None:
    """bitsandbytes 는 Linux only (Windows / Mac 미지원 회귀 가드)."""
    data = _readPyproject()
    ft = data["project"]["optional-dependencies"]["ft"]
    bnb_line = next((p for p in ft if p.startswith("bitsandbytes")), None)
    assert bnb_line is not None
    assert "sys_platform == 'linux'" in bnb_line


def test_modelChoices_document_exists() -> None:
    p = Path(__file__).resolve().parents[3] / "src" / "dartlab" / "ai" / "training" / "modelChoices.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Qwen2.5-7B" in text
    assert "Apache 2.0" in text


def test_deploymentChoices_document_exists() -> None:
    p = Path(__file__).resolve().parents[3] / "src" / "dartlab" / "ai" / "training" / "deploymentChoices.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Ollama" in text
    assert "vLLM" in text


def test_default_install_no_ft_packages() -> None:
    """기본 dependencies 에 transformers / peft 등 ML 패키지가 들어 있지 않음."""
    data = _readPyproject()
    deps = data["project"].get("dependencies", [])
    base_pkgs = " ".join(deps)
    for ml_pkg in ("transformers", "peft", "trl", "accelerate"):
        # base dependencies 에는 없어야 (ft extra 안에만)
        assert ml_pkg not in base_pkgs, f"{ml_pkg} 가 base dependencies 에 누출"
