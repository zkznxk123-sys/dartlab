"""테스트 강제 게이트 — Track 6 (src/ 새 함수 vs tests/ 참조).

본 게이트 SSOT — [tests/POLICY.md](../../tests/POLICY.md) §5 Track 5.

src/dartlab/**/*.py 의 새 함수가 추가될 때 tests/ 에 해당 함수가 참조되는지
확인한다. 누락 시 warning (Phase 1: warning-only). 부드러운 도입 1 개월 후
fail 전환 예정 (2026-Q3).

사용:
    # 변경된 파일만 검사 (PR 모드)
    uv run python -X utf8 tests/audit/testCoverageGate.py --diff origin/master

    # 전체 검사 (nightly 모드)
    uv run python -X utf8 tests/audit/testCoverageGate.py --all

    # warning 만 (default) — fail 차단 트리거 옵션
    uv run python -X utf8 tests/audit/testCoverageGate.py --diff origin/master --fail-on-missing

예외 룰 (테스트 강제 안 함):
    - _private (언더스코어 prefix)
    - cli/main.py 진입점 (e2e 으로 간접 검증)
    - server/api/* (HTTP 핸들러 — realData 간접)
    - providers/*/openapi/* (네트워크 호출 — VCR 카세트 간접)
    - viz/charts/*, viz/display/* (시각화 — snapshot 간접)
    - mcp/* (외부 protocol — 별도 contract test)
    - ai/audit/* (개발자 전용)
    - __init__.py
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src" / "dartlab"
_TESTS = _REPO / "tests"

# 테스트 강제 안 하는 경로 prefix (relative to src/dartlab).
_EXEMPT_PATH_PREFIXES = (
    "cli/main.py",
    "cli/parser.py",
    "cli/rendering.py",
    "cli/services/",
    "cli/commands/",
    "server/api/",
    "server/web.py",
    "providers/dart/openapi/",
    "providers/edgar/openapi/",
    "providers/edinet/openapi/",
    "providers/dart/docs/viewer",
    "viz/charts/",
    "viz/display/",
    "viz/generators.py",
    "viz/plotly.py",
    "viz/network.py",
    "channel/adapters/",
    "channel/devtunnel.py",
    "mcp/",
    "ai/audit/",
    "ai/providers/",
)


@dataclass
class MissingCoverage:
    src_path: str
    func_name: str
    line: int


@dataclass
class Report:
    checked_files: int = 0
    total_public_funcs: int = 0
    missing: list[MissingCoverage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "checked_files": self.checked_files,
            "total_public_funcs": self.total_public_funcs,
            "missing_count": len(self.missing),
            "missing": [{"path": m.src_path, "func": m.func_name, "line": m.line} for m in self.missing],
        }


def _isExempt(rel_path: str) -> bool:
    """exempt 경로 확인."""
    if rel_path.endswith("__init__.py"):
        return True
    if rel_path.endswith("/_reference/") or "/_reference/" in rel_path:
        return True
    if "/_backup/" in rel_path:
        return True
    for prefix in _EXEMPT_PATH_PREFIXES:
        if rel_path.startswith(prefix):
            return True
    return False


def _extractPublicFunctions(src_file: Path) -> list[tuple[str, int]]:
    """src/dartlab/X.py 의 top-level + class-level public def 목록 (name, lineno)."""
    try:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            name = node.name
            # private (언더스코어) 제외
            if name.startswith("_"):
                continue
            # Protocol method / abstract — 함수 본문이 ellipsis/pass 만이면 제외
            if len(node.body) == 1:
                stmt = node.body[0]
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                    if stmt.value.value is Ellipsis:
                        continue
                if isinstance(stmt, ast.Pass):
                    continue
            # abstractmethod / Protocol 데코레이터 제외
            decorators = {
                d.attr if isinstance(d, ast.Attribute) else (d.id if isinstance(d, ast.Name) else "")
                for d in node.decorator_list
            }
            if "abstractmethod" in decorators or "overload" in decorators:
                continue
            out.append((name, node.lineno))
    return out


def _grepTests(func_name: str) -> bool:
    """tests/ 안에서 func_name 참조 확인 — substring grep.

    완전 정확하지 않지만 (예: foo 가 다른 모듈에도 있으면 false-positive),
    부드러운 도입 단계의 휴리스틱으로 충분. 정확성은 Phase 3 강화.
    """
    for test_file in _TESTS.rglob("test_*.py"):
        try:
            content = test_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if func_name in content:
            return True
    return False


def _changedSrcFiles(diff_ref: str) -> list[Path]:
    """git diff --name-only diff_ref...HEAD — src/dartlab/**/*.py 만."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{diff_ref}...HEAD"],
            cwd=_REPO,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"⚠ git diff 실패: {e.stderr}", file=sys.stderr)
        return []

    out: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("src/dartlab/") or not line.endswith(".py"):
            continue
        p = _REPO / line
        if p.exists():
            out.append(p)
    return out


