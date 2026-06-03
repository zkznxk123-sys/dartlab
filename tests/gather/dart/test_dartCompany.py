"""mirror smoke — dart/openapi/dartCompany.py (split helper).

분할 helper 모듈의 임포트 가능성 + 룰 7 mirror 슬롯 충족.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_import() -> None:
    """clean-interpreter import smoke — pytest 세션 import-order 순환 면역."""
    import subprocess
    import sys

    code = "import dartlab.gather.dart.dartCompany"
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", code], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr
