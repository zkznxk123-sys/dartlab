"""camelCase + docstring lint — AST 기반, diff 기준 (legacy 비차단).

룰 (operation.code):
    1. 네이밍 — camelCase (클래스는 PascalCase, 모듈 상수는 ALL_CAPS).
    2. 독스트링 — public def/class 에 1 줄 이상 존재.

검사 대상:
    - 함수/async 함수/클래스 정의 이름
    - 메서드/async 메서드 이름 (클래스 안)
    - 함수 매개변수 이름 (positional / keyword / posonly / kwonly)
    - 모듈 레벨 assignment target (ALL_CAPS 상수 제외)
    - public def/class 의 docstring 존재 여부

면제 (절대 면제):
    - tests/ · experiments/ · notebooks/ · scripts/  하위 전체
    - 파일명: _generated*.py · *_pb2.py · conftest.py
    - dunder (`__init__`, `__call__`, `__repr__` 등)
    - 단일 underscore prefix (`_private`) — 명시적 private 으로 간주
    - ALL_CAPS_CONST (모듈 상수)
    - `_`, `__`, `*args`, `**kwargs` 등 관용 매개변수
    - Python/3rd party 표준 메서드 시그니처 (setUp, tearDown 등)

diff 기준:
    HEAD 에 이미 있던 (name, kind) 는 legacy 로 간주, 검사에서 제외.
    이번 edit 으로 *새로 추가된* identifier 만 검사한다.
    파일 자체가 신규면 모든 identifier 가 새 것 → 전수 검사.

shim 모드:
    기본은 `snake_alias = camelOrigin` 패턴을 backward-compat shim 으로 자동
    인정 (operation.code 권고). 0.10 결정에 따라 shim 없이 절대금지가 필요한
    경우 `--no-shim` 또는 환경변수 `DARTLAB_LINT_NO_SHIM=1` 로 비활성화.

실행 모드:
    파일 모드 — 명시 파일 lint::

        python -X utf8 scripts/dev/lint_camelcase_ast.py path/to/file.py [...] [--strict]
        python -X utf8 scripts/dev/lint_camelcase_ast.py --changed         # git diff (staged + unstaged)
        python -X utf8 scripts/dev/lint_camelcase_ast.py --all             # src/dartlab/ 전수
        python -X utf8 scripts/dev/lint_camelcase_ast.py --all --no-shim   # P6 codemod 후 absolute

    Hook 모드 — PostToolUse 호환 stdin JSON::

        python -X utf8 scripts/dev/lint_camelcase_ast.py --hook

종료 코드:
    0 — 통과 (검사 안 함 / 위반 없음)
    1 — 입력 오류
    2 — 새 위반 발견 (Hook 모드에서 edit 차단 의미)
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DEFAULT = ROOT / "src" / "dartlab"

# shim alias 자동 감지 비활성화 플래그.
# 환경변수로 사전 set 또는 main 의 --no-shim 으로 런타임 set.
_NO_SHIM: bool = bool(os.environ.get("DARTLAB_LINT_NO_SHIM"))

# ── 정규식 ─────────────────────────────────────────────────

# camelCase: lower 또는 _lower 시작, 이후 영문/숫자만, 단일 단어 ok
CAMEL_RE = re.compile(r"^_?[a-z][a-zA-Z0-9]*$")
# PascalCase: Upper 또는 _Upper 시작
PASCAL_RE = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")
# ALL_CAPS_CONST (밑줄 허용)
ALL_CAPS_RE = re.compile(r"^_?[A-Z0-9][A-Z0-9_]*$")
# dunder
DUNDER_RE = re.compile(r"^__[a-z][a-zA-Z0-9_]*__$")
# 명시적 private (_lower 시작 — single underscore)
PRIVATE_PREFIX_RE = re.compile(r"^_[a-zA-Z]")

# ── 면제 ───────────────────────────────────────────────────

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

SKIP_NAME_PATTERNS: tuple[str, ...] = (
    "_generated",
    "_pb2.py",
    "conftest.py",
)

# 관용 매개변수 — camelCase 룰 면제
ARG_ALLOWLIST: frozenset[str] = frozenset(
    {
        "self",
        "cls",
        "mcs",  # metaclass 관용
        "_",  # placeholder
        "args",
        "kwargs",
        "x",
        "y",
        "z",
        "n",
        "i",
        "j",
        "k",
        "v",
        "fn",
        "df",
        "lf",
        "id",
        # Kalman filter 수학 표준 표기 (Rauch-Tung-Striebel smoother 등)
        "P_pred",
        "P_filt",
        "a_pred",
        "a_filt",
        "P_smooth",
        "a_smooth",
    }
)

# 표준/3rd party override 메서드 — 이름이 snake_case 여도 허용
METHOD_NAME_ALLOWLIST: frozenset[str] = frozenset(
    {
        "setUp",
        "tearDown",
        "setUpClass",
        "tearDownClass",
        # pytest fixture / hook
        "setup_method",
        "teardown_method",
        "setup_class",
        "teardown_class",
        # Pydantic v1/v2
        "model_config",
        "model_fields",
        "model_dump",
        "model_validate",
        # asyncio
        "run_until_complete",
        # Jupyter / IPython mime 표준 — 변환 시 Jupyter 가 인식 못 함
        "_repr_html_",
        "_repr_mimebundle_",
        "_repr_pretty_",
        "_repr_markdown_",
        "_repr_png_",
        "_repr_json_",
        "_repr_latex_",
        "_repr_jpeg_",
        "_repr_svg_",
        "_ipython_key_completions_",  # IPython tab completion
        "_ipythonKeyCompletions_",  # camelCase 변환 alias
        # Python http.server BaseHTTPRequestHandler 표준 메서드
        "do_GET",
        "do_POST",
        "do_PUT",
        "do_DELETE",
        "do_HEAD",
        "do_OPTIONS",
        "log_message",
        # html.parser HTMLParser hook — parent 가 snake 이름으로 호출. camel 변환 시 호출 안 됨.
        "handle_starttag",
        "handle_endtag",
        "handle_startendtag",
        "handle_data",
        "handle_entityref",
        "handle_charref",
        "handle_comment",
        "handle_decl",
        "handle_pi",
        "unknown_decl",
    }
)

# Python keyword 회피용 trailing underscore 매개변수 — 변경 불가능
ARG_KEYWORD_SUFFIX_ALLOWLIST: frozenset[str] = frozenset(
    {
        "open_",
        "close_",
        "type_",
        "class_",
        "id_",
        "from_",
        "import_",
        "global_",
        "lambda_",
        "yield_",
        "async_",
        "await_",
        "is_",
        "and_",
        "or_",
        "not_",
        "if_",
        "else_",
        "elif_",
        "for_",
        "while_",
        "return_",
        "raise_",
        "try_",
        "except_",
        "finally_",
        "with_",
        "as_",
        "pass_",
        "break_",
        "continue_",
        "del_",
    }
)

# kind → 사람 라벨
KIND_LABEL = {
    "func": "함수",
    "asyncfunc": "async 함수",
    "method": "메서드",
    "asyncmethod": "async 메서드",
    "class": "클래스",
    "arg": "매개변수",
    "var": "모듈 변수",
}


# ── 데이터 클래스 ─────────────────────────────────────────


@dataclass(frozen=True)
class Identifier:
    """소스에서 추출한 식별자 (이름 + 종류 + 위치).

    diff 비교는 (name, kind) 튜플 기준으로만 한다 (line 은 메시지 표시용).
    """

    name: str
    kind: str
    line: int
    qualifier: str = ""  # 클래스명 (메서드/매개변수일 때) 또는 함수명 (매개변수)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.qualifier, self.name, self.kind)


@dataclass
class Violation:
    path: str
    line: int
    name: str
    kind: str
    rule: str
    message: str

    def format(self) -> str:
        label = KIND_LABEL.get(self.kind, self.kind)
        return f"  - {self.path}:{self.line} [{self.rule}] {label} '{self.name}' — {self.message}"


# ── AST 추출 ──────────────────────────────────────────────


class _Collector(ast.NodeVisitor):
    """모듈 AST 에서 검사 대상 식별자 + 독스트링 결손을 수집."""

    def __init__(self) -> None:
        self.identifiers: list[Identifier] = []
        # public def/class 중 docstring 없는 것 (qualifier, name, line)
        self.missing_docstring: list[tuple[str, str, int, str]] = []
        self._class_stack: list[str] = []

    # 모듈 = 함수와 동일 처리 + module-level Assign
    def visit_Module(self, node: ast.Module) -> None:
        for stmt in node.body:
            self._collect_module_assign(stmt)
        self.generic_visit(node)

    def _collect_module_assign(self, stmt: ast.stmt) -> None:
        # 모듈 레벨에서만 호출됨
        if isinstance(stmt, ast.Assign):
            # 하위호환 shim 감지: `snake_alias = camelOrigin` (단일 target + 단일 value)
            # operation.code: "이동된 기존 snake_case 는 하위호환 유지 (shim)" — 허용.
            if _is_shim_alias(stmt):
                return
            for tgt in stmt.targets:
                self._record_assign_target(tgt, stmt.lineno)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if _is_shim_annassign(stmt):
                return
            self._record_assign_target(stmt.target, stmt.lineno)

    def _record_assign_target(self, tgt: ast.expr, line: int) -> None:
        if isinstance(tgt, ast.Name):
            name = tgt.id
            if DUNDER_RE.match(name) or name == "_":
                return
            self.identifiers.append(Identifier(name=name, kind="var", line=line))
        elif isinstance(tgt, (ast.Tuple, ast.List)):
            for elt in tgt.elts:
                self._record_assign_target(elt, line)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_func(node, is_async=True)

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        in_class = bool(self._class_stack)
        qualifier = self._class_stack[-1] if in_class else ""
        if in_class:
            kind = "asyncmethod" if is_async else "method"
        else:
            kind = "asyncfunc" if is_async else "func"

        self.identifiers.append(Identifier(name=node.name, kind=kind, line=node.lineno, qualifier=qualifier))

        # 매개변수
        args = node.args
        for arg in (
            list(args.posonlyargs)
            + list(args.args)
            + list(args.kwonlyargs)
            + ([args.vararg] if args.vararg else [])
            + ([args.kwarg] if args.kwarg else [])
        ):
            if arg is None:
                continue
            self.identifiers.append(
                Identifier(
                    name=arg.arg,
                    kind="arg",
                    line=arg.lineno,
                    qualifier=f"{qualifier}.{node.name}" if qualifier else node.name,
                )
            )

        # docstring
        if not node.name.startswith("_"):
            doc = ast.get_docstring(node)
            if not doc or not doc.strip():
                self.missing_docstring.append((qualifier, node.name, node.lineno, kind))

        # 함수 본문은 traverse — 중첩 클래스/함수 내부의 클래스 def 잡기 위해
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualifier = self._class_stack[-1] if self._class_stack else ""
        self.identifiers.append(Identifier(name=node.name, kind="class", line=node.lineno, qualifier=qualifier))
        # docstring
        if not node.name.startswith("_"):
            doc = ast.get_docstring(node)
            if not doc or not doc.strip():
                self.missing_docstring.append((qualifier, node.name, node.lineno, "class"))

        self._class_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()


def _is_camel_or_pascal_or_dotted(value: ast.expr) -> bool:
    """value 가 camelCase/PascalCase Name 또는 Attribute 체인 (foo.barBaz) 인지."""
    if isinstance(value, ast.Name):
        return bool(CAMEL_RE.match(value.id) or PASCAL_RE.match(value.id))
    if isinstance(value, ast.Attribute):
        # 마지막 attr 만 확인 — 모듈 prefix 는 무관
        return bool(CAMEL_RE.match(value.attr) or PASCAL_RE.match(value.attr))
    return False


def _is_shim_value(value: ast.expr, lhs_name: str) -> bool:
    """value 가 backwards-compat shim 패턴인지.

    허용 패턴:
        1. camelCase Name 또는 Attribute (`fetchOhlcv`, `mod.fetchOhlcv`)
        2. Call(camelFn, ...) 또는 Call(staticmethod, camelFn) 등 — 함수 자체가
           camelCase 이고 인자에 camelCase Name 이 포함 (래핑 헬퍼)
        3. Call(...) 의 어떤 인자가 lhs_name 과 동일한 문자열 리터럴 — 명시적
           "alias name" 표기 (`_deprecatedAlias(target, "snake_name")`)
    """
    if _is_camel_or_pascal_or_dotted(value):
        return True
    if isinstance(value, ast.Call):
        # 함수 부분도 camelCase 인지
        func = value.func
        func_camel = False
        if isinstance(func, ast.Name):
            func_camel = bool(CAMEL_RE.match(func.id) or PASCAL_RE.match(func.id))
        elif isinstance(func, ast.Attribute):
            func_camel = bool(CAMEL_RE.match(func.attr) or PASCAL_RE.match(func.attr))
        if not func_camel:
            return False
        # 인자 중 하나라도 camelCase Name 또는 lhs_name 과 같은 문자열 리터럴
        for arg in list(value.args) + [kw.value for kw in value.keywords]:
            if _is_camel_or_pascal_or_dotted(arg):
                return True
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value == lhs_name:
                    return True
    return False


def _is_shim_alias(stmt: ast.Assign) -> bool:
    """`snake_alias = camelOrigin` 또는 `snake_alias = wrap(camelOrigin)` 패턴.

    operation.code "이동된 기존 snake_case 는 하위호환 유지 (shim)" 허용.
    `--no-shim` (또는 환경변수 DARTLAB_LINT_NO_SHIM) 활성 시 항상 False.
    """
    if _NO_SHIM:
        return False
    if len(stmt.targets) != 1:
        return False
    tgt = stmt.targets[0]
    if not isinstance(tgt, ast.Name):
        return False
    name = tgt.id
    if CAMEL_RE.match(name) or ALL_CAPS_RE.match(name) or DUNDER_RE.match(name):
        return False
    if "_" not in name.lstrip("_"):
        return False
    return _is_shim_value(stmt.value, name)


def _is_shim_annassign(stmt: ast.AnnAssign) -> bool:
    """AnnAssign 형태의 backwards-compat shim 감지 (`snake: T = camelOrigin`)."""
    if _NO_SHIM:
        return False
    if not isinstance(stmt.target, ast.Name) or stmt.value is None:
        return False
    name = stmt.target.id
    if CAMEL_RE.match(name) or ALL_CAPS_RE.match(name) or DUNDER_RE.match(name):
        return False
    if "_" not in name.lstrip("_"):
        return False
    return _is_shim_value(stmt.value, name)


def _collect(source: str) -> _Collector:
    """소스 문자열을 파싱해 Collector 반환. 파싱 실패 시 빈 Collector."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _Collector()
    col = _Collector()
    col.visit(tree)
    return col


