"""마스터 플랜 트랙 2 PR-O6 — memory recall A/B 측정 harness.

cryptic-discovering-kettle.md PR-O6. ``_injectPastContextIfAvailable`` ON/OFF
양쪽 동일 질문 N 회 실행 → ref 수 + token 추정 + 정답률 비교.

목적
-----
recall 활성 (stockCode kwargs 전달 → ``fetchPastContext`` 호출 → system prompt 에
"## 과거 결정 회고" 블록 부착) 이 실제로 답변 품질을 올리는지 정량 측정. ON 일 때
system prompt 가 더 길어 input token 비용 발생하나, LLM 이 과거 매핑/결정 인용해
ref 수 증가 또는 hallucination 감소 효과가 있어야 정당. trade-off 측정.

기대 결과
---------
- ON: refs 평균 +15%, system prompt 길이 +10~30%
- OFF: 동일 ref 수 또는 미세 감소, system prompt 더 짧음
- 결론 = ON 의 추가 token 가치 평가 (digest cost vs answer quality)

본 harness 는 *scripted* — 실제 LLM 호출 0, ScriptedProvider 패턴으로 결정론. 실제
운영 A/B 는 별도 (DARTLAB_AI_TRACE_DUMP=1 활성 후 1+ 주 누적 데이터 의존).

실행
----
``uv run --no-sync python -X utf8 tests/_attempts/memoryRecallAb.py``

결과
----
2026-05-28 실행 — N=20, scripted 결정론 base case.
- ON  : 평균 refs=1.00, system prompt 평균 길이 16254 자
- OFF : 평균 refs=1.00, system prompt 평균 길이 16028 자
- delta refs=+0.00 (mock past_context 가 ref 생성 변경 안 함 — *제한*: 실제 LLM
  이 과거 맥락 인용 행동 시뮬 못 함). 실제 운영 데이터로 재측정 필요.
- delta length=+226 자 ≈ +57 tokens — 본 harness 가 cost overhead 만 정량화.

결론
----
scripted harness 는 cost overhead (system prompt 길이) 정량화만 가능. 답변 품질
delta 는 real LLM 운영 trace 1+ 주 필요. 본 harness 는 *infra* 박힘 — 운영 데이터
도착 시 즉시 재실행 + 결론 갱신 위치 박혀있음 (feedback_attempts_docstring_results.md
강행).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# repo root import path 확보 — uv run 호환
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from dartlab.ai.agent import runAgent  # noqa: E402
from dartlab.ai.providers import ProviderTurn, ToolCall  # noqa: E402


class _ScriptedProvider:
    """결정론 ProviderTurn 리플레이."""

    class _Cfg:
        provider = "scripted"
        model = "scripted-model"

    def __init__(self, turns: list[ProviderTurn]) -> None:
        self.config = self._Cfg()
        self._turns = list(turns)
        self._index = 0
        self.lastSystemLen = 0

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        # system prompt 길이 측정 — recall ON 시 "## 과거 결정 회고" 블록 누적 확인.
        for m in messages:
            if m.get("role") == "system":
                self.lastSystemLen = len(str(m.get("content", "")))
                break
        if self._index >= len(self._turns):
            return ProviderTurn(content="", toolCalls=[], raw=None)
        t = self._turns[self._index]
        self._index += 1
        return t


def _runOnce(*, recallOn: bool, monkeypatchPast: Any) -> dict[str, Any]:
    """한 번 question 실행 → metrics 반환.

    recallOn=True: kwargs 에 stockCode 전달 + fetchPastContext mock.
    recallOn=False: kwargs 없음 → past_context 블록 부재.
    """
    if recallOn:
        monkeypatchPast(lambda code, market="KR": "[past] 005930 매수 결정 2026-04-15 — alpha +3.2%")
    else:
        monkeypatchPast(lambda code, market="KR": "")

    def fake_execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "summary": "ok",
            "refs": [
                {
                    "id": "x:1",
                    "kind": "valueRef",
                    "title": "v",
                    "source": "x",
                    "payload": {"value": 1, "confidence": 50},
                }
            ],
            "data": {},
            "error": None,
        }

    import dartlab.ai.agent as agent_mod  # noqa: PLC0415

    original_execute = agent_mod.executeTool
    agent_mod.executeTool = fake_execute  # type: ignore[assignment]
    try:
        provider = _ScriptedProvider(
            [
                ProviderTurn(
                    content="",
                    toolCalls=[ToolCall(id="t1", name="ReadSkill", args={"query": "x"})],
                    raw=None,
                ),
                ProviderTurn(content="답변", toolCalls=[], raw=None),
            ]
        )
        kwargs: dict[str, Any] = {"stockCode": "005930"} if recallOn else {}
        events = list(runAgent("삼성전자 분석", provider=provider, toolNames=("ReadSkill",), **kwargs))
        done = next((e for e in events if e.kind == "done"), None)
        ref_count = len(done.data.get("refs", [])) if done else 0
        return {"refs": ref_count, "systemLen": provider.lastSystemLen}
    finally:
        agent_mod.executeTool = original_execute  # type: ignore[assignment]


def _monkeypatchPastFactory():
    """fetchPastContext 모듈 함수를 in-process replace 하는 monkeypatch 헬퍼."""
    saved: dict[str, Any] = {}

    def setter(fn: Any) -> None:
        from dartlab.ai.memory import wiring  # noqa: PLC0415

        if "orig" not in saved:
            saved["orig"] = wiring.fetchPastContext
        wiring.fetchPastContext = fn  # type: ignore[assignment]

    def restorer() -> None:
        if "orig" in saved:
            from dartlab.ai.memory import wiring  # noqa: PLC0415

            wiring.fetchPastContext = saved["orig"]  # type: ignore[assignment]

    return setter, restorer


def main(n: int = 20) -> None:
    """N 회 × ON/OFF 실행 → 평균 ref 수 + system prompt 길이 비교."""
    setter, restorer = _monkeypatchPastFactory()
    try:
        on_results = [_runOnce(recallOn=True, monkeypatchPast=setter) for _ in range(n)]
        off_results = [_runOnce(recallOn=False, monkeypatchPast=setter) for _ in range(n)]
    finally:
        restorer()

    def _avg(results: list[dict[str, Any]], key: str) -> float:
        if not results:
            return 0.0
        return sum(r[key] for r in results) / len(results)

    on_refs = _avg(on_results, "refs")
    off_refs = _avg(off_results, "refs")
    on_len = _avg(on_results, "systemLen")
    off_len = _avg(off_results, "systemLen")
    print(f"N={n} (scripted, 결정론)")
    print(f"  ON  refs={on_refs:.2f}  systemLen={on_len:.0f}")
    print(f"  OFF refs={off_refs:.2f}  systemLen={off_len:.0f}")
    print(f"  delta refs={on_refs - off_refs:+.2f}  delta length={on_len - off_len:+.0f} chars")
    print(
        "  결론: scripted harness 는 cost overhead (system prompt 길이) 정량화만 가능. "
        "답변 품질 delta 는 운영 trace 1+ 주 필요."
    )


if __name__ == "__main__":
    main(n=int(os.getenv("DARTLAB_RECALL_AB_N", "20")))
