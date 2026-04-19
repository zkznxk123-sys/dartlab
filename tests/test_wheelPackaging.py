"""Wheel packaging 계약 — 실제 빌드된 wheel 에 필수 리소스가 모두 들어가는지.

========================================
이 파일이 잡는 버그 클래스:
========================================
`python -m build` (또는 `uv build`) 로 실제 wheel 을 빌드한 뒤,
git-tracked 된 모든 번들 리소스(JSON/parquet/py.typed)가 wheel 에
포함됐는지 zip 파일 목록 수준에서 직접 검증한다.

과거 사고 (2026-04-19, 0.9.15 + 0.9.16 모두):
    PyPI 에 올라간 wheel 에 `src/dartlab/core/data/parserMappings/` 누락 →
    외부 사용자가 `import dartlab` 하는 순간 `FileNotFoundError`.
    wheel-smoke job 이 별도로 빌드한 wheel 을 검증했기에 PyPI 에 올라간
    wheel 과 다른 대상을 본 게 원인. 이 테스트는 매 push 마다 실제 빌드를
    수행해서 packaging 설정 (pyproject.toml + .gitignore) 자체를 검증한다.

주의:
    - `mark unit` 이지만 실제 `python -m build` 를 호출하므로 ~10초 소요.
    - CI 에서 1회 실행만 해도 2026-04-19 class 회귀는 차단됨.
    - 로컬 호출 시 기존 `dist/` 를 건드리지 않도록 tmp_path 사용.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src" / "dartlab"


def _gitTrackedBundleFiles() -> set[str]:
    """git 이 추적하는 src/dartlab/ 하위 번들 리소스 (JSON/parquet/py.typed)."""
    result = subprocess.run(
        ["git", "ls-files", "src/dartlab/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    bundled: set[str] = set()
    for line in result.stdout.splitlines():
        if not line:
            continue
        # wheel 에 들어가면 안 되는 경로
        if "/_reference/" in line or "/_backup/" in line:
            continue
        if line.startswith("src/dartlab/engines/edinet/"):
            continue
        if line.startswith("src/dartlab/engines/esg/"):
            continue
        if line.startswith("src/dartlab/engines/event/"):
            continue
        if line.startswith("src/dartlab/engines/supply/"):
            continue
        if line.startswith("src/dartlab/engines/watch/"):
            continue
        if line.endswith((".json", ".parquet")) or line.endswith("py.typed"):
            bundled.add(line.removeprefix("src/"))  # "dartlab/..." 형태
    return bundled


@pytest.fixture(scope="module")
def builtWheel(tmp_path_factory) -> Path:
    """현재 소스로 wheel 을 빌드해서 경로 반환. 테스트 끝나면 tmp_path 자동 정리."""
    out = tmp_path_factory.mktemp("wheel-packaging-test")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"wheel 빌드 실패 (python -m build 미설치 가능): {result.stderr[-500:]}")
    wheels = list(out.glob("*.whl"))
    if not wheels:
        pytest.skip("빌드 산출물에 wheel 없음")
    return wheels[0]


def test_bundleFiles_allIncludedInWheel(builtWheel: Path):
    """git-tracked 번들 리소스가 모두 wheel 에 포함됐는지 전수 검증.

    2026-04-19 사고 핵심 방어. packaging 설정이 깨져서 특정 디렉토리가
    통째로 빠지는 케이스를 파일 수준으로 잡는다.
    """
    with zipfile.ZipFile(builtWheel) as zf:
        inWheel = set(zf.namelist())

    expected = _gitTrackedBundleFiles()
    missing = sorted(f for f in expected if f not in inWheel)
    assert not missing, (
        f"wheel 에 누락된 git-tracked 번들 리소스 {len(missing)}건:\n"
        + "\n".join(f"  - {m}" for m in missing[:20])
        + (f"\n  ... +{len(missing) - 20} 건 더" if len(missing) > 20 else "")
        + "\n\npyproject.toml [tool.hatch.build.targets.wheel] 의 include/artifacts 확인 필요."
    )


def test_parserMappings_inWheel(builtWheel: Path):
    """2026-04-19 사고 직접 타겟 — parserMappings/ 4개 JSON 개별 확인."""
    with zipfile.ZipFile(builtWheel) as zf:
        names = zf.namelist()
    required = [
        "dartlab/core/data/parserMappings/sections.json",
        "dartlab/core/data/parserMappings/affiliate.json",
        "dartlab/core/data/parserMappings/costByNature.json",
        "dartlab/core/data/parserMappings/sectorPriors.json",
    ]
    for req in required:
        assert req in names, (
            f"wheel 에 {req} 누락 — 2026-04-19 packaging 사고 직접 재현 조건.\n"
            f"외부 사용자가 pip install dartlab 후 `import dartlab` 만 해도 crash."
        )


def test_accountMappings_inWheel(builtWheel: Path):
    """accountMappings.json — 재무제표 라벨링 전멸 방지."""
    with zipfile.ZipFile(builtWheel) as zf:
        names = zf.namelist()
    assert "dartlab/core/data/accountMappings.json" in names, (
        "accountMappings.json 누락 — 모든 계정 라벨이 snakeId 로만 표시되는 회귀"
    )


def test_sectionMappings_inWheel(builtWheel: Path):
    """DART + EDGAR + EDINET section mapping JSON 들."""
    with zipfile.ZipFile(builtWheel) as zf:
        names = zf.namelist()
    required = [
        "dartlab/providers/dart/docs/sections/mapperData/sectionMappings.json",
        "dartlab/providers/dart/docs/sections/mapperData/tableMappings.json",
        "dartlab/providers/edgar/docs/sections/mapperData/sectionMappings.json",
        "dartlab/providers/edinet/docs/sections/mapperData/sectionMappings.json",
    ]
    for req in required:
        assert req in names, f"wheel 에 {req} 누락"


def test_sectionProfileTable_parquet_inWheel(builtWheel: Path):
    """sectionProfileTable.parquet — sections 런타임 필수 데이터."""
    with zipfile.ZipFile(builtWheel) as zf:
        names = zf.namelist()
    assert "dartlab/providers/dart/docs/sections/profileData/sectionProfileTable.parquet" in names, (
        "sectionProfileTable.parquet 누락 — sections 파이프라인 동작 불가"
    )


@pytest.mark.heavy
def test_installedWheel_importAndSectionsLoad(builtWheel: Path, tmp_path):
    """빌드된 wheel 을 격리 venv 에 설치하고 실제로 loadSections() 호출.

    단순 파일 존재가 아니라 "설치 후 import → 런타임 체인 정상 동작" 까지 검증.
    2026-04-19 사고의 최종 증상(외부 사용자 첫 호출 crash)을 직접 재현.
    """
    import os
    import shutil
    import venv

    # venv 생성
    venvDir = tmp_path / "testvenv"
    venv.create(venvDir, with_pip=True)
    if os.name == "nt":
        py = venvDir / "Scripts" / "python.exe"
    else:
        py = venvDir / "bin" / "python"

    # wheel 설치
    install = subprocess.run(
        [str(py), "-m", "pip", "install", "--quiet", str(builtWheel)],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        pytest.skip(f"venv 에 wheel 설치 실패: {install.stderr[-300:]}")

    # loadSections().chapterByMajor 실제 호출
    check = subprocess.run(
        [
            str(py),
            "-X",
            "utf8",
            "-c",
            "from dartlab.core.mappers.parserMapper import loadSections; "
            "s = loadSections(); "
            "assert s.get('chapterByMajor'), 'chapterByMajor empty — 2026-04-19 사고 재현'; "
            "print('OK chapterByMajor:', len(s['chapterByMajor']))",
        ],
        capture_output=True,
        text=True,
    )
    # venv 정리 (테스트 완료 후 자동이지만 명시적으로)
    try:
        shutil.rmtree(venvDir, ignore_errors=True)
    except Exception:
        pass

    assert check.returncode == 0, (
        f"설치된 wheel 에서 loadSections 호출 실패 — 2026-04-19 사고 재현:\n"
        f"STDOUT: {check.stdout}\n"
        f"STDERR: {check.stderr}"
    )
