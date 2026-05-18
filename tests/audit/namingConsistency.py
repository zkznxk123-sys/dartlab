"""매개변수 의미 일관성 lint — `core/naming/aliases.json` 표준 사전 검사.

정책 SSOT: src/dartlab/skills/specs/operation/code.md

dartlab 의 매개변수 명명이 같은 의미인데 `code` / `codeOrName` / `ticker` /
`stockCode` 로 흩어져 AI 가 도구 추론할 때 어려움을 겪는 문제를 해소.
표준 사전 (`src/dartlab/core/naming/aliases.json`) 에 의미 → 표준 이름 매핑을
정의하고, AST 매개변수 검사로 alias 사용 시 fail.

P0 단계는 placeholder — sentence dictionary 가 비어있으면 통과 (P5 에서 채움).

실행:
    python -X utf8 tests/audit/namingConsistency.py            # 전수 검사 (경고 모드)
    python -X utf8 tests/audit/namingConsistency.py --strict   # 위반 시 exit 2
    python -X utf8 tests/audit/namingConsistency.py --all      # 전수 (기본도 동일)

종료 코드:
    0 — 위반 0 건 (또는 사전 비어있음)
    2 — 위반 ≥ 1 건 (--strict)
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"
ALIASES_JSON = SRC / "core" / "naming" / "aliases.json"

SKIP_PATH_PARTS: tuple[str, ...] = (
    "tests",
    "experiments",
    "notebooks",
    "scripts",
    "blog",
    "landing",
    "sns",
    ".venv",
    ".venv-wsl",
    "build",
    "dist",
)

# 외부 노출 route handler — 매개변수 = HTTP path/query/CLI flag.
# 변경 시 URL/CLI 시그니처 BC 깨짐. namingConsistency 면제.
SKIP_PATH_PREFIXES: tuple[str, ...] = (
    "src/dartlab/server/api/",
    "src/dartlab/server/services/",
    "src/dartlab/cli/services/",
    "src/dartlab/cli/commands/",
)


@dataclass(frozen=True)
class Violation:
    """검출된 매개변수 명명 위반 — alias 사용을 표준 이름 후보와 함께 보고."""

    path: str
    line: int
    funcName: str
    argName: str
    standard: str
    meaning: str

    def format(self) -> str:
        """사람 가독 메시지 — Violation 객체를 한 줄 문자열로 변환."""
        return (
            f"  - {self.path}:{self.line} [{self.meaning}] {self.funcName}({self.argName}=...) → '{self.standard}' 권장"
        )


def _loadAliases() -> dict[str, dict]:
    """aliases.json 의 `aliases` 섹션 dict 반환 (없으면 빈)."""
    if not ALIASES_JSON.exists():
        return {}
    try:
        data = json.loads(ALIASES_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("aliases", {})


def _buildAliasIndex(aliases: dict[str, dict]) -> dict[str, tuple[str, str]]:
    """alias 이름 → (standard, meaning) 역인덱스. 같은 alias 가 여러 의미면 마지막 우선."""
    out: dict[str, tuple[str, str]] = {}
    for meaning, spec in aliases.items():
        std = spec.get("standard", "")
        for alias in spec.get("aliases", []):
            out[alias] = (std, meaning)
    return out


def _isSkipped(p: Path) -> bool:
    """면제 폴더 (tests/scripts/notebooks/blog/landing/sns + route handlers) 인지."""
    parts = {x.lower() for x in p.parts}
    if any(s in parts for s in SKIP_PATH_PARTS):
        return True
    # route handler 면제 (HTTP/CLI 시그니처 BC 영향)
    try:
        rel = p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return any(rel.startswith(prefix) for prefix in SKIP_PATH_PREFIXES)


def _scanFile(path: Path, aliasIndex: dict[str, tuple[str, str]]) -> list[Violation]:
    """단일 .py 파일에서 매개변수 alias 사용 검출."""
    violations: list[Violation] = []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return violations
    try:
        relPath = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        # 프로젝트 밖 파일 — absolute path (단위 테스트·외부 호출 지원)
        relPath = path.resolve().as_posix()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            if arg.arg in aliasIndex:
                std, meaning = aliasIndex[arg.arg]
                if arg.arg == std:
                    continue
                violations.append(
                    Violation(
                        path=relPath,
                        line=arg.lineno,
                        funcName=node.name,
                        argName=arg.arg,
                        standard=std,
                        meaning=meaning,
                    )
                )
    return violations


def main(argv: list[str]) -> int:
    """엔트리포인트 — aliases.json 로드 후 src/ 전수 스캔."""
    strict = "--strict" in argv
    aliases = _loadAliases()
    if not aliases:
        print("[naming-consistency] aliases.json 비어있음 (P5 에서 채워짐) — placeholder 통과.")
        return 0
    aliasIndex = _buildAliasIndex(aliases)
    if not aliasIndex:
        print("[naming-consistency] aliases.json 의 standard 와 alias 가 모두 비어있음.")
        return 0
    allViolations: list[Violation] = []
    fileCount = 0
    for py in SRC.rglob("*.py"):
        if py.name.startswith("_generated"):
            continue
        if _isSkipped(py):
            continue
        fileCount += 1
        allViolations.extend(_scanFile(py, aliasIndex))
    if not allViolations:
        print(f"[naming-consistency] OK — {fileCount} 파일 검사, 위반 0 건.")
        return 0
    print(f"[naming-consistency] 위반 {len(allViolations)} 건:")
    for v in allViolations:
        print(v.format())
    print("\n룰 SSOT: src/dartlab/core/naming/aliases.json\n  - 같은 의미면 같은 매개변수 이름 강제 (AI 추론 단순화).")
    return 2 if strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
