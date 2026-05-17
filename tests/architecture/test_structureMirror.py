"""src ↔ tests 1:1 mirror 검증 — P-트랙 룰 7 게이트.

각 `src/dartlab/providers/X/Y.py` 는 `tests/providers/X/test_Y.py` 슬롯 보유 필수.
각 `src/dartlab/gather/X/Y.py` 는 `tests/gather/X/test_Y.py` 슬롯 보유 필수.

P6 strict: 모든 providers/ src 파일 mirror 보유.
P-G7 점진: gather/ 잔여 미러 누락은 _baselines/gatherStructureMirror.json freeze.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parent.parent.parent
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "structureMirror.json"
_GATHER_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "gatherStructureMirror.json"
_PROVIDERS_SRC = _REPO / "src" / "dartlab" / "providers"
_PROVIDERS_TEST = _REPO / "tests" / "providers"
_GATHER_SRC = _REPO / "src" / "dartlab" / "gather"
_GATHER_TEST = _REPO / "tests" / "gather"


def _providerScope() -> tuple[str, ...]:
    raw = os.environ.get("DARTLAB_PROVIDER_SCOPE", "dart,edgar")
    providers = tuple(p.strip() for p in raw.split(",") if p.strip())
    return providers or ("dart", "edgar")


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"missingMirrors": [], "_note": "P0.5 baseline"}


def _scanSrc(root: Path) -> list[str]:
    """src 폴더의 모든 .py (테스트 가능한 진입점) 식별."""
    if not root.exists():
        return []
    paths: list[str] = []
    for p in root.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        if "__pycache__" in p.parts:
            continue
        # _ prefix 는 룰 5 에서 폐지 — mirror 대상에서도 제외
        if p.name.startswith("_"):
            continue
        rel = p.relative_to(root).as_posix()
        paths.append(rel)
    return sorted(paths)


def _scanProviderSrc() -> list[str]:
    paths: list[str] = []
    for provider in _providerScope():
        providerRoot = _PROVIDERS_SRC / provider
        for srcRel in _scanSrc(providerRoot):
            paths.append(f"{provider}/{srcRel}")
    return sorted(paths)


def _mirrorPath(srcRel: str) -> str:
    """src/dartlab/X/Y/Z.py → tests/X/Y/test_Z.py."""
    parts = srcRel.split("/")
    parts[-1] = "test_" + parts[-1]
    return "/".join(parts)


def test_providers_have_test_mirrors() -> None:
    """모든 providers/X/Y.py 에 tests/providers/X/test_Y.py 슬롯 존재.

    baseline 외 신규 미러 누락만 fail (회귀 가드).
    """
    srcFiles = _scanProviderSrc()
    missing: list[str] = []
    for srcRel in srcFiles:
        mirrorRel = _mirrorPath(srcRel)
        mirrorPath = _PROVIDERS_TEST / mirrorRel
        if not mirrorPath.exists():
            missing.append(srcRel)

    baseline = _loadBaseline(_BASELINE)
    allowed = set(baseline.get("missingMirrors", []))
    new_missing = set(missing) - allowed
    assert not new_missing, (
        f"Mirror 누락 회귀 {len(new_missing)} 건: {list(new_missing)[:10]}... (P6 에서 메우거나 baseline 갱신 필요)"
    )


def test_gather_have_test_mirrors() -> None:
    """모든 gather/X/Y.py 에 tests/gather/X/test_Y.py 슬롯 존재.

    baseline 외 신규 미러 누락만 fail. P-G7 점진 — 잔여는 gatherStructureMirror.json 에 freeze.
    """
    srcFiles = _scanSrc(_GATHER_SRC)
    missing: list[str] = []
    for srcRel in srcFiles:
        mirrorRel = _mirrorPath(srcRel)
        mirrorPath = _GATHER_TEST / mirrorRel
        if not mirrorPath.exists():
            missing.append(srcRel)

    baseline = _loadBaseline(_GATHER_BASELINE)
    allowed = set(baseline.get("missingMirrors", []))
    new_missing = set(missing) - allowed
    assert not new_missing, (
        f"gather mirror 누락 회귀 {len(new_missing)} 건: {list(new_missing)[:10]}... "
        "(P-G7 에서 메우거나 gatherStructureMirror baseline 갱신 필요)"
    )


def test_baseline_file_format() -> None:
    """baseline JSON 형식 검증 (있다면)."""
    for path in (_BASELINE, _GATHER_BASELINE):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "missingMirrors" in data, f"{path.name}: missingMirrors 키 부재"
        assert isinstance(data["missingMirrors"], list), f"{path.name}: missingMirrors 가 list 아님"
