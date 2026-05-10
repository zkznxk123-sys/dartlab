"""snake_case → camelCase 일괄 변환 (P6 Pass 2~3 적용).

전략:
    1. dartlab 자체 정의 식별자 set 빌드 (def name + arg name + 모듈 var)
    2. 같은 set 안 식별자만 변환 (외부 라이브러리 함수명 보호)
    3. libCST 로 정의 + 호출 사이트 + kwarg 동시 변환
    4. Attribute (a.b 의 b) 는 정의 set 안에 있으면 변환

면제:
    - dunder, _private (single underscore, ALL_CAPS_CONST)
    - tests/scripts/notebooks 폴더
    - ARG_ALLOWLIST (self/cls/df/lf 등)

실행:
    python -X utf8 scripts/dev/applyCamelTransform.py --apply

종료 코드:
    0 — 적용 OK
    1 — 입력 오류
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import libcst as cst
import libcst.matchers as m

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"

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

SKIP_NAME_PATTERNS: tuple[str, ...] = ("_generated", "_pb2.py", "conftest.py")

ARG_ALLOWLIST: frozenset[str] = frozenset(
    {"self", "cls", "mcs", "_", "args", "kwargs", "x", "y", "z", "n", "i", "j", "k", "v", "fn", "df", "lf", "id"}
)

DUNDER_RE = re.compile(r"^__[a-z][a-zA-Z0-9_]*__$")
ALL_CAPS_RE = re.compile(r"^_?[A-Z][A-Z0-9_]*$")
SNAKE_RE = re.compile(r"^_?[a-z][a-z0-9_]*$")


def _toCamel(name: str) -> str:
    """snake_case → camelCase. leading/trailing underscore 보존, ALL_CAPS 보존, Python keyword 충돌 회피."""
    import keyword

    if not name or DUNDER_RE.match(name) or ALL_CAPS_RE.match(name):
        return name
    # trailing underscore 보존 (Python keyword 충돌 회피용 — `is_`, `in_`, `for_` 등)
    trailing = ""
    base = name
    while base.endswith("_"):
        trailing = "_" + trailing
        base = base[:-1]
    if not base:
        return name  # 모두 underscore 면 그대로
    leading = ""
    rest = base
    while rest.startswith("_"):
        leading += "_"
        rest = rest[1:]
    if not rest or "_" not in rest:
        result = leading + rest + trailing
    else:
        parts = rest.split("_")
        head, *tail = parts
        result = leading + head.lower() + "".join(p[:1].upper() + p[1:].lower() for p in tail if p) + trailing
    # Python keyword 충돌 시 trailing underscore 추가
    if keyword.iskeyword(result):
        result = result + "_"
    return result


def _isSkipped(p: Path) -> bool:
    parts = {x.lower() for x in p.parts}
    if any(s in parts for s in SKIP_PATH_PARTS):
        return True
    return any(pat in p.name for pat in SKIP_NAME_PATTERNS)


def _isVariableSnake(name: str) -> bool:
    """변환 대상 snake_case 식별자 판정."""
    if name in ARG_ALLOWLIST:
        return False
    if not SNAKE_RE.match(name):
        return False
    if "_" not in name.lstrip("_"):
        return False
    if name.startswith("__"):  # dunder/private mangled
        return False
    return True


class _IdentifierCollector(cst.CSTVisitor):
    """dartlab 자체 정의 snake_case 식별자 수집."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if _isVariableSnake(node.name.value):
            self.names.add(node.name.value)
        for param in node.params.params:
            if _isVariableSnake(param.name.value):
                self.names.add(param.name.value)
        for param in node.params.kwonly_params:
            if _isVariableSnake(param.name.value):
                self.names.add(param.name.value)
        for param in node.params.posonly_params:
            if _isVariableSnake(param.name.value):
                self.names.add(param.name.value)


class _Renamer(cst.CSTTransformer):
    """dartlab 정의 식별자 set 안 이름만 snake → camel 변환."""

    def __init__(self, definedNames: set[str]) -> None:
        self.defined = definedNames

    def leave_FunctionDef(self, _orig: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        if updated.name.value in self.defined:
            updated = updated.with_changes(name=cst.Name(_toCamel(updated.name.value)))
        return updated

    def leave_Param(self, _orig: cst.Param, updated: cst.Param) -> cst.Param:
        if updated.name.value in self.defined:
            updated = updated.with_changes(name=cst.Name(_toCamel(updated.name.value)))
        return updated

    def leave_Name(self, _orig: cst.Name, updated: cst.Name) -> cst.Name:
        if updated.value in self.defined:
            return updated.with_changes(value=_toCamel(updated.value))
        return updated

    def leave_Attribute(self, _orig: cst.Attribute, updated: cst.Attribute) -> cst.Attribute:
        # Attribute 의 attr 부분 — dartlab 정의 set 에 있으면 변환
        # 위험: 외부 라이브러리 메서드 (예: pydantic Field 의 max_length kwarg, polars df.read_csv) 와
        # 우연히 이름 같으면 false positive. attr 변환은 method name 만 영향 — kwarg 보호 됨.
        if updated.attr.value in self.defined:
            return updated.with_changes(attr=cst.Name(_toCamel(updated.attr.value)))
        return updated

    # leave_Arg 비활성: kwarg 변환 시 외부 라이브러리 (Pydantic Field, polars, plotly) 의 kwarg 까지
    # false positive 변환됨 (예: Field(max_length=100) → Field(maxLength=100) 으로 Pydantic 키워드 깨짐).
    # dartlab 자체 호출의 kwarg 갱신은 별도 sed 또는 수동.


def _collectAllDefined() -> set[str]:
    """src/dartlab 전수 스캔 → 정의된 snake 식별자 set."""
    collector = _IdentifierCollector()
    for py in SRC.rglob("*.py"):
        if _isSkipped(py):
            continue
        try:
            source = py.read_text(encoding="utf-8")
            tree = cst.parse_module(source)
        except (OSError, UnicodeDecodeError, cst.ParserSyntaxError):
            continue
        tree.visit(collector)
    return collector.names


def _applyToFile(path: Path, definedNames: set[str]) -> bool:
    """단일 파일 변환 — 변경 시 True."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = cst.parse_module(source)
    except (OSError, UnicodeDecodeError, cst.ParserSyntaxError):
        return False
    new = tree.visit(_Renamer(definedNames))
    new_source = new.code
    if new_source != source:
        path.write_text(new_source, encoding="utf-8")
        return True
    return False


def main(argv: list[str]) -> int:
    """CLI — --apply 시 src/dartlab + tests + scripts 일괄 변환."""
    if "--apply" not in argv:
        print("[apply-camel] --apply 명시 필요 (dry-run 은 codemodToCamel.py).")
        return 1
    print("[apply-camel] 정의 식별자 set 수집 중...")
    defined = _collectAllDefined()
    print(f"  정의 식별자: {len(defined)}")
    print(f"  대표 5: {sorted(defined)[:5]}")
    targets = [p for p in SRC.rglob("*.py") if not _isSkipped(p)]
    # tests / scripts 는 호출 사이트 갱신 위해 포함
    for d in (ROOT / "tests", ROOT / "scripts"):
        targets.extend(p for p in d.rglob("*.py"))
    changed = 0
    for path in targets:
        if _applyToFile(path, defined):
            changed += 1
    print(f"\n[apply-camel] {changed} / {len(targets)} 파일 변경됨")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
