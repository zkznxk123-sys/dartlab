# AI Evidence Flow — workbench 5 패스 + ref 추적

> 워크벤치 추론 흐름. 외부 본문 untrusted 가드 + ref 검증 + trace dump.

---

## 5 패스 + ref/evidence flow

```mermaid
flowchart TD
    User[사용자 자연어 질문] --> Agent[ai/agent.py chat-native]

    Agent --> Brief["BRIEF<br/>의도 분해"]
    Brief --> Work["WORK<br/>도구 선택 + 호출"]

    Work --> Tools{도구 선택}
    Tools -->|"단일 호출"| EngineCall[EngineCall]
    Tools -->|"다단 계산"| RunPython[RunPython]
    Tools -->|"외부 본문"| WebSearch["WebSearch<br/>+ wrap_external_in_result"]
    Tools -->|"plugin 호출"| Plugin["loadPlugin / listPlugins"]

    EngineCall --> RefProduced[("ref 발급<br/>tableRef / valueRef")]
    RunPython --> RefProduced
    WebSearch --> ExternalRef[("external ref<br/>untrusted 마커")]
    Plugin --> RefProduced

    RefProduced --> Critique["CRITIQUE<br/>ref 검증 (groundingCheck)"]
    ExternalRef --> Critique

    Critique --> Compose["COMPOSE<br/>답변 합성 + ref 인용"]
    Compose --> Gate["GATE<br/>evidence 통과 확인"]
    Gate --> Harvest["HARVEST<br/>메모리 저장 + dumpToJson"]

    Harvest --> TraceFile[("data/_trace/<br/>{sessionId}.json")]
    Harvest --> Answer[사용자 답변 + ref]

    TraceFile -.->|refCircularityCheck T11-3| Audit[순환 감지 audit]
    TraceFile -.->|metrics workflow T1-2| Metrics[7 신호 수집]

    style ExternalRef fill:#fef2f2,stroke:#991b1b
    style Audit fill:#e0f2fe,stroke:#0369a1
    style Metrics fill:#e0f2fe,stroke:#0369a1
```

---

## untrusted 본문 처리 흐름

```mermaid
flowchart LR
    A[외부 본문<br/>DART/EDGAR/뉴스/웹] --> B{sourceType = external?}
    B -->|예| C[wrap_external_in_result]
    C --> D["[EXTERNAL CONTENT START — untrusted]<br/>본문<br/>[EXTERNAL CONTENT END]"]
    D --> E[LLM 호출 시 마커로 격리]
    E --> F["LLM 이 마커 안 내용을<br/>지시가 아닌 데이터로만 처리"]
    B -->|아니오| G[일반 ref]

    A2[새 gather source 추가] --> H["tests/audit/untrustedWrapAudit.py"]
    H -->|wrap 누락| I[PR 차단]
    H -->|wrap 동행| J[허용]
```

---

## ref circularity 검사 (T11-3)

```mermaid
flowchart LR
    TraceJson[("data/_trace/<br/>{sessionId}.json")] --> Loader[loadFromJson]
    Loader --> Graph[ref 의존 그래프<br/>refProduced → refUsed]
    Graph --> DFS["Tarjan-style DFS<br/>WHITE/GRAY/BLACK"]
    DFS --> Detect{cycle?}
    Detect -->|있음| Alert[순환 검출 + path 보고]
    Detect -->|없음| OK[OK]
    Alert -.->|--strict| FailCI[CI 차단]
```

---

## 룰

- **본체는 `ai/agent.py`** — chat-native + 자율 tool calling. 5 패스 노드 *class 신설 금지* (T11-5 audit).
- **외부 본문 untrusted** — `wrap_external_in_result` 마커 강행 (T2-5 audit).
- **trace 항상 dump 가능** — `AuditCollector.dumpToJson()` (T11-4).
- **ref 순환 0** — `refCircularityCheck.py` (T11-3).
- **graph 강박 회귀 금지** — `checkAgentBoundary.py` 가 5 패스 노드 식별자 12 패턴 차단.

---

## 관련

- [ARCHITECTURE.md](ARCHITECTURE.md) — 4 계층 + 워크벤치 sequence
- [DATA_PIPELINE.md](DATA_PIPELINE.md) — 데이터 흐름
- [../../src/dartlab/ai/agent.py](../../src/dartlab/ai/agent.py)
- [../../src/dartlab/ai/trace.py](../../src/dartlab/ai/trace.py) (T11-4)
- [../../tests/audit/refCircularityCheck.py](../../tests/audit/refCircularityCheck.py) (T11-3)
- [../../tests/audit/untrustedWrapAudit.py](../../tests/audit/untrustedWrapAudit.py) (T2-5)
- [../../tests/audit/checkAgentBoundary.py](../../tests/audit/checkAgentBoundary.py) (T11-5)
