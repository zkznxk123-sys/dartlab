"""엔진 SKILL.md 호출 규약 4 섹션 강제 — 회귀 차단 lint.

`src/dartlab/skills/specs/engines/{name}/SKILL.md` 15 종이 모두 같은 4 섹션을
갖도록 강제. 사용자 시점 "엔진마다 사용법이 어디 박혀있는지 모름" 문제의 SSOT
가드. 추가로 frontmatter `purpose` + `examples` 존재도 검증.

강제 섹션 (모든 엔진 본문에 ## 헤딩으로 1 회 이상 등장):

1. `## 공개 호출 방식`   — 진입점 패턴 (모듈 callable / Company-bound / 클래스 직접)
2. `## 호출 동작`        — axis/method 디스패치·dispatch 룰
3. `## 대표 반환 형태`   — DataFrame 컬럼·dataclass 필드·dtype
4. `## 기본 검증`        — 변경 시 동기화 약속·실패 표시 경로

axis/method 표는 권장 (warn) — 본 lint 차단 X. 향후 별도 lint 로 분리.

Sig:
    main(argv: list[str] | None = None) -> int

Args:
    --json        — 위반을 JSON 으로 stdout 출력 (CI 통합용)
    --update-baseline — baseline 파일 덮어쓰기 (운영자 수동만)

Example:
    uv run python -X utf8 tests/audit/checkEngineSpecSchema.py
    uv run python -X utf8 tests/audit/checkEngineSpecSchema.py --json

Returns:
    exit 0  — 위반 없음 또는 baseline 과 동일
    exit 2  — 신규 위반 (baseline 증가)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_ENGINES = _REPO / "src" / "dartlab" / "skills" / "specs" / "engines"
_BASELINE = _REPO / "tests" / "audit" / "_baselines" / "engineSpecSchema.json"

REQUIRED_SECTIONS = (
    "## 공개 호출 방식",
    "## 호출 동작",
    "## 대표 반환 형태",
    "## 기본 검증",
)

REQUIRED_FRONTMATTER = ("purpose", "examples")


def _split_frontmatter(text: str) -> tuple[str, str]:
    """frontmatter 블록 (--- ... ---) 와 본문을 분리."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5 :]


def _has_frontmatter_key(fm: str, key: str) -> bool:
    """frontmatter 안에 `key:` 가 등장하고 값이 비어있지 않은지."""
    pat = re.compile(rf"^{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    m = pat.search(fm)
    if not m:
        return False
    inline = m.group(1).strip()
    if inline:
        return True
    # block-style (list 또는 multi-line) — 다음 줄이 들여쓰기 + `-` 또는 비공백
    tail = fm[m.end() :]
    for line in tail.splitlines():
        if not line.strip():
            continue
        if line.startswith(("  ", "\t")):
            return True
        break
    return False


def _section_present(body: str, heading: str) -> bool:
    """본문에 ## 헤딩이 1 회 이상 등장하는지 (sub-spec 흡수로 중복 가능)."""
    pat = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    return pat.search(body) is not None


def _check_engine(spec_path: Path) -> list[str]:
    """단일 엔진 SKILL.md 검사. 위반 list 반환."""
    engine_id = spec_path.parent.name
    text = spec_path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    violations: list[str] = []
    for key in REQUIRED_FRONTMATTER:
        if not _has_frontmatter_key(fm, key):
            violations.append(f"{engine_id}::frontmatter::{key}")
    for heading in REQUIRED_SECTIONS:
        if not _section_present(body, heading):
            violations.append(f"{engine_id}::section::{heading}")
    return violations


def _load_baseline() -> set[str]:
    if not _BASELINE.exists():
        return set()
    data = json.loads(_BASELINE.read_text(encoding="utf-8"))
    return set(data.get("violations", []))


def _write_baseline(violations: list[str]) -> None:
    _BASELINE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_note": ("engine SKILL.md 4 섹션 강제 위반. baseline 증가 = 회귀. 위반 해소 시 본 파일에서 해당 라인 제거."),
        "violations": sorted(violations),
    }
    _BASELINE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)

    if not _ENGINES.exists():
        print(f"[checkEngineSpecSchema] engines dir 없음: {_ENGINES}", file=sys.stderr)
        return 2

    all_violations: list[str] = []
    for spec in sorted(_ENGINES.glob("*/SKILL.md")):
        all_violations.extend(_check_engine(spec))

    if args.update_baseline:
        _write_baseline(all_violations)
        print(
            f"[checkEngineSpecSchema] baseline 갱신: {len(all_violations)} 위반.",
            file=sys.stderr,
        )
        return 0

    baseline = _load_baseline()
    current = set(all_violations)
    new = sorted(current - baseline)
    cleared = sorted(baseline - current)

    if args.json:
        print(
            json.dumps(
                {
                    "current": sorted(current),
                    "baseline": sorted(baseline),
                    "new_violations": new,
                    "cleared_violations": cleared,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    if new:
        print(
            f"[checkEngineSpecSchema] FAIL — 신규 위반 {len(new)} 건:",
            file=sys.stderr,
        )
        for v in new:
            print(f"  + {v}", file=sys.stderr)
        print(
            "[checkEngineSpecSchema] 강제 섹션 4 종: " + " · ".join(REQUIRED_SECTIONS),
            file=sys.stderr,
        )
        return 2

    if cleared:
        print(
            f"[checkEngineSpecSchema] OK — baseline {len(cleared)} 건 해소 (운영자가"
            f" --update-baseline 으로 인덱스 갱신 권장).",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
