"""recipe_promote.py CLI unit — frontmatter 조작 + scorecard 게이트 + force 우회.

`feedback_no_graph_regression.md` 준수: 본 CLI 가 status frontmatter 단독 권한.
다른 도구가 자동으로 status 를 바꾸지 않는다는 계약 검증.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "src" / "dartlab" / "skills" / "recipePromote.py"


def _loadCli():
    spec = importlib.util.spec_from_file_location("recipe_promote_cli", CLI_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["recipe_promote_cli"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cli_module():
    return _loadCli()


def _writeRecipe(
    path: Path,
    status: str = "unverified",
    *,
    extra_fields: str = "",
    skill_id: str = "recipes.fundamental.quality.cliProbe",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "---\n"
        f"id: {skill_id}\n"
        "title: CLI 검증 probe\n"
        "category: recipes\n"
        "kind: recipe\n"
        f"status: {status}\n"
        f"{extra_fields}"
        "---\n\n"
        "## 공개 호출 방식\n\n"
        "```python\nimport dartlab\n```\n\n"
        "## 호출 동작\n\n1. probe\n"
    )
    path.write_text(body, encoding="utf-8")


def test_set_status_replaces_status_line_preserves_other_fields(tmp_path: Path, cli_module):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="unverified", extra_fields="purpose: 테스트\nlinkedSkills:\n  - engines.x\n")

    cli_module._setStatus(path, "verified", validatedAt="2026-05-10")
    text = path.read_text(encoding="utf-8")
    assert "status: verified" in text
    assert "validatedAt: '2026-05-10'" in text
    # 다른 frontmatter 필드 보존.
    assert "purpose: 테스트" in text
    assert "engines.x" in text
    # 본문 보존.
    assert "## 공개 호출 방식" in text


def test_set_status_inserts_validated_at_when_missing(tmp_path: Path, cli_module):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="unverified")
    cli_module._setStatus(path, "verified", validatedAt="2026-05-10")
    text = path.read_text(encoding="utf-8")
    assert "validatedAt: '2026-05-10'" in text


def test_set_deprecated_writes_reason(tmp_path: Path, cli_module):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="verified")
    cli_module._setDeprecated(path, "schema drift > 50%")
    text = path.read_text(encoding="utf-8")
    assert "status: deprecated" in text
    assert "deprecatedAt:" in text
    assert "deprecatedReason:" in text
    assert "schema drift > 50%" in text


def test_promote_rejects_when_scorecard_fails(tmp_path: Path, cli_module, monkeypatch):
    """scorecard.meetsThresholds=False 면 promote 거부 (return 1)."""
    path = tmp_path / "credit" / "distressDual.md"
    _writeRecipe(path, status="unverified", skill_id="recipes.credit.distressDual")
    # RECIPE_DIR 을 tmp 로 모킹 (cli_module 의 path resolver 가 본 디렉터리 사용).
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "_recipeMeta", lambda sid: {"status": "unverified"})
    # loadRuns / computeScorecard 는 빈 runs → meetsThresholds=False.
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path / "runs"))

    args = type("Args", (), {})()
    args.skillId = "recipes.credit.distressDual"
    args.toStatus = "verified"
    args.force = False
    rc = cli_module.cmdPromote(args)
    assert rc == 1
    # 파일 status 변하지 않았는지 확인.
    text = path.read_text(encoding="utf-8")
    assert "status: unverified" in text


def test_promote_with_force_bypasses_scorecard(tmp_path: Path, cli_module, monkeypatch):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="unverified")
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "_recipeMeta", lambda sid: {"status": "unverified"})
    monkeypatch.setenv("DARTLAB_RECIPE_RUNS_DIR", str(tmp_path / "runs"))

    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    args.toStatus = "verified"
    args.force = True
    rc = cli_module.cmdPromote(args)
    assert rc == 0
    text = path.read_text(encoding="utf-8")
    assert "status: verified" in text


def test_promote_noop_when_already_target_status(tmp_path: Path, cli_module, monkeypatch):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="verified")
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "_recipeMeta", lambda sid: {"status": "verified"})

    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    args.toStatus = "verified"
    args.force = False
    rc = cli_module.cmdPromote(args)
    assert rc == 0


def test_promote_rejects_unknown_transition_without_force(tmp_path: Path, cli_module, monkeypatch):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="verified")
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)
    monkeypatch.setattr(cli_module, "_recipeMeta", lambda sid: {"status": "verified"})

    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    args.toStatus = "curated"
    args.force = False
    rc = cli_module.cmdPromote(args)
    assert rc == 1


def test_deprecate_requires_reason(tmp_path: Path, cli_module, monkeypatch):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="verified")
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)

    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    args.reason = ""
    rc = cli_module.cmdDeprecate(args)
    assert rc == 1


def test_deprecate_marks_status_deprecated(tmp_path: Path, cli_module, monkeypatch):
    path = tmp_path / "fundamental" / "quality" / "cliProbe.md"
    _writeRecipe(path, status="verified")
    monkeypatch.setattr(cli_module, "RECIPE_DIR", tmp_path)

    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    args.reason = "drift > 50%"
    rc = cli_module.cmdDeprecate(args)
    assert rc == 0
    text = path.read_text(encoding="utf-8")
    assert "status: deprecated" in text
    assert "drift > 50%" in text


def test_promote_to_storyboard_requires_verified_or_curated(tmp_path: Path, cli_module, monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "_recipeMeta",
        lambda sid: {"status": "tested"},  # verified 미만 → 거부.
    )
    args = type("Args", (), {})()
    args.skillId = "recipes.fundamental.quality.cliProbe"
    rc = cli_module.cmdPromoteToStoryboard(args)
    assert rc == 1
