---
id: engines.viz.mermaidDiagram
title: Viz - Mermaid 인과 다이어그램
kind: curated
scope: builtin
status: observed
category: engines
purpose: 숫자 표로만 설명하기 어려운 충격 전파, 공시 변화, 지배구조 연결, thesis falsifier 경로를 Mermaid diagram 으로 제한적으로 표현한다.
whenToUse:
  - Mermaid diagram
  - 인과 다이어그램
  - 충격 전파
  - 지배구조 network
  - thesis path
inputs:
  - nodes
  - edges
  - node evidence refs
  - diagram title
outputs:
  - mermaid source
  - diagramRef
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.viz
sourceRefs:
  - dartlab://skills/engines.viz.mermaidDiagram
requiredEvidence:
  - node
  - edge
  - evidenceRef
expectedOutputs:
  - Mermaid graph LR source
  - 인과 경로 설명
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
failureModes:
  - 근거 없는 관계를 edge 로 그림
  - 데이터 모양과 다이어그램 양식 불일치 (예: 수렴인데 LR 양식, 트리인데 가로)
  - 노드 라벨에 긴 설명·문장을 넣어 다이어그램이 텍스트 박스가 됨
  - flowchart LR 인데 노드 5 개 초과 → 가로로 너무 길어 채팅 폭 (720 px) 잘림
  - 결정 분기를 사각형 노드로만 그려 양식 식별 안 됨 (다이아몬드 미사용)
forbidden:
  - 근거 없는 edge 금지
  - 데이터 모양 분류 (A~F 양식) 없이 그리기 금지 → 항상 본문 구조 → 양식 매핑부터
  - flowchart LR 양식에서 노드 5 개 초과 금지 (5 초과면 TD 로 작성)
  - 노드 라벨 12 자 초과 금지 (긴 설명은 본문 텍스트에)
  - 노드에 마침표·줄바꿈·`<br/>` 사용 금지 (라벨은 키워드 + 숫자/단위만)
  - 수치나 문서 근거가 없는 thesis impact 단정 금지
examples:
  - 금리 상승 → 차입비용 → 이자보상배율 path
  - 공시 tone 변화 → 회계 리스크 → thesis risk path
linkedSkills:
  - engines.viz
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-16'
---

## 양식 선택 — 데이터 모양 → 다이어그램 모양

**먼저 본문에 그릴 내용의 구조를 분류한다. 구조가 적합 다이어그램을 결정한다.**

### A. 선형 인과 사슬 (A → B → C, 3-4 단계)
양식: `flowchart TD` (세로). 시간/논리 순서가 자연스럽게 위→아래로 흐른다.
```mermaid
flowchart TD
  A[금리 +100bp] --> B[이자비용 ↑]
  B --> C[ICR 1.2x 하락]
```
- 노드 3~4 개. 단방향 화살표.
- LR 양식 안 쓴다 (채팅 폭 절약).

### B. 한 원인 → 여러 결과 (분기, fan-out)
양식: `flowchart TD` 루트 1 개 + 자식 2-4 개.
```mermaid
flowchart TD
  R[WACC ↑]
  R --> A[DCF 가치 ↓]
  R --> B[부채 비용 ↑]
  R --> C[성장 가정 ↓]
```
- 루트 위, 자식 아래 펼침.
- 자식 4 개 초과면 그룹화 (subgraph) 또는 본문 bullet 으로.

### C. 여러 요인 → 한 결과 (수렴, fan-in)
양식: `flowchart TD` 자식 위 → 루트 아래.
```mermaid
flowchart TD
  A[매출 성장 25%] --> S
  B[마진 28.86%] --> S
  C[WACC 10.55%] --> S
  S[자기자본가치 246.16조 원]
```
- 단순 합산·집계·valuation 결론 양식.

### D. 결정 분기 (조건 → 갈래)
양식: `flowchart TD` + 다이아몬드 노드 `{}`.
```mermaid
flowchart TD
  Q{영업CF > 부채상환?}
  Q -->|예| Y[현금흐름 양호]
  Q -->|아니오| N[차환 의존]
```
- 다이아몬드 = 결정. 화살표 라벨 = 분기 조건.
- 결정 ≤ 2 개. 다중 결정은 의사결정 트리 → 별도 비주얼.

