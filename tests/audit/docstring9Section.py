"""Docstring 9-섹션 검증 — G+ 트랙 룰 6b (rich docstring).

public 함수/메서드 docstring 에 dartlab 표준 9 섹션 명시:

    1. Capabilities — 이 함수가 제공하는 능력 (한줄~짧은 목록)
    2. AIContext     — AI/Agent 사용 맥락 (언제 호출, 어떤 evidence 남기는지)
    3. Guide        — 자유형 사용 가이드 (When/How/Verified 의 상위 섹션)
    4. When         — 호출 시점 (어떤 사용자 의도일 때)
    5. How          — 호출 방법 (다른 함수와의 연계 흐름)
    6. Requires     — 외부 의존성 (API 키 · 네트워크 · 캐시 등)
    7. Raises       — 발생 가능 예외
    8. Example      — 사용 예 (>>> 또는 `Example::` 블록)
    9. SeeAlso      — 관련 함수/엔진 cross-link

heuristic skip:
    - private (`_*`) 함수 — 검사 제외 (룰 5 가 별도 강제)
    - 단순 wrapper (본문 ≤ 3 line, return delegate) — `Capabilities/AIContext/Guide/When/How/SeeAlso` 면제, `Requires/Raises/Example` 만 검사
    - 인자 0 + return None (no-arg side-effect) — `Requires` 도 면제

baseline (`_baselines/<target>Docstring9Section.json`) 외 위반만 fail.

사용법::

    uv run python -X utf8 tests/audit/docstring9Section.py src/dartlab/gather
    uv run python -X utf8 tests/audit/docstring9Section.py src/dartlab/gather --strict
    uv run python -X utf8 tests/audit/docstring9Section.py src/dartlab/gather --update-baseline --baseline tests/audit/_baselines/gatherDocstring9Section.json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_TARGET = _REPO / "src" / "dartlab" / "gather"
_BASELINE = _REPO / "scripts" / "audit" / "_baselines" / "gatherDocstring9Section.json"


# ── 9 섹션 키워드 (한/영 변종 포함) ──────────────────────────────

_CAPABILITIES_KEYWORDS = (
    "Capabilities:",
    "Capabilities\n",
    "기능:",
    "기능\n",
)
_AICONTEXT_KEYWORDS = (
    "AIContext:",
    "AIContext\n",
    "AI Context:",
    "AI Context\n",
    "AI 컨텍스트:",
)
_GUIDE_KEYWORDS = (
    "Guide:",
    "Guide\n",
    "가이드:",
    "가이드\n",
)
_WHEN_KEYWORDS = (
    "When:",
    "When\n",
    "언제:",
    "사용 시점:",
)
_HOW_KEYWORDS = (
    "How:",
    "How\n",
    "어떻게:",
    "방법:",
)
_REQUIRES_KEYWORDS = (
    "Requires:",
    "Requires\n",
    "요구사항:",
    "필요:",
)
_RAISES_KEYWORDS = (
    "Raises:",
    "Raises\n",
    "Errors:",
    "Throws:",
    "예외:",
    "에러:",
)
_EXAMPLE_KEYWORDS = (
    "Example:",
    "Examples:",
    "Example\n",
    "Examples\n",
    "Example::",
    "Usage:",
    "예:",
    "예제:",
    "사용법:",
    ">>>",
)
_SEEALSO_KEYWORDS = (
    "See Also:",
    "SeeAlso:",
    "See Also\n",
    "참조:",
    "관련:",
)

_SECTIONS = (
    ("Capabilities", _CAPABILITIES_KEYWORDS),
    ("AIContext", _AICONTEXT_KEYWORDS),
    ("Guide", _GUIDE_KEYWORDS),
    ("When", _WHEN_KEYWORDS),
    ("How", _HOW_KEYWORDS),
    ("Requires", _REQUIRES_KEYWORDS),
    ("Raises", _RAISES_KEYWORDS),
    ("Example", _EXAMPLE_KEYWORDS),
    ("SeeAlso", _SEEALSO_KEYWORDS),
)

# 단순 wrapper 면제 — Capabilities/AIContext/Guide/When/How/SeeAlso 는 안 봐도 됨.
# Requires/Raises/Example 은 단순 wrapper 라도 외부 noise/예외 가능성 명시 필요.
_RICH_ONLY = {"Capabilities", "AIContext", "Guide", "When", "How", "SeeAlso"}


def _hasSection(docstring: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in docstring for kw in keywords)


def _isSimpleWrapper(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """본문이 docstring + 1~2 statement (대부분 return 위임) 이면 simple wrapper.

    Args/Return None 함수도 wrapper 로 간주 (Requires 면제 까지).
    """
    body = func.body
    # docstring 제외한 실제 statement
    start = 1 if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)) else 0
    realBody = body[start:]
    return len(realBody) <= 2


def _isNoArgVoid(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """인자 0 (self/cls 제외) + return None — side-effect 함수."""
    posargs = [a for a in func.args.args if a.arg not in ("self", "cls")]
    if posargs or func.args.kwonlyargs or func.args.vararg or func.args.kwarg:
        return False
    if func.returns is None:
        return True
    if isinstance(func.returns, ast.Constant) and func.returns.value is None:
        return True
    if isinstance(func.returns, ast.Name) and func.returns.id == "None":
        return True
    return False


def _scanFile(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    violations: list[dict] = []
    rel = str(path.relative_to(_REPO).as_posix())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        docstring = ast.get_docstring(node) or ""
        simple = _isSimpleWrapper(node)
        noArgVoid = _isNoArgVoid(node)
        missing: list[str] = []
        for name, keywords in _SECTIONS:
            if _hasSection(docstring, keywords):
                continue
            # heuristic skip
            if simple and name in _RICH_ONLY:
                continue
            if simple and noArgVoid and name == "Requires":
                continue
            missing.append(name)
        if missing:
            violations.append(
                {
                    "path": rel,
                    "line": node.lineno,
                    "function": node.name,
                    "missing": missing,
                }
            )
    return violations


def _scan(target: Path) -> list[dict]:
    if target.is_file():
        return sorted(_scanFile(target), key=lambda v: (v["path"], v["line"]))
    all_violations: list[dict] = []
    for p in target.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        all_violations.extend(_scanFile(p))
    return sorted(all_violations, key=lambda v: (v["path"], v["line"]))


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"violations": [], "_note": "G+ baseline"}


def _key(v: dict) -> str:
    return f"{v['path']}::{v['function']}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(_DEFAULT_TARGET.relative_to(_REPO).as_posix()))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--baseline",
        default=None,
        help="baseline JSON path (기본 _baselines/gatherDocstring9Section.json)",
    )
    args = parser.parse_args()
    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE

    target = (_REPO / args.target).resolve()
    if not target.exists():
        print(f"ERROR: target 부재 — {target}", file=sys.stderr)
        return 1

    violations = _scan(target)
    print(f"=== docstring 9-section audit (룰 6b) — {args.target} ===")
    print(f"위반 {len(violations)} 건 (9 섹션 중 1개 이상 부재)")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        baselinePath.write_text(
            json.dumps(
                {
                    "_note": "G+ 트랙 P-D 에서 docstring 채우며 축소",
                    "violations": sorted(_key(v) for v in violations),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)}")
        return 0

    baseline = _loadBaseline(baselinePath)
    allowed = set(baseline.get("violations", []))
    new_violations = [v for v in violations if _key(v) not in allowed]

    if args.strict:
        if violations:
            print("\n=== STRICT FAIL ===")
            for v in violations[:20]:
                print(f"  {v['path']}:{v['line']} {v['function']}() — 누락: {v['missing']}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    if new_violations:
        print("\n=== baseline 외 신규 위반 ===")
        for v in new_violations[:20]:
            print(f"  {v['path']}:{v['line']} {v['function']}() — 누락: {v['missing']}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
