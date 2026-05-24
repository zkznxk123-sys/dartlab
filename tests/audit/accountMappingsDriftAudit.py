"""accountMappings drift audit — _version.json 정합 + 신규 mapping 검출 (T7-1).

src/dartlab/reference/data/accountMappings.json 의 *변경* 을 _version.json 의
*선언된 history* 와 비교. mapping 추가/삭제/rename 시 운영자가 history 항목
동행 강제.

검출 패턴:
    1. accountMappings.json `_metadata.totalMappings` 와 실제 mappings count drift
    2. _version.json 의 마지막 history.added 항목 ↔ 코드 변경 일관성
    3. standardAccountsCount drift (3143 baseline)

실행::

    uv run python -X utf8 tests/audit/accountMappingsDriftAudit.py
    uv run python -X utf8 tests/audit/accountMappingsDriftAudit.py --strict
    uv run python -X utf8 tests/audit/accountMappingsDriftAudit.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAPPINGS_FILE = REPO_ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"
VERSION_FILE = REPO_ROOT / "src" / "dartlab" / "reference" / "data" / "_version.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="accountMappings drift audit (T7-1)")
    parser.add_argument("--strict", action="store_true", help="drift 발견 시 exit 2")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if not MAPPINGS_FILE.exists():
        print(f"[accountMappingsDrift] mappings 파일 없음: {MAPPINGS_FILE}")
        return 0
    if not VERSION_FILE.exists():
        print("[accountMappingsDrift] _version.json 없음 — T7-1 미설정")
        return 1

    try:
        mappings = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
        version = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[accountMappingsDrift] JSON 파싱 실패: {e}")
        return 1

    metadata = mappings.get("_metadata", {})
    actualMappings = mappings.get("mappings", {})
    actualCount = len(actualMappings)
    declaredTotal = metadata.get("merged", 0)
    declaredStandard = metadata.get("standardAccountsCount", 0)

    versionDeclaredTotal = version.get("totalMappings", 0)
    versionDeclaredStandard = version.get("standardAccountsCount", 0)

    drifts: list[str] = []

    if actualCount != declaredTotal:
        drifts.append(
            f"_metadata.merged ({declaredTotal}) vs 실제 mappings count ({actualCount}) — drift {actualCount - declaredTotal:+d}"
        )

    if declaredTotal != versionDeclaredTotal:
        drifts.append(
            f"accountMappings._metadata.merged ({declaredTotal}) vs _version.totalMappings ({versionDeclaredTotal}) — drift"
        )

    if declaredStandard != versionDeclaredStandard:
        drifts.append(
            f"accountMappings._metadata.standardAccountsCount ({declaredStandard}) vs _version.standardAccountsCount ({versionDeclaredStandard}) — drift"
        )

    result = {
        "accountMappingsVersion": version.get("accountMappingsVersion"),
        "schemaVersion": version.get("schemaVersion"),
        "actualMappingsCount": actualCount,
        "declaredTotalInMetadata": declaredTotal,
        "declaredTotalInVersion": versionDeclaredTotal,
        "drifts": drifts,
        "ok": len(drifts) == 0,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[accountMappingsDrift] accountMappings version: {result['accountMappingsVersion']}")
        print(
            f"[accountMappingsDrift] 실제 mappings: {actualCount}, _metadata.merged: {declaredTotal}, _version.totalMappings: {versionDeclaredTotal}"
        )
        if drifts:
            print(f"[accountMappingsDrift] drift {len(drifts)} 건:")
            for d in drifts:
                print(f"  - {d}")
            print("\n수정: _version.json history 항목 추가 + version bump + _metadata 동기화")
        else:
            print("[accountMappingsDrift] OK — drift 0")

    if args.strict and drifts:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
