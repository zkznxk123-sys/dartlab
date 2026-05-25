"""wheel 검증 스크립트 — 번들 리소스 + 런타임 체인 통합 검사.

ci.yml 의 wheel-smoke 잡과 publish.yml 의 build 잡이 동일한 검증 로직을 쓰도록
한 곳에 모음. 과거 두 워크플로우가 서로 다른 코드로 wheel 을 검증해서 "CI 는
통과했는데 publish wheel 은 깨진" 사고(2026-04-19) 가 발생한 구조적 원인 제거.

사용법::

    python .github/scripts/verifyWheel.py dist/dartlab-0.9.17-py3-none-any.whl
    python .github/scripts/verifyWheel.py dist/dartlab-0.9.17-py3-none-any.whl --skip-install

옵션::

    --skip-install    격리 venv 설치 단계 생략 (네트워크 제약 환경용).

종료 코드::

    0 성공 / 1 번들 리소스 누락 / 2 런타임 검증 실패 / 3 입력 오류
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

# 필수 번들 리소스 — 2026-04-19 사고 class 직접 방어.
# `tests/audit/test_wheelPackaging.py::test_parserMappings_inWheel` 와 동기화.
_REQUIRED_BUNDLE_FILES = [
    # parserMappings
    "dartlab/providers/data/parserMappings/sections.json",
    "dartlab/providers/data/parserMappings/affiliate.json",
    "dartlab/providers/data/parserMappings/costByNature.json",
    "dartlab/providers/data/parserMappings/sectorPriors.json",
    # reference data
    "dartlab/reference/data/accountMappings.json",
    "dartlab/reference/data/labelSupplements.json",
    "dartlab/providers/data/notesStructure.json",
    "dartlab/reference/data/dalio48Cases.json",
    "dartlab/reference/data/dalioDetailCases.json",
    "dartlab/reference/data/damodaranDefaults.json",
    "dartlab/reference/data/rrCrises800y.json",
    # DART sections runtime
    "dartlab/providers/dart/docs/sections/mapperData/sectionMappings.json",
    "dartlab/providers/dart/docs/sections/mapperData/tableMappings.json",
    "dartlab/providers/dart/docs/sections/profileData/projectionRules.chapterII.json",
    "dartlab/providers/dart/docs/sections/profileData/sectionProfileTable.parquet",
    # EDGAR sections
    "dartlab/providers/edgar/docs/sections/mapperData/sectionMappings.json",
    # EDINET sections
    "dartlab/providers/edinet/docs/sections/mapperData/sectionMappings.json",
]


def checkBundle(whl: Path) -> int:
    """wheel zip 목록에 필수 리소스가 모두 있는지 확인."""
    with zipfile.ZipFile(whl) as z:
        names = set(z.namelist())
    missing = [f for f in _REQUIRED_BUNDLE_FILES if f not in names]
    if missing:
        print("FAIL — wheel 에 필수 리소스 누락 (2026-04-19 사고 class):")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"OK — 번들 리소스 {len(_REQUIRED_BUNDLE_FILES)}개 모두 포함, wheel 총 {len(names)} 파일")
    return 0


def checkRuntime(whl: Path) -> int:
    """격리 venv 에 wheel 설치 후 loadSections() 호출."""
    with tempfile.TemporaryDirectory(prefix="wheel-verify-") as tmp:
        venvDir = Path(tmp) / "venv"
        venv.create(venvDir, with_pip=True)
        py = venvDir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")

        install = subprocess.run(
            [str(py), "-m", "pip", "install", "--quiet", str(whl)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if install.returncode != 0:
            print("FAIL — 격리 venv 에 wheel 설치 실패:")
            print((install.stderr or install.stdout or "")[-800:])
            return 2

        check = subprocess.run(
            [
                str(py),
                "-X",
                "utf8",
                "-c",
                (
                    "from dartlab.providers.mappers.parserMapper import loadSections;"
                    " s = loadSections();"
                    " assert s.get('chapterByMajor'), 'chapterByMajor empty';"
                    " print('OK chapterByMajor:', len(s['chapterByMajor']))"
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if check.returncode != 0:
            print("FAIL — 설치된 wheel 에서 loadSections 런타임 체인 실패:")
            print("STDOUT:", check.stdout)
            print("STDERR:", check.stderr)
            return 2
        print(check.stdout.strip())

        smoke = subprocess.run(
            [
                str(py),
                "-X",
                "utf8",
                str(Path(__file__).resolve().parents[2] / "tests" / "audit" / "productSmoke.py"),
                "--suite",
                "quick",
                "--data-mode",
                "empty",
                "--import-mode",
                "installed",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if smoke.returncode != 0:
            print("FAIL — 설치된 wheel 에서 사용자 API quick smoke 실패:")
            print("STDOUT:", smoke.stdout[-4000:])
            print("STDERR:", smoke.stderr[-4000:])
            return 2
        print(smoke.stdout.strip())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="dartlab wheel 검증")
    parser.add_argument("wheel", type=Path, help="검증할 .whl 파일")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="격리 venv 설치 단계 생략 (번들 검증만 수행)",
    )
    args = parser.parse_args()

    whl: Path = args.wheel
    if not whl.exists():
        print(f"FAIL — wheel 파일 없음: {whl}", file=sys.stderr)
        return 3
    if not whl.suffix == ".whl":
        print(f"FAIL — .whl 확장자 아님: {whl}", file=sys.stderr)
        return 3

    print(f"[verify-wheel] {whl}")
    rc = checkBundle(whl)
    if rc != 0:
        return rc

    if args.skip_install:
        print("[verify-wheel] --skip-install 지정 → 런타임 검증 생략")
        return 0

    return checkRuntime(whl)


if __name__ == "__main__":
    sys.exit(main())
