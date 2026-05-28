"""마스터 플랜 트랙 4 — agent.runAgent end-to-end 시나리오.

각 시나리오 = _ScriptedProvider 패턴으로 mock LLM 응답 정의 + runAgent 호출 →
TraceEvent 시퀀스 assertion. 외부 LLM 의존 0 — 결정론.
"""
