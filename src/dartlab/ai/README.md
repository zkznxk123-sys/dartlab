# ai/ — L4 chat-native agent

> dartlab 의 LLM 자율 tool-calling 본체. 사용자 자연어 질문을 받아 dartlab 의 엔진/도구를 자율 호출.
> CLAUDE.md "graph 회귀 금지" 강행규칙 — `agent.py` chat-native 본체 보존, 5 패스 노드 클래스 신설 금지.

---

## 공개 API

| 모듈 | 역할 |
|------|------|
| `ai/agent.py` | chat-native agent (본체) — LLM 자율 tool calling |
| `ai/tools/` | tool 카탈로그 (현재 32 수동 + `_autogen.py` 자동 변환 후속) |
| `ai/trace.py` | AuditCollector — 5 패스 dump JSON round-trip (T11-4) |
| `ai/workbench/` | sub-agent (옵션) — 5 패스 BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST |
| `ai/providers/` | LLM provider (OAuth / API 키) wrapper |
| `ai/memory/` | 세션 메모리 + searchPastSessions |
| `ai/recipes/` | AI 추천 recipe 카탈로그 |
| `ai/settings/` | model resolver / config |

---

## 진입점

```python
import dartlab
result = dartlab.ask("삼성전자 재무건전성")
# → AI 가 Company / analysis / credit / scan 도구 자율 호출
# → 답변 + ref (원본 추적 가능)
```

---

## 룰 (CLAUDE.md 강행)

- **본체는 `agent.py`** — chat-native + LLM 자율 tool calling. 5 패스 노드 클래스 신설 금지.
- **외부 본문은 untrusted** — `wrap_external_in_result` 마커 강제 (T2-5 audit).
- **5 패스 노드 식별자 회귀 가드** — `tests/audit/checkAgentBoundary.py` 가 차단 (T11-5).
- **ref circularity 가드** — `tests/audit/refCircularityCheck.py` (T11-3).

---

## 관련

- [src/dartlab/skills/specs/runtime/workbenchEvidenceFlow.md](../skills/specs/runtime/workbenchEvidenceFlow.md) — evidence flow 본문 SSOT
- [memory/feedback_no_graph_regression.md](../../../) — graph 강박 회귀 가드 룰
- [TODO.md](../../../TODO.md) T11 트랙
- [docs/diagrams/ARCHITECTURE.md](../../../docs/diagrams/ARCHITECTURE.md) — 워크벤치 sequence 도식
