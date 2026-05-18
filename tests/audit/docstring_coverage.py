"""docstring 9 섹션 충족률 측정 — W-C 게이트.

개요
====

공개 함수·메서드의 docstring 이 `operation.code` 규격 (9 섹션) 을 충족하는지
측정한다. skill 급 docstring 은 AI tool schema description 자동 변환의 근거
(operation.opsAsSkills) 이므로 충족률이 엔진별 운영 건전성 지표.

9 섹션
------

1. Summary (첫 줄)
2. Description (섹션 헤더는 선택 — Description 키워드 또는 Summary 다음 설명 문단)
3. Parameters (또는 Args)
4. Returns
5. Raises (선택 — 실제 예외 던지는 함수만)
6. Examples (또는 Example)
7. Notes (선택)
8. Guide (dartlab 고유 — When/How/Verified/Examples 하위)
9. See Also (또는 SeeAlso)

사용
====

전 엔진 커버리지
    uv run python tests/audit/docstring_coverage.py --all

특정 엔진
    uv run python tests/audit/docstring_coverage.py --engine scan --min 80

결과 JSON 저장
    uv run python tests/audit/docstring_coverage.py --all --out data/audit/docstring_coverage.json

종료 코드
    0: 모든 대상 게이트 (--min) 통과
    1: 하나 이상 미달
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 엔진별 코드 루트 매핑 (operation.architecture 기준)
ENGINES: dict[str, list[str]] = {
    "scan": ["src/dartlab/scan"],
    "analysis": ["src/dartlab/analysis"],
    "quant": ["src/dartlab/quant"],
    "credit": ["src/dartlab/credit"],
    "macro": ["src/dartlab/macro"],
    "industry": ["src/dartlab/industry"],
    "gather": ["src/dartlab/gather"],
    "story": ["src/dartlab/story"],
    "ai": ["src/dartlab/ai"],
}

# 9 섹션 regex — 대소문자·한영 alias 수용
# (section name, required, regex)
SECTIONS: list[tuple[str, bool, str]] = [
    # Summary: 첫 줄이 비어있지 않고 period 로 끝 or 한 줄 요약
    ("Summary", True, r"\A\s*\S"),
    # Description: 섹션 헤더 "Description:" 또는 Summary 다음 설명 문단
    ("Description", False, r"(?mi)^\s*(Description|설명)\s*:?$|^\s{0,4}[A-Za-zㄱ-힣].{10,}"),
    # Parameters / Args
    ("Parameters", False, r"(?mi)^\s*(Parameters|Args|매개변수|파라미터)\s*:?$|^\s*Parameters\b"),
    # Returns
    ("Returns", False, r"(?mi)^\s*(Returns|반환|리턴)\s*:?$|^\s*Returns\b"),
    # Raises
    ("Raises", False, r"(?mi)^\s*(Raises|예외)\s*:?$|^\s*Raises\b"),
    # Examples
    ("Examples", False, r"(?mi)^\s*(Examples?|예시|예제|사용례)\s*:?$|^\s*>>>"),
    # Notes
    ("Notes", False, r"(?mi)^\s*(Notes?|주의|참고)\s*:?$"),
    # Guide (dartlab 고유)
    ("Guide", False, r"(?mi)^\s*Guide\s*:?$|^\s*Guide\b"),
    # See Also
    ("SeeAlso", False, r"(?mi)^\s*(See Also|SeeAlso|관련|참조)\s*:?$"),
]

# ─────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────


@dataclass
class FunctionStat:
    path: str
    name: str
    kind: str  # "function" | "method" | "class"
    has_docstring: bool
    sections: dict[str, bool]
    score: int  # 충족 섹션 개수 (0~9)
    ratio: float  # score / 9


@dataclass
class EngineStat:
    engine: str
    total_public: int
    with_docstring: int
    # 9 섹션 평균 충족률 (%)
    avg_ratio: float
    # 축별 최저/최고
    min_ratio: float
    max_ratio: float
    # 각 섹션별 충족 함수 비율 (%)
    section_coverage: dict[str, float]


# ─────────────────────────────────────────────────────────────────
# AST 수집
# ─────────────────────────────────────────────────────────────────


def _iter_public_defs(tree: ast.AST, path: str):
    """공개 함수/메서드/클래스 수집. 이름 `_` 시작 제외."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            kind = "method" if _inside_class(tree, node) else "function"
            yield path, node.name, kind, ast.get_docstring(node)
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            yield path, node.name, "class", ast.get_docstring(node)


def _inside_class(tree: ast.AST, target: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef):
            if target in ast.walk(cls) and target is not cls:
                return True
    return False