# ── 룰 판정 ──────────────────────────────────────────────


def _is_skipped_path(p: Path) -> bool:
    parts = {x.lower() for x in p.parts}
    if any(s in parts for s in SKIP_PATH_PARTS):
        return True
    name = p.name
    return any(pat in name for pat in SKIP_NAME_PATTERNS)


def _check_naming(ident: Identifier) -> str | None:
    """식별자 이름이 룰을 어기면 룰 코드 반환, OK 면 None."""
    name = ident.name
    kind = ident.kind

    # dunder, single underscore placeholder, ALL_CAPS 상수 등 면제
    if name in ("_", "__"):
        return None
    if DUNDER_RE.match(name):
        return None
    if ALL_CAPS_RE.match(name):
        # 변수면 상수로 인정, 함수/메서드/클래스라면 ALL_CAPS 는 비전형 → 일단 통과
        return None

    if kind == "arg":
        if name in ARG_ALLOWLIST:
            return None
        if name in ARG_KEYWORD_SUFFIX_ALLOWLIST:
            return None
        # trailing underscore 매개변수 (is_/in_/for_) — Python keyword 회피용, 보존 허용
        import keyword

        if name.endswith("_") and keyword.iskeyword(name.rstrip("_")):
            return None
        # arg 도 camelCase
        if not CAMEL_RE.match(name):
            return "naming/arg-snake"
        return None

    if kind == "class":
        if PASCAL_RE.match(name):
            return None
        return "naming/class-not-pascal"

    if kind in ("method", "asyncmethod"):
        if name in METHOD_NAME_ALLOWLIST:
            return None
        if CAMEL_RE.match(name):
            return None
        return "naming/method-snake"

    if kind in ("func", "asyncfunc"):
        if CAMEL_RE.match(name):
            return None
        # PascalCase 함수 = factory 패턴 인정 (Company(), Macro() 같은 callable factory)
        if PASCAL_RE.match(name):
            return None
        return "naming/func-snake"

    if kind == "var":
        # 모듈 변수: camelCase 허용 (ALL_CAPS 는 위에서 면제됨)
        if CAMEL_RE.match(name):
            return None
        # PascalCase 모듈 변수 = TypeAlias 또는 클래스 alias 인정 (Pydantic Literal 타입 등)
        if PASCAL_RE.match(name):
            return None
        # private (_xxx_yyy single underscore prefix) 모듈 변수는 의도된 internal —
        # operation.code 룰 면제. 외부 사용 안 되니 snake 로 두는 게 더 안전 (rename
        # 영향이 module 안에 갇힘). plan F5 정책.
        if name.startswith("_") and not name.startswith("__"):
            return None
        return "naming/var-snake"

    return None