### E. 트리 분해 (계층, 부 → 자 → 손)
양식: `flowchart TD`. 최대 3 레벨, 레벨당 자식 ≤ 4.
```mermaid
flowchart TD
  ROE[ROE 18%]
  ROE --> NM[순이익률]
  ROE --> AT[자산회전]
  ROE --> LV[레버리지]
  NM --> GM[매출총이익률]
  NM --> OE[영업비용 비율]
```
- DuPont, Piotroski, 회계 분해 양식.

### F. 네트워크 (방향성 약함, 상호 관계)
양식: `graph` (방향 생략 가능) + subgraph 로 클러스터.
- 지배구조, 거래 네트워크 등. 채팅 양식 안 거의 안 씀 — viz 의 NetworkChart 가 더 적합.

## 노드 / 라벨 양식

| 노드 종류 | 모양 | 라벨 양식 | 예 |
|---|---|---|---|
| 상태/지표 | `[X]` 사각형 | "지표명 값" | `[WACC 10.55%]` |
| 액션/단계 | `(X)` 둥근 | "동사형 단어" | `(데이터 검증)` |
| 결정 | `{X?}` 다이아몬드 | "조건? 양식" | `{ICR ≥ 1.5?}` |
| 결론/출력 | `[[X]]` 이중 | "결론 한 줄" | `[[고평가 판정]]` |

라벨 규칙:
- 12 자 이하. 단어 1-2 개 + 숫자/단위.
- 동사 + 명사 (액션) 또는 명사 + 값 (지표).
- 긴 설명·근거·해석은 본문 텍스트에. 다이어그램은 **포인터** 역할.
- 마침표 / 줄바꿈 안 쓴다 (`<br/>` 도 가급적 피함).

## 방향 선택 결정 규칙

- **기본**: `flowchart TD` (세로, 위→아래).
- `flowchart LR` 허용 조건: 노드 ≤ 4 AND 시간/공정 순서가 명백히 좌→우 인 경우만 (예: "원료 → 가공 → 출하").
- 그 외 모든 경우 TD. 채팅 양식 (폭 720 px) 에 가장 안전.

## 채팅 폭 가이드 (web ask 모드)

- 메시지 폭 ≈ 720 px (`max-w-3xl`). 다이어그램 자연 폭이 이 안에 들어가야 가로 스크롤 / 글씨 찌그러짐 없음.
- TD + 6 노드 + 12 자 라벨 → 자연 폭 약 200~280 px, 높이 자라남 → 안전.
- LR + 5 노드 + 12 자 라벨 → 자연 폭 약 600~700 px → 한계.
- LR + 노드 6 개 이상 → 폭 1000 px 이상 → 절대 안 됨. UI 자동 TD 회전 fallback 있지만 일관성 손상 → 처음부터 TD 로 그릴 것.

## 절차 (작성 순서)

1. 본문에 어떤 구조 (위 A~F) 를 보여줄지 분류.
2. 해당 양식 + 라벨 양식 적용.
3. edge 마다 근거 ref 부여 (`evidenceBinding` 또는 본문 인용).
4. 노드 수 / 라벨 길이 / 방향 self-check.
5. 채팅에서 잘릴 위험 있으면 부 다이어그램 2 개로 쪼개거나 본문 bullet 으로 강등.

## 공개 호출 방식

```python
from dartlab.viz import emit_diagram

source = "graph LR\n  A[금리 +100bp] --> B[이자비용 증가]\n  B --> C[ICR 하락]"
emit_diagram("mermaid", source)
```

## 호출 동작

- 입력 view 또는 rows 를 검산 가능한 ChartSpec 으로 변환한다.
- `evidenceBinding` 또는 `evidenceIds` 가 없으면 emit 하지 않는다.
- 데이터가 부족하면 값을 추정하지 않고 표, coverage note, 또는 bullet path 로 낮춘다.

## 대표 반환 형태

- `dict` ChartSpec: `chartType`, `title`, `series` 또는 `data`, `categories`, `evidenceBinding`, `meta`.
- Mermaid 계열은 diagram source 와 node/edge evidence refs 를 함께 남긴다.

## 기본 검증

- diagram 의 모든 edge 가 answer claim 또는 evidence ref 로 되짚어져야 한다.
- Mermaid 는 설명을 대체하지 않고 메커니즘 섹션에만 배치한다.
