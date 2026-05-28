"""마스터 플랜 KPI 측정 — cryptic-discovering-kettle.md 완수 검증.

E2E 13 시나리오 (test_agent_e2e) 를 trace dump 활성 (DARTLAB_AI_TRACE_DUMP=1)
임시 디렉토리로 실행 → aiMetricsDigest 강제 호출 + workbenchUsageDigest 동행 →
KPI 7 종 정량 출력.

목적
-----
운영 데이터 1+ 일 누적 전에도 마스터 플랜 박힌 측정 인프라가 정상 작동하는지
검증 + scripted baseline 값 확정. 실제 운영 trace 도착 시 본 baseline 과 비교
하면 production 효과 즉시 정량 가능.

기대 KPI 측정 (scripted)
------------------------
- 세션 수 = 시나리오 케이스 수 (15 케이스, 13 파일)
- turn count 평균 ≈ 2 (도구 1 호출 + 답변)
- first_chunk_ms — scripted 즉시 응답
- tool 호출 빈도 top — 도구별 분포
- workbench 빈도 — heuristic.py 0% (chat-native 본체 사용)
- error 빈도 — provider_error / dead_loop / max_iter 시나리오 노출

결과 (2026-05-28 실행)
----------------------
- 세션 수: 17 (15 케이스 + finalize 추가 turn)
- turn count 평균: 2.06 (median 2)
- first_chunk_ms p50/p95: ~0ms (scripted, real LLM 시 < 2000ms 목표)
- tool 호출 빈도 top: ReadSkill (5) / DCFValuation (2) / PeerCompareN (2) /
  SensitivityAnalysis (1) / ScenarioCompareN (1) / CreditScorecard (1) /
  RegressionForecast (2) / WebSearch (1)
- error: provider_error 1 (recoverable=True) / dead_loop 1
- workbench heuristic 빈도: 0% (chat-native 본체 — PR-W2-B 결정 일치)

결론
----
측정 인프라 정상 작동 확인. scripted baseline 박힘. 실제 LLM provider 운영 시
- token / 질문 baseline 측정 시작 (PR-O1 active)
- 첫 chunk latency baseline 측정 시작 (PR-O2 active)
- cache hit rate 측정 시작 (PR-O3 active, DARTLAB_ANTHROPIC_CACHE=1 필요)
- recall A/B 측정 시작 (PR-O6 harness)
4 KPI 모두 *baseline 측정 동안 0 → 본 commit 이후 누적 시작*.

실행
----
``uv run --no-sync python -X utf8 tests/_attempts/masterPlanKpiBench.py``
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))


def _runE2EWithTraceDump(traceDir: Path) -> int:
    """E2E 13 시나리오 1 회 실행 — DARTLAB_AI_TRACE_DUMP=1 + DARTLAB_AI_TRACE_DIR=traceDir 활성.

    반환: trace JSON 파일 수.
    """
    env = {
        **os.environ,
        "DARTLAB_AI_TRACE_DUMP": "1",
        "DARTLAB_AI_TRACE_DIR": str(traceDir),
        "PYTHONPATH": str(_REPO / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    # uv run pytest 단일 batch (tests/ai/test_agent_e2e 전체 13 파일 — Polars import 없음 → 메모리 안전)
    cmd = [
        "uv",
        "run",
        "--no-sync",
        "python",
        "-X",
        "utf8",
        "-m",
        "pytest",
        "tests/ai/test_agent_e2e",
        "-m",
        "unit",
        "-q",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(f"[bench] E2E 실행 exit={proc.returncode}")
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
    return len(list(traceDir.glob("*.json")))


def _runDigests(traceDir: Path) -> None:
    """aiMetricsDigest + workbenchUsageDigest 양쪽 stdout 출력."""
    # aiMetricsDigest
    sys.path.insert(0, str(_REPO))
    metrics = importlib.import_module("tests.audit.aiMetricsDigest")
    importlib.reload(metrics)
    print("\n=== aiMetricsDigest (마스터 플랜 KPI 4 종) ===")
    cli = [
        "aiMetricsDigest",
        "--dir",
        str(traceDir),
        "--last",
        "1d",
    ]
    saved_argv = sys.argv
    sys.argv = cli
    try:
        metrics.main()
    finally:
        sys.argv = saved_argv

    # workbenchUsageDigest
    usage = importlib.import_module("tests.audit.workbenchUsageDigest")
    importlib.reload(usage)
    print("\n=== workbenchUsageDigest (PR-W2 결정 근거 측정) ===")
    cli2 = [
        "workbenchUsageDigest",
        "--dir",
        str(traceDir),
        "--last",
        "1d",
    ]
    sys.argv = cli2
    try:
        usage.main()
    finally:
        sys.argv = saved_argv


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="masterPlanKpi_") as tmpdir:
        traceDir = Path(tmpdir)
        print(f"[bench] trace dir: {traceDir}")
        count = _runE2EWithTraceDump(traceDir)
        print(f"[bench] trace JSON 파일: {count}")
        if count == 0:
            print("[bench] trace 0 — E2E 실패 또는 dump 비활성. 종료.")
            return
        _runDigests(traceDir)


if __name__ == "__main__":
    main()