# ── HEAD 비교 ─────────────────────────────────────────────


def _git_show_head(path_rel: str) -> str | None:
    """HEAD:path 의 내용 반환. 신규 파일이면 None."""
    try:
        out = subprocess.run(
            ["git", "show", f"HEAD:{path_rel}"],
            capture_output=True,
            cwd=ROOT,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        return out.stdout.decode("utf-8", errors="replace")
    except Exception:
        return None


def _new_identifiers(current: _Collector, head: _Collector | None) -> list[Identifier]:
    if head is None:
        return list(current.identifiers)
    head_keys = {i.key for i in head.identifiers}
    return [i for i in current.identifiers if i.key not in head_keys]


def _new_missing_docs(current: _Collector, head: _Collector | None) -> list[tuple[str, str, int, str]]:
    if head is None:
        return list(current.missing_docstring)
    head_keys = {(q, n) for (q, n, _ln, _k) in head.missing_docstring}
    head_def_keys = {
        (i.qualifier, i.name)
        for i in head.identifiers
        if i.kind in ("func", "asyncfunc", "method", "asyncmethod", "class")
    }
    out: list[tuple[str, str, int, str]] = []
    for q, n, ln, k in current.missing_docstring:
        # HEAD 에서 이미 docstring 없던 채로 존재했다면 legacy → 통과
        if (q, n) in head_keys:
            continue
        # HEAD 에 그 def 자체가 있었다면 (docstring 만 빠진 게 아니라 새로 추가된 게 아님) → legacy 로 본다
        if (q, n) in head_def_keys:
            continue
        out.append((q, n, ln, k))
    return out


# ── 파일 lint 진입점 ──────────────────────────────────────


def _lint_file(path: Path, *, baseline: bool = False) -> list[Violation]:
    """단일 파일 lint, 새 위반 리스트 반환.

    baseline=True 면 HEAD 와 diff 하지 않고 *모든* 위반을 보고한다 (--all 용도).
    """
    violations: list[Violation] = []

    if not path.exists() or path.suffix != ".py":
        return violations

    try:
        path_rel = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        # 프로젝트 밖 파일 — absolute path 그대로 (단위 테스트·외부 호출 지원)
        path_rel = path.resolve().as_posix()

    if _is_skipped_path(Path(path_rel)):
        return violations

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    current = _collect(source)
    if baseline:
        head = None  # 전수 검사 — HEAD diff 생략
    else:
        head_src = _git_show_head(path_rel)
        head = _collect(head_src) if head_src is not None else None

    # 네이밍
    for ident in _new_identifiers(current, head):
        rule = _check_naming(ident)
        if rule is None:
            continue
        violations.append(
            Violation(
                path=path_rel,
                line=ident.line,
                name=ident.name,
                kind=ident.kind,
                rule=rule,
                message=_naming_message(ident, rule),
            )
        )

    # 독스트링
    for q, n, ln, k in _new_missing_docs(current, head):
        violations.append(
            Violation(
                path=path_rel,
                line=ln,
                name=n,
                kind=k,
                rule="docstring/missing",
                message="public 정의에 docstring 누락 — 1 줄 이상의 한국어 설명 필요 (operation.code 9 섹션 권장).",
            )
        )

    return violations


def _naming_message(ident: Identifier, rule: str) -> str:
    suggestion = _camelize(ident.name) if rule != "naming/class-not-pascal" else _pascalize(ident.name)
    convention = "PascalCase" if rule == "naming/class-not-pascal" else "camelCase"
    return f"{convention} 위반 — '{ident.name}' → '{suggestion}' 권장 (룰 SSOT: operation.code)."


def _camelize(name: str) -> str:
    leading_us = ""
    rest = name
    while rest.startswith("_"):
        leading_us += "_"
        rest = rest[1:]
    parts = rest.split("_")
    if not parts:
        return name
    head, *tail = parts
    return leading_us + head.lower() + "".join(p[:1].upper() + p[1:].lower() for p in tail if p)


def _pascalize(name: str) -> str:
    leading_us = ""
    rest = name
    while rest.startswith("_"):
        leading_us += "_"
        rest = rest[1:]
    parts = [p for p in rest.split("_") if p]
    return leading_us + "".join(p[:1].upper() + p[1:].lower() for p in parts)


# ── 모드별 실행 ───────────────────────────────────────────


def _list_changed_paths() -> list[Path]:
    """git diff (staged + unstaged + untracked) 의 .py 파일."""
    paths: set[str] = set()
    cmds = [
        ["git", "diff", "--name-only", "--diff-filter=ACMR"],
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for cmd in cmds:
        try:
            out = subprocess.run(cmd, capture_output=True, cwd=ROOT, check=False, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if out.returncode != 0:
            continue
        for line in out.stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.endswith(".py"):
                paths.add(line)
    return sorted({(ROOT / p) for p in paths if p})


def _all_src_paths() -> list[Path]:
    return sorted(SRC_DEFAULT.rglob("*.py"))


def _emit(violations: list[Violation], stream) -> None:
    if not violations:
        return
    stream.write(f"[lint-camelcase] 새 위반 {len(violations)} 건:\n")
    for v in violations:
        stream.write(v.format() + "\n")
    stream.write(
        "\n룰 SSOT: src/dartlab/skills/specs/operation/code.md "
        "(camelCase + 9 섹션 docstring). diff 기준이라 legacy 는 통과.\n"
    )


# ── Hook 모드 ────────────────────────────────────────────


def _run_hook() -> int:
    """PostToolUse 호환 hook — stdin JSON 받아 lint, 위반 시 exit 2.

    PostToolUse 입력::

        {
          "session_id": "...",
          "tool_name": "Edit" | "Write" | "MultiEdit" | ...,
          "tool_input": {"file_path": "...", ...},
          "tool_response": {...}
        }

    exit 2 + stderr 메시지 → 호스트 harness 가 모델에게 피드백.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # 입력 파싱 실패 — 차단하지 않음 (hook 자체 실패가 작업을 막으면 안됨)
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0

    path = Path(file_path)
    if path.suffix != ".py":
        return 0

    violations = _lint_file(path)
    if not violations:
        return 0

    _emit(violations, sys.stderr)
    sys.stderr.write(
        "\n수정 후 다시 시도하거나, 의도된 legacy shim 이면 commit 후 재시도 "
        "(diff 기준이라 commit 된 식별자는 legacy 로 통과).\n"
    )
    return 2


# ── CLI 진입점 ───────────────────────────────────────────


def main(argv: list[str]) -> int:
    """CLI 진입점 — flag 파싱 후 모드별 lint 실행."""
    global _NO_SHIM
    if "--no-shim" in argv:
        _NO_SHIM = True
    if "--hook" in argv:
        return _run_hook()

    strict = "--strict" in argv
    args = [a for a in argv if not a.startswith("--")]

    baseline = "--all" in argv
    if "--changed" in argv:
        targets = _list_changed_paths()
    elif baseline:
        targets = _all_src_paths()
    elif args:
        targets = [Path(a) for a in args]
    else:
        # 기본 = changed
        targets = _list_changed_paths()

    if not targets:
        print("[lint-camelcase] 검사 대상 .py 없음.")
        return 0

    all_violations: list[Violation] = []
    for path in targets:
        all_violations.extend(_lint_file(path, baseline=baseline))

    if not all_violations:
        print(f"[lint-camelcase] OK — 검사 {len(targets)} 파일, 새 위반 0 건.")
        return 0

    _emit(all_violations, sys.stdout)
    # CLI 기본은 exit 0 (경고 모드), --strict 면 exit 2
    return 2 if strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
