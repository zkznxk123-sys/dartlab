"""모듈 import 사이클 검출 — 양방향 cycle 만 차단 (단방향 허용).

정책 SSOT: src/dartlab/skills/specs/operation/architecture.md

import-linter 의 layers contract 가 동급 sibling 단방향 허용을 깔끔히 표현하지
못해 별도 보조 도구로 양방향 cycle 만 검출한다. AST 로 lazy import (함수 내부
import) 까지 추적하여 import-linter 가 놓치는 케이스 보완.

검사 대상:
    src/dartlab/ 안 모든 .py 파일의 dartlab.* 1 차 패키지 import
    (dartlab.analysis.X.Y → dartlab.macro.Z 는 dartlab.analysis → dartlab.macro edge).

Self-loop (같은 패키지 내부 import) 는 무시.
양방향 (A → B, B → A 동시 존재) 만 cycle 로 보고. 3+ 모듈 cycle 은 networkx 사용 시 추가 검출.

실행:
    python -X utf8 scripts/audit/cycleScan.py            # 검사 (CLI 기본 = exit 0 경고 모드)
    python -X utf8 scripts/audit/cycleScan.py --strict   # cycle 발견 시 exit 2 (CI 용)

종료 코드:
    0 — cycle 0 건 (또는 --strict 미지정)
    2 — cycle ≥ 1 건 (--strict)
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"

# dartlab 1 차 패키지 (dartlab.<X> 단위 노드)
PRIMARY_PACKAGES: tuple[str, ...] = (
    "core",
    "gather",
    "scan",
    "search",
    "analysis",
    "credit",
    "macro",
    "quant",
    "industry",
    "story",
    "company",
    "ai",
    "viz",
    "dashboard",
    "mcp",
    "server",
    "mappers",
    "providers",
    "channel",
    "cli",
    "skills",
    "ui",
)


def _modulePath(p: Path) -> str | None:
    """src/dartlab/<X>/Y/Z.py → 'dartlab.X' (1 차 패키지 단위) 변환."""
    try:
        rel = p.resolve().relative_to(SRC).with_suffix("").as_posix()
    except ValueError:
        return None
    parts = rel.split("/")
    if not parts:
        return None
    head = parts[0]
    if head not in PRIMARY_PACKAGES:
        return None
    return f"dartlab.{head}"


def _toPrimary(modName: str) -> str | None:
    """import target 문자열에서 dartlab.<X> 1 차 패키지만 추출."""
    if not modName.startswith("dartlab."):
        return None
    parts = modName.split(".")
    if len(parts) < 2:
        return None
    head = parts[1]
    if head not in PRIMARY_PACKAGES:
        return None
    return f"dartlab.{head}"


def _extractImports(source: str) -> set[str]:
    """AST 안 모든 import (top-level + lazy 함수내) 에서 dartlab.* 1 차 패키지 set."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = _toPrimary(alias.name)
                if pkg:
                    out.add(pkg)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            mod = node.module or ""
            pkg = _toPrimary(mod)
            if pkg:
                out.add(pkg)
    return out


def _buildGraph() -> dict[str, set[str]]:
    """src/dartlab 전수 스캔 → {srcPkg: {dstPkg, ...}} edge 그래프."""
    graph: dict[str, set[str]] = defaultdict(set)
    for py in SRC.rglob("*.py"):
        if py.name.startswith("_generated"):
            continue
        src = _modulePath(py)
        if not src:
            continue
        try:
            source = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for dst in _extractImports(source):
            if dst == src:
                continue
            graph[src].add(dst)
    return graph


def _findCycles(graph: dict[str, set[str]]) -> tuple[list[tuple[str, str]], list[tuple[str, ...]]]:
    """양방향 cycle (2-cycle) + 3+ 모듈 cycle 추출. 3+ 는 sorted-key dedup."""
    twoCycles: set[tuple[str, str]] = set()
    for src, dsts in graph.items():
        for dst in dsts:
            if src in graph.get(dst, set()):
                pair = tuple(sorted([src, dst]))
                twoCycles.add(pair)
    longerSet: set[tuple[str, ...]] = set()
    try:
        import networkx as nx

        G = nx.DiGraph()
        for src, dsts in graph.items():
            for dst in dsts:
                G.add_edge(src, dst)
        for cyc in nx.simple_cycles(G):
            if len(cyc) > 2:
                longerSet.add(tuple(sorted(cyc)))
    except ImportError:
        pass
    return sorted(twoCycles), sorted(longerSet)


def _print2Cycles(cycles: list[tuple[str, str]]) -> None:
    """2-cycle (양방향 cycle) 출력 — 진짜 차단 대상."""
    for a, b in cycles:
        print(f"  - 2-cycle: {a} <-> {b}")


def _printLongerCycles(cycles: list[tuple[str, ...]], maxShow: int = 10) -> None:
    """3+ 모듈 cycle — 상위 maxShow 만 표시 (정보성). 보통 2-cycle 의 합성."""
    if not cycles:
        return
    print(f"\n  3+ 모듈 cycle {len(cycles)} 종 (상위 {min(maxShow, len(cycles))} 만 표시):")
    for cyc in cycles[:maxShow]:
        print(f"  - {len(cyc)}-cycle: {' -> '.join(cyc)} -> {cyc[0]}")
    if len(cycles) > maxShow:
        print(f"  ... ({len(cycles) - maxShow} 종 추가, 2-cycle 해소 시 대부분 자동 정리)")


def main(argv: list[str]) -> int:
    """엔트리포인트 — CLI 옵션 파싱 후 _buildGraph + _findCycles 실행."""
    strict = "--strict" in argv
    graph = _buildGraph()
    twoCycles, longerCycles = _findCycles(graph)
    if not twoCycles and not longerCycles:
        print(f"[cycle-scan] OK — {len(graph)} 패키지 분석, cycle 0 건.")
        return 0
    print(f"[cycle-scan] 양방향 cycle (2-cycle) {len(twoCycles)} 건 — 차단 대상:")
    _print2Cycles(twoCycles)
    _printLongerCycles(longerCycles)
    print(
        "\n정책 SSOT: src/dartlab/skills/specs/operation/architecture.md\n"
        "  - 상하 단방향: L0 ← L1 ← L1.5 ← L2 ← L3 ← L4\n"
        "  - 동급 단방향 허용\n"
        "  - 양방향 cycle 절대금지\n"
        "해소: 한쪽 import 를 story 위임 또는 core 강등 후 재실행."
    )
    return 2 if strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
