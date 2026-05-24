# Architecture Diagrams — 3 도식

> dartlab 아키텍처를 *세 시각* 으로 보는 다이어그램 세트. Mermaid 텍스트 — GitHub / VSCode / 대부분 markdown viewer 가 직접 렌더링.
> SVG export 가 필요한 경우: VSCode 의 Markdown Preview Mermaid Support 또는 `mmdc -i ARCHITECTURE.md -o output.svg`.

---

## 1. 전체 아키텍처 — 4 계층 단방향 + 14 sub-namespace

```mermaid
flowchart TB
    subgraph L4 [L4 소비자]
        AI[ai/<br/>chat-native agent]
        MCP[mcp/<br/>외부 LLM 진입]
        CLI[cli/<br/>dartlab 명령]
        SRV[server/<br/>FastAPI viz]
    end

    subgraph L4ext [표현·전송 헬퍼]
        VIZ[viz/<br/>차트 spec]
        CH[channel/<br/>블로그·SNS]
    end

    subgraph L3 [L3 조합기]
        STORY[story/<br/>8막 인과 + ref]
    end

    subgraph L2 [L2 분석 엔진]
        ANA[analysis/<br/>재무 분석]
        CRD[credit/<br/>Z-score]
        MAC[macro/<br/>사이클]
        QNT[quant/<br/>factor]
        IND[industry/<br/>peer]
    end

    subgraph L15 [L1.5 가공 4 형제]
        SCN[scan/<br/>횡단면]
        FRM[frame/<br/>raw 결합]
        SYN[synth/<br/>매칭·시나리오]
        REF[reference/<br/>매핑·룩업]
    end

    subgraph L1 [L1 raw 생산]
        PRV[providers/<br/>DART · EDGAR]
        GTH[gather/<br/>외부 수집]
    end

    subgraph L0 [L0 primitive]
        CORE[core/<br/>cache · logger · DI · decimal]
    end

    L4 --> L3
    L4 --> L2
    L4ext --> L3
    L3 --> L2
    L2 --> L15
    L15 --> L1
    L1 --> L0
    L2 -.예외만.-> L1

    HF[(HuggingFace<br/>dartlab-data)]
    EXT[(외부 API<br/>DART · EDGAR · FRED · ECOS · KRX · Naver)]

    L1 --> EXT
    L15 -.->|prebuild offline| HF
    L1 -.->|sync online| HF
```

룰:
- 화살표 = 호출 방향. 의존성은 *역방향*.
- L1.5 4 형제 **cross import 금지** (강제: `tests/architecture/test_l15_no_cross_import.py`).
- L2 5 엔진 **상호 import 0** (강제: importlinter).
- L2 → L1 직접 import 는 *L1.5 에 없는 raw 필요 시 예외만*.

---

## 2. Data Flow — XBRL → Polars → 분석 ready

```mermaid
flowchart LR
    subgraph S1 [Sync 단계 - online]
        API[(외부 API)]
        SYNC[".github/scripts/sync/<br/>(DART/EDGAR/FRED/ECOS/KRX)"]
        RAW[(raw parquet<br/>data/_raw/)]
        UPLOAD[bulkUploadHf.py]
        HF[(HuggingFace<br/>eddmpython/dartlab-data)]
    end

    subgraph S2 [Prebuild 단계 - offline]
        DL[hf_hub_download]
        PRE[".github/scripts/prebuild/<br/>(corp profile / macro / industry)"]
        DRV[(derived parquet/json<br/>data/_derived/)]
    end

    subgraph S3 [Runtime - 사용자]
        CMP[Company facade]
        SCAN[scan engine]
        ANL[analysis engine]
        VIZ2[viz / 답변]
    end

    API --> SYNC --> RAW --> UPLOAD --> HF
    HF --> DL --> PRE --> DRV
    DRV --> CMP & SCAN & ANL --> VIZ2

    style S1 fill:#e1f5ff,stroke:#1976d2
    style S2 fill:#fff4e1,stroke:#f57c00
    style S3 fill:#e8f5e9,stroke:#388e3c
```

룰:
- **Sync = online** (외부 API 호출 허용)
- **Prebuild = offline only** (HF 다운로드만, `enforceOffline()` 강제)
- 3 층 가드: 런타임 `core/offlineGuard.py` + AST `test_prebuild_offline.py` + main entry lint
- DART 원본 zip 은 *로컬 임시 보관* (HF 비공개, .gitignore + skip + artifact 제외)

---

## 3. AI Workbench Flow — 5 패스 + evidence/ref

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as ai/agent.py<br/>(chat-native)
    participant Tools as ai/tools/*
    participant Engine as L2 분석 엔진
    participant Refs as ref/evidence
    participant Trace as ai/trace.py<br/>(T11-4)

    User->>Agent: ask "삼성전자 분석"
    Note over Agent: BRIEF — 의도 분해
    Agent->>Trace: observe(BRIEF, intent=...)
    Note over Agent: WORK — 도구 선택
    Agent->>Tools: EngineCall / RunPython / WebSearch
    Tools->>Engine: 실제 호출
    Engine->>Refs: tableRef / valueRef 발급
    Refs-->>Agent: ref 반환
    Agent->>Trace: observe(WORK, refUsed/refProduced)
    Note over Agent: CRITIQUE — ref 검증
    Agent->>Refs: groundingCheck(ref)
    Refs-->>Agent: 검증 결과
    Note over Agent: COMPOSE — 답변 합성
    Agent->>Trace: observe(COMPOSE, sections=...)
    Note over Agent: GATE — evidence 통과 확인
    Agent->>Trace: observe(GATE, requiredEvidence=...)
    Note over Agent: HARVEST — 메모리·노트북 저장
    Agent->>Trace: markFinished() + dumpToJson()
    Agent-->>User: 답변 + 원본 ref
```

룰:
- 본체는 **`ai/agent.py` chat-native** (LLM 자율 tool calling).
- 5 패스는 *옵션 sub-agent* — workbench/loop.py 만 직접 호출.
- **새 5 패스 노드 클래스 추가 금지** (`tests/audit/checkAgentBoundary.py` 가 차단 — T11-5).
- 외부 본문은 **untrusted** — `wrap_external_in_result` 마커 강제.
- 모든 trace 는 `data/_trace/{sessionId}.json` 저장 가능 (T11-4) → ref circularity 검사 (T11-3).

---

## 관련

- [API_FLOWCHART.md](../API_FLOWCHART.md) — 사용자 진입점 의사결정 흐름
- [DEVELOPMENT.md](../DEVELOPMENT.md) — 첫 수정 10분 가이드
- [../../src/dartlab/skills/specs/operation/architecture.md](../../src/dartlab/skills/specs/operation/architecture.md) — Skill OS 아키텍처 SSOT
- [../../src/dartlab/skills/specs/runtime/workbenchEvidenceFlow.md](../../src/dartlab/skills/specs/runtime/workbenchEvidenceFlow.md) — evidence flow 본문
- [../../TODO.md](../../TODO.md) T10-1 트랙
