"""AI 엔진 boundary lint — graph 강박 회귀 패턴 감지.

룰 (memory/feedback_no_graph_regression.md):
- 본체는 ai/agent.py (runAgent — chat-native + LLM 자율 tool calling)
- WorkbenchLoop 는 옵션 sub-agent — agent_gateway.py / kernel.py 만 직접 호출
- 새 5 패스 패턴 모듈 / *Loop / *Graph 클래스 추가 금지
- "graph 강제" / "verify 강제" / "회귀 가드" 같은 자기 인식 단어 등장 시 검토

경고만 — 점진 마이그레이션. CI / pre-commit 추적용.

Usage:
    uv run python -X utf8 scripts/dev/checkAgentBoundary.py
    uv run python -X utf8 scripts/dev/checkAgentBoundary.py --strict   # exit 1 if violations
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "dartlab"

# WorkbenchLoop 직접 호출 허용 파일 (agent_gateway / kernel / workbench 내부).
_ALLOWED_WORKBENCH_CALLERS = {
    SRC / "server" / "agent_gateway.py",
    SRC / "ai" / "kernel.py",
}

# workbench 모듈에 *기존* 파일들. 새 파일 추가 시 경고.
_KNOWN_WORKBENCH_FILES = {
    "__init__.py",
    "SSOT.md",
    "brief.py",
    "chatNative.py",
    "compose.py",
    "critique.py",
    "gate.py",
    "harvest.py",
    "heuristic.py",
    "intent.py",
    "loop.py",
    "passes.py",
    "prompts.py",
    "runner.py",
    "scratchpad.py",
    "state.py",
    "targets.py",
    "work.py",
}

# 새 코드에 등장하면 검토 필요한 자기 인식 단어.
_REGRESSION_KEYWORDS = (
    "graph 강제",
    "verify 강제",
    "5 패스 강제",
    "6 막 강제",
    "회귀 가드",
    "anti-pattern",
)


def _check_workbench_direct_calls(violations: list[str]) -> None:
    """`WorkbenchLoop()` 직접 호출 — 허용 파일 외 발견 시 경고."""
    for path in SRC.rglob("*.py"):
        if path.resolve() in {p.resolve() for p in _ALLOWED_WORKBENCH_CALLERS}:
            continue
        if "workbench" in str(path).replace("\\", "/").split("dartlab/", 1)[-1]:
            # workbench 디렉터리 내부는 정당
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "WorkbenchLoop()" in stripped and not stripped.startswith(("#", "import", "from")):
                rel = path.relative_to(ROOT)
                violations.append(
                    f"{rel}:{line_no} — WorkbenchLoop() 직접 호출. agent.py runAgent / ai.kernel.ask 사용 권장."
                )


def _check_new_workbench_modules(violations: list[str]) -> None:
    """workbench/ 안의 *새 모듈* 감지 — 5 패스 패턴 회귀 가능성."""
    workbench_dir = SRC / "ai" / "workbench"
    if not workbench_dir.is_dir():
        return
    for path in workbench_dir.iterdir():
        if not path.is_file():
            continue
        if path.name in _KNOWN_WORKBENCH_FILES:
            continue
        rel = path.relative_to(ROOT)
        violations.append(
            f"{rel} — 새 workbench 모듈. 5 패스 패턴 회귀 가능성. memory/feedback_no_graph_regression.md 검토."
        )


def _check_new_loop_classes(violations: list[str]) -> None:
    """ai/ 안 *Loop / *Graph / *Kernel 클래스 새로 추가 감지.

    범위 = ai/ 한정 — analysis/graph (Causal Graph, 자료구조) 등 *AI 강박과 무관* 한 graph 자료구조 제외.
    """
    ai_dir = SRC / "ai"
    if not ai_dir.is_dir():
        return
    for path in ai_dir.rglob("*.py"):
        if "workbench" in str(path).replace("\\", "/"):
            continue
        if "providers" in str(path).replace("\\", "/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith("class "):
                continue
            class_name = stripped.split(":", 1)[0].split("(", 1)[0].replace("class ", "").strip()
            if class_name.endswith(("Loop", "Graph", "Kernel")) and class_name != "WorkbenchLoop":
                rel = path.relative_to(ROOT)
                violations.append(
                    f"{rel}:{line_no} — class {class_name} (Loop/Graph/Kernel 패턴). graph 강박 회귀 가능성."
                )


def _check_regression_keywords(violations: list[str]) -> None:
    """자기 인식 단어 등장 — 새 graph 패턴 추가 시 자주 함께 등장."""
    for path in SRC.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # 룰 인용 / system prompt 인용 / 회귀 방지 docstring 은 허용.
        if "feedback_no_graph_regression" in text or "회귀 방지" in text or "DARTLAB_CHAT_SYSTEM" in text:
            continue
        for keyword in _REGRESSION_KEYWORDS:
            if keyword in text:
                rel = path.relative_to(ROOT)
                violations.append(f"{rel} — '{keyword}' 표현 발견. memory/feedback_no_graph_regression.md 검토.")
                break


def main() -> int:
    violations: list[str] = []
    _check_workbench_direct_calls(violations)
    _check_new_workbench_modules(violations)
    _check_new_loop_classes(violations)
    _check_regression_keywords(violations)

    strict = "--strict" in sys.argv

    if not violations:
        print("[agent-boundary] OK — 모든 룰 통과.")
        return 0

    print(f"[agent-boundary] 위반 {len(violations)} 건:\n")
    for v in violations:
        print(f"  - {v}")
    print("\n룰 본문: memory/feedback_no_graph_regression.md")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
