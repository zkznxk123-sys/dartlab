"""Docstring 9-섹션 검증 (providers 한정) — P-PR 트랙 측정 게이트.

`operation.docstringStandard` SSOT 의 9 섹션 정의 부합:
    사람용 8: Capabilities · Args · Returns · Example · Guide · SeeAlso · Requires · AIContext
    LLM용 1: ## LLM Specifications (안 6 sub-key)

본 audit 은 기존 `docstring4Section.py` (Args/Returns/Example/Raises) 의 **상위집합** —
새 5 sub-section + 1 Specifications = 6 sub-baseline 분리 검사:
    docstringCapabilities.json
    docstringGuide.json
    docstringSeeAlso.json
    docstringRequires.json
    docstringAIContext.json
    docstringSpecifications.json

Args/Returns/Example/Raises 는 기존 `docstring4Section.py` 관할 — 중복 검사 회피.

다른 세션의 `docstring9Section.py` 는 gather/ 한정 + 다른 9 섹션 정의
(`Capabilities/AIContext/Guide/When/How/Requires/Raises/Example/SeeAlso`) — 별개 audit.

mode:
    --mode baseline (default) — 6 baseline 외 new violation 만 fail
    --mode strict — 전 violation fail

P-PR2 (자동 4 섹션 sweep) / P-PR3 (사람 review 5 섹션 + Specifications) 통과마다 축소.
P-PR3 종료 시 6 baseline 모두 0 (strict).
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
_PROVIDERS_SRC = _REPO / "src" / "dartlab" / "providers"
_BASELINE_DIR = _REPO / "scripts" / "audit" / "_baselines"

# ── 6 sub-section keyword set (SSOT docstringStandard.md 부합) ──

_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Capabilities": ("Capabilities:", "Capabilities\n", "기능:", "기능\n"),
    "Guide": ("Guide:", "Guide\n", "가이드:", "가이드\n"),
    "SeeAlso": ("SeeAlso:", "See Also:", "SeeAlso\n", "참고:", "참고\n"),
    "Requires": ("Requires:", "Requires\n", "필요:", "필요\n", "전제:", "전제\n"),
    "AIContext": ("AIContext:", "AI Context:", "AIContext\n", "AI 컨텍스트:"),
    "Specifications": ("LLM Specifications:", "## LLM Specifications", "LLM Specifications\n"),
}

_BASELINE_FILES: dict[str, Path] = {
    section: _BASELINE_DIR / f"docstring{section}.json" for section in _SECTION_KEYWORDS
}


def _hasSection(docstring: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in docstring for kw in keywords)


def _isWrapper(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """단순 wrapper (본문 ≤ 2 stmt + return delegate) — Capabilities/Guide/AIContext 면제."""
    if len(func.body) > 2:
        return False
    last = func.body[-1] if func.body else None
    if isinstance(last, ast.Return) and last.value is not None:
        return True
    return False


def _isPureReturnNone(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """인자 0 + return None — Specifications 도 면제 (side-effect)."""
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


def _scan() -> dict[str, list[str]]:
    """providers/ 안 공개 함수/메서드 docstring → 6 sub-section 별 위반 key list."""
    violations: dict[str, list[str]] = {section: [] for section in _SECTION_KEYWORDS}
    for srcPath in _PROVIDERS_SRC.rglob("*.py"):
        if "__pycache__" in srcPath.parts:
            continue
        try:
            tree = ast.parse(srcPath.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        rel = str(srcPath.relative_to(_REPO).as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            docstring = ast.get_docstring(node) or ""
            isWrapper = _isWrapper(node)
            isPureNone = _isPureReturnNone(node)
            key = f"{rel}::{node.name}"
            for section, keywords in _SECTION_KEYWORDS.items():
                # 면제 조건 — wrapper 는 thin delegate 라 의미 X (SeeAlso/Requires 포함)
                if isWrapper and section in {"Capabilities", "Guide", "AIContext", "SeeAlso", "Requires"}:
                    continue
                if isPureNone and section == "Specifications":
                    continue
                if not _hasSection(docstring, keywords):
                    violations[section].append(key)
    return {section: sorted(set(keys)) for section, keys in violations.items()}


def _loadBaseline(section: str, path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("violations", []))


def main() -> int:
    parser = argparse.ArgumentParser(description="providers docstring 9-section (sub) audit")
    parser.add_argument("--mode", choices=["baseline", "strict"], default="strict")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    violations = _scan()
    total = sum(len(v) for v in violations.values())
    print("=== docstring 9-section sub audit (P-PR 트랙) — src/dartlab/providers ===")
    for section, items in violations.items():
        print(f"  {section}: {len(items)} 건")
    print(f"  total: {total} 건")

    if args.update_baseline:
        _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        for section, items in violations.items():
            path = _BASELINE_FILES[section]
            path.write_text(
                json.dumps(
                    {
                        "_note": (
                            f"P-PR 트랙 — providers/ docstring {section} sub-section baseline. "
                            "P-PR2 (자동 sweep) / P-PR3 (사람 review) 통과마다 축소. P-PR3 종료 시 strict 0."
                        ),
                        "violations": items,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        print("\nbaseline 6 갱신 완료.")
        return 0

    fail = False
    if args.mode == "strict":
        for section, items in violations.items():
            if items:
                fail = True
                print(f"\n=== STRICT FAIL — {section} {len(items)} 건 ===")
                for k in items[:10]:
                    print(f"  {k}")
        if not fail:
            print("\n=== STRICT PASS ===")
        return 1 if fail else 0

    # baseline 모드
    for section, items in violations.items():
        allowed = _loadBaseline(section, _BASELINE_FILES[section])
        new = [k for k in items if k not in allowed]
        if new:
            fail = True
            print(f"\n=== baseline 외 신규 위반 ({section}, {len(new)} 건) ===")
            for k in new[:10]:
                print(f"  {k}")

    if not fail:
        print("\n=== baseline 안 — 통과 ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