def _check_sections(doc: str | None) -> tuple[dict[str, bool], int]:
    if not doc:
        return {name: False for name, _, _ in SECTIONS}, 0
    import re

    hits: dict[str, bool] = {}
    score = 0
    for name, required, pattern in SECTIONS:
        ok = bool(re.search(pattern, doc))
        hits[name] = ok
        if ok:
            score += 1
    return hits, score


# ─────────────────────────────────────────────────────────────────
# Engine walk
# ─────────────────────────────────────────────────────────────────


def _collect_engine(engine: str, roots: list[str]) -> tuple[list[FunctionStat], EngineStat]:
    funcs: list[FunctionStat] = []
    for root in roots:
        base = ROOT / root
        if not base.is_dir():
            continue
        for py in base.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            rel = py.relative_to(ROOT).as_posix()
            for path, name, kind, doc in _iter_public_defs(tree, rel):
                hits, score = _check_sections(doc)
                funcs.append(
                    FunctionStat(
                        path=path,
                        name=name,
                        kind=kind,
                        has_docstring=bool(doc),
                        sections=hits,
                        score=score,
                        ratio=score / len(SECTIONS),
                    )
                )

    total = len(funcs)
    with_doc = sum(1 for f in funcs if f.has_docstring)
    ratios = [f.ratio for f in funcs] if funcs else [0.0]
    section_coverage = {
        name: (sum(1 for f in funcs if f.sections[name]) / total * 100.0) if total else 0.0 for name, _, _ in SECTIONS
    }
    stat = EngineStat(
        engine=engine,
        total_public=total,
        with_docstring=with_doc,
        avg_ratio=(sum(ratios) / len(ratios)) * 100.0 if ratios else 0.0,
        min_ratio=min(ratios) * 100.0 if ratios else 0.0,
        max_ratio=max(ratios) * 100.0 if ratios else 0.0,
        section_coverage=section_coverage,
    )
    return funcs, stat


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────


def _print_stat(stat: EngineStat, verbose: bool = False) -> None:
    print(f"\n── {stat.engine} ──")
    print(f"  public 심볼 수: {stat.total_public}")
    print(f"  docstring 있음: {stat.with_docstring} ({stat.with_docstring / max(stat.total_public, 1) * 100:.1f}%)")
    print(f"  평균 9 섹션 충족률: {stat.avg_ratio:.1f}%  (min {stat.min_ratio:.1f}% / max {stat.max_ratio:.1f}%)")
    if verbose:
        print("  섹션별 충족률:")
        for name, pct in stat.section_coverage.items():
            print(f"    {name:12s}: {pct:5.1f}%")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=list(ENGINES.keys()) + ["all"], default="all")
    ap.add_argument("--all", action="store_true", help="전 엔진 순회")
    ap.add_argument("--min", type=float, default=0.0, help="평균 충족률 게이트 (%). 미달 시 exit 1")
    ap.add_argument("--out", type=Path, default=None, help="결과 JSON 저장 경로")
    ap.add_argument("--verbose", "-v", action="store_true", help="섹션별 커버리지 출력")
    ap.add_argument("--worst", type=int, default=0, help="섹션 점수 낮은 N 개 함수 표시")
    args = ap.parse_args()

    if args.all or args.engine == "all":
        engines = list(ENGINES.keys())
    else:
        engines = [args.engine]

    all_funcs: list[FunctionStat] = []
    stats: list[EngineStat] = []
    for eng in engines:
        funcs, stat = _collect_engine(eng, ENGINES[eng])
        all_funcs.extend(funcs)
        stats.append(stat)
        _print_stat(stat, verbose=args.verbose)

    if args.worst > 0:
        low = sorted(all_funcs, key=lambda f: (f.ratio, f.has_docstring))[: args.worst]
        print(f"\n── 충족률 낮은 {args.worst} 개 심볼 ──")
        for f in low:
            print(f"  [{f.score}/9] {f.kind:8s} {f.path}::{f.name}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "engines": [asdict(s) for s in stats],
            "generated_at_cmd": " ".join(sys.argv),
        }
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n결과 저장: {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")

    # Gate 판정
    exitCode = 0
    if args.min > 0:
        failed = [s for s in stats if s.avg_ratio < args.min]
        if failed:
            print(f"\n[FAIL] {len(failed)} 엔진이 게이트 ({args.min:.1f}%) 미달:")
            for s in failed:
                print(f"  {s.engine}: {s.avg_ratio:.1f}%")
            exitCode = 1
        else:
            print(f"\n[PASS] 전 엔진 게이트 ({args.min:.1f}%) 통과")

    return exitCode


if __name__ == "__main__":
    sys.exit(main())
