"""docstring audit target handling tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_FIXTURE_FILE = _REPO / "tests" / "fixtures" / "auditDocstrings" / "docTarget.py"
_FIXTURE_DIR = _FIXTURE_FILE.parent


def _loadScript(name: str):
    script = _REPO / "scripts" / "audit" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("scriptName", ["docstring9Section.py", "docstring4Section.py"])
def testDocstringAuditScansSingleFileTarget(scriptName: str) -> None:
    """단일 파일 target 이 빈 디렉터리처럼 false pass 하지 않는다."""
    module = _loadScript(scriptName)

    fileViolations = module._scan(_FIXTURE_FILE)
    dirViolations = module._scan(_FIXTURE_DIR)

    assert fileViolations
    assert fileViolations == dirViolations
    assert fileViolations[0]["path"] == "tests/fixtures/auditDocstrings/docTarget.py"
    assert fileViolations[0]["function"] == "missingSections"
