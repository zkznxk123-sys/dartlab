"""dartlabGuard.py 얇은 pytest 접점."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def testDartlabGuardStrictJson() -> None:
    """Guard strict JSON 결과가 pass 여야 한다."""
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "tests/audit/dartlabGuard.py",
            "strict",
            "--scope",
            "l0-l15",
            "--providers",
            "dart,edgar",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["status"] == "pass"
    assert payload["summary"]["activeKnownDebt"] == 0
    assert payload["summary"]["protectedCompanyFacadeDebt"] == 19
    active = payload["baseline"]["activeKnownViolations"]
    protected = payload["baseline"]["protectedCompanyFacadeDebt"]
    assert len(active) == 0
    assert len(protected) == 19
    assert all("/company.py" not in item["path"] for item in active)
    assert all(item["path"].endswith("/company.py") for item in protected)
