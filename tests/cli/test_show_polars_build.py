"""M7: showPolarsBuild 진단 스크립트 import + 실행 검증."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_script_runs_clean(capsys):
    """``scripts/dev/showPolarsBuild.py`` main() exit 0, polars/python/platform 라인 포함."""
    repo = Path(__file__).resolve().parent.parent.parent
    scriptPath = repo / "scripts" / "dev" / "showPolarsBuild.py"
    assert scriptPath.exists(), f"M7 스크립트 부재: {scriptPath}"

    # 동적 import (sys.path 임시 추가)
    sys.path.insert(0, str(scriptPath.parent))
    try:
        # importlib 사용 — module 이름이 hyphen 가능
        import importlib.util

        spec = importlib.util.spec_from_file_location("showPolarsBuild", scriptPath)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # main() 호출 — stdout 캡쳐
        buf = io.StringIO()
        oldStdout = sys.stdout
        sys.stdout = buf
        try:
            rc = module.main()
        finally:
            sys.stdout = oldStdout

        output = buf.getvalue()
        assert rc == 0, f"main() exit {rc} 0 아님. output={output[:500]}"
        assert "polars version" in output
        assert "Allocator" in output
    finally:
        sys.path.pop(0)
