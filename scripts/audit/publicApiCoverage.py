"""공개 API 시나리오 매핑 감사.

이 스크립트는 사용자 표면을 동적으로 읽고, `publicApiScenarios.yml` 이 그
표면을 전부 선언/커버하는지 확인한다. 새 top-level API 또는 scan 축을 추가한
PR이 이 파일을 갱신하지 않으면 실패해야 한다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "scripts" / "audit" / "publicApiScenarios.yml"


def _loadManifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"manifest 형식 오류: {path}")
    return data


def _runtimeSurface() -> dict[str, list[str]]:
    import dartlab
    import dartlab.api as dartlabApi

    return {
        "dartlab_symbols": sorted(dartlab.__all__),
        "dartlab_api_symbols": sorted(dartlabApi.__all__),
        "scan_axes": sorted(dartlab.scan.availableScans()),
    }


def _manifestSurface(manifest: dict[str, Any]) -> dict[str, list[str]]:
    public = manifest.get("public_api", {})
    return {
        "dartlab_symbols": sorted(public.get("dartlab_symbols", [])),
        "dartlab_api_symbols": sorted(public.get("dartlab_api_symbols", [])),
        "scan_axes": sorted(public.get("scan_axes", [])),
        "company_members": sorted(public.get("company_members", [])),
    }


def _coverageTokens(manifest: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    scenarios = manifest.get("scenarios", {})
    if not isinstance(scenarios, dict):
        raise SystemExit("manifest.scenarios 는 dict 여야 합니다")
    for scenarioId, scenario in scenarios.items():
        covers = scenario.get("covers", []) if isinstance(scenario, dict) else []
        if not isinstance(covers, list):
            raise SystemExit(f"{scenarioId}: covers 는 list 여야 합니다")
        tokens.update(str(item) for item in covers)
    return tokens


def _requiredTokens(runtime: dict[str, list[str]], manifest: dict[str, Any]) -> set[str]:
    public = manifest.get("public_api", {})
    companyMembers = public.get("company_members", [])
    return {
        *(f"dartlab.{name}" for name in runtime["dartlab_symbols"]),
        *(f"dartlab.api.{name}" for name in runtime["dartlab_api_symbols"]),
        *(f"scan.axis.{axis}" for axis in runtime["scan_axes"]),
        *(f"Company.{name}" for name in companyMembers),
    }


def _validateWaivers(manifest: dict[str, Any]) -> set[str]:
    today = dt.date.today()
    tokens: set[str] = set()
    for token, waiver in (manifest.get("waivers") or {}).items():
        if not isinstance(waiver, dict):
            raise SystemExit(f"{token}: waiver 는 dict 여야 합니다")
        missing = [field for field in ("owner", "reason", "expires") if not waiver.get(field)]
        if missing:
            raise SystemExit(f"{token}: waiver 필수 필드 누락: {missing}")
        try:
            expires = dt.date.fromisoformat(str(waiver["expires"]))
        except ValueError as exc:
            raise SystemExit(f"{token}: waiver expires 형식 오류: {waiver['expires']!r}") from exc
        if expires < today:
            raise SystemExit(f"{token}: waiver 만료됨 ({expires.isoformat()})")
        tokens.add(str(token))
    return tokens


def _diff(expected: list[str], actual: list[str]) -> list[str]:
    expectedSet = set(expected)
    actualSet = set(actual)
    lines: list[str] = []
    for item in sorted(actualSet - expectedSet):
        lines.append(f"  + runtime only: {item}")
    for item in sorted(expectedSet - actualSet):
        lines.append(f"  - manifest only: {item}")
    return lines


def audit(manifestPath: Path = MANIFEST_PATH) -> int:
    manifest = _loadManifest(manifestPath)
    runtime = _runtimeSurface()
    declared = _manifestSurface(manifest)
    failures: list[str] = []

    for key in ("dartlab_symbols", "dartlab_api_symbols", "scan_axes"):
        diff = _diff(declared[key], runtime[key])
        if diff:
            failures.append(f"[{key}] runtime 과 manifest 불일치\n" + "\n".join(diff))

    covered = _coverageTokens(manifest)
    waived = _validateWaivers(manifest)
    required = _requiredTokens(runtime, manifest)
    missingCoverage = sorted(required - covered - waived)
    if missingCoverage:
        failures.append("[coverage] 시나리오/waiver 없는 공개 표면\n" + "\n".join(f"  - {x}" for x in missingCoverage))

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1

    print(
        "[public-api-coverage] OK "
        f"dartlab={len(runtime['dartlab_symbols'])} "
        f"api={len(runtime['dartlab_api_symbols'])} "
        f"scanAxes={len(runtime['scan_axes'])} "
        f"company={len(declared['company_members'])} "
        f"scenarios={len(manifest.get('scenarios', {}))}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    return audit(args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
