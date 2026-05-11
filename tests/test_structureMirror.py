"""src ↔ tests 1:1 mirror 검증 — P-트랙 룰 7 게이트.

각 `src/dartlab/providers/X/Y.py` 는 `tests/providers/X/test_Y.py` 슬롯 보유 필수.
P6 strict: 모든 providers/ src 파일 mirror 보유.
P0.5 baseline: 현 미러 갭은 _baselines/structureMirror.json 기록 — 회귀만 차단.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "structureMirror.json"
_PROVIDERS_SRC = _REPO / "src" / "dartlab" / "providers"
_PROVIDERS_TEST = _REPO / "tests" / "providers"


def _loadBaseline() -> dict:
    if _BASELINE.exists():
        return json.loads(_BASELINE.read_text(encoding="utf-8"))
    return {"missingMirrors": [], "_note": "P0.5 baseline"}


def _scanProviders() -> list[str]:
    """providers/ 의 모든 .py (테스트 가능한 진입점) 식별."""
    if not _PROVIDERS_SRC.exists():
        return []
    paths: list[str] = []
    for p in _PROVIDERS_SRC.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        if "__pycache__" in p.parts:
            continue
        # _ prefix 는 룰 5 에서 폐지 — mirror 대상에서도 제외
        if p.name.startswith("_"):
            continue
        rel = p.relative_to(_PROVIDERS_SRC).as_posix()
        paths.append(rel)
    return sorted(paths)


def _mirrorPath(srcRel: str) -> str:
    """src/dartlab/providers/X/Y.py → tests/providers/X/test_Y.py."""
    parts = srcRel.split("/")
    parts[-1] = "test_" + parts[-1]
    return "/".join(parts)


def test_providers_have_test_mirrors() -> None:
    """모든 providers/X/Y.py 에 tests/providers/X/test_Y.py 슬롯 존재.

    baseline 외 신규 미러 누락만 fail (회귀 가드).
    """
    srcFiles = _scanProviders()
    missing: list[str] = []
    for srcRel in srcFiles:
        mirrorRel = _mirrorPath(srcRel)
        mirrorPath = _PROVIDERS_TEST / mirrorRel
        if not mirrorPath.exists():
            missing.append(srcRel)

    baseline = _loadBaseline()
    allowed = set(baseline.get("missingMirrors", []))
    new_missing = set(missing) - allowed
    assert not new_missing, (
        f"Mirror 누락 회귀 {len(new_missing)} 건: {list(new_missing)[:10]}... (P6 에서 메우거나 baseline 갱신 필요)"
    )


def test_baseline_file_format() -> None:
    """baseline JSON 형식 검증 (있다면)."""
    if not _BASELINE.exists():
        pytest.skip("baseline 미존재 — P0.5 첫 실행")
    data = json.loads(_BASELINE.read_text(encoding="utf-8"))
    assert "missingMirrors" in data
    assert isinstance(data["missingMirrors"], list)