def _allSrcFiles() -> list[Path]:
    return sorted(_SRC.rglob("*.py"))


def runGate(files: list[Path]) -> Report:
    report = Report()
    for src_file in files:
        rel = str(src_file.relative_to(_SRC)).replace("\\", "/")
        if _isExempt(rel):
            continue
        funcs = _extractPublicFunctions(src_file)
        if not funcs:
            continue
        report.checked_files += 1
        report.total_public_funcs += len(funcs)
        for name, line in funcs:
            if not _grepTests(name):
                report.missing.append(MissingCoverage(src_path=rel, func_name=name, line=line))
    return report


def _loadBaseline(baseline_path: Path) -> set[tuple[str, str]]:
    """baseline JSON 에서 (path, func_name) 집합 추출 — 기존 부채.

    PowerShell `Out-File -Encoding utf8` 는 BOM 을 붙이므로 utf-8-sig 로 읽어 흡수.
    """
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    return {(m["path"], m["func"]) for m in data.get("missing", [])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--diff", metavar="REF", help="git diff REF...HEAD 의 변경 파일만 검사")
    group.add_argument("--all", action="store_true", help="src/dartlab 전체 검사 (nightly 모드)")
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="누락 발견 시 exit 1 (default: warning-only, Phase 2 도입 시 활성)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=_REPO / "tests" / "audit" / "_baselines" / "testCoverage.json",
        help="baseline JSON 경로. 기존 누락은 면제, 신규만 fail (default 첨부 파일).",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="baseline 무시 — 모든 누락 보고 (전체 부채 ledger 갱신용)",
    )
    parser.add_argument("--json", action="store_true", help="JSON 결과 출력")
    parser.add_argument("--limit", type=int, default=20, help="missing 출력 limit (default 20)")
    args = parser.parse_args(argv)

    if args.diff:
        files = _changedSrcFiles(args.diff)
        if not files:
            print("✓ 변경된 src/dartlab/*.py 없음 — 게이트 skip")
            return 0
    else:
        files = _allSrcFiles()

    report = runGate(files)

    # Baseline diff — 기존 누락 면제, 신규만 fail 대상
    baseline = set() if args.no_baseline else _loadBaseline(args.baseline)
    new_missing = [m for m in report.missing if (m.src_path, m.func_name) not in baseline]
    grandfathered = [m for m in report.missing if (m.src_path, m.func_name) in baseline]

    if args.json:
        out = report.to_dict()
        out["baseline_count"] = len(baseline)
        out["grandfathered_count"] = len(grandfathered)
        out["new_missing_count"] = len(new_missing)
        out["new_missing"] = [{"path": m.src_path, "func": m.func_name, "line": m.line} for m in new_missing]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"검사 파일: {report.checked_files}")
        print(f"공개 함수: {report.total_public_funcs}")
        print(f"테스트 누락 (전체): {len(report.missing)}")
        print(f"  - baseline grandfathered: {len(grandfathered)}")
        print(f"  - 신규 누락: {len(new_missing)}")
        if new_missing:
            print("\n신규 누락 상위 (본 PR 차단 대상):")
            for m in new_missing[: args.limit]:
                print(f"  - {m.src_path}:{m.line}  {m.func_name}")
            if len(new_missing) > args.limit:
                print(f"  ... 외 {len(new_missing) - args.limit} 종 더")

    # 신규 누락만 fail 대상 (baseline 부채는 별도 quota 트랙)
    if new_missing and args.fail_on_missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
