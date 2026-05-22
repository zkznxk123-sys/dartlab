---
id: recipes.macro.scenarioDiagram
title: 경제 시나리오 인과 다이어그램
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: macro.scenario 또는 경제분석 결과를 Mermaid 인과 그래프로 emit 하여 충격 전파 경로를 시각화하는 절차. 트리거 — '시나리오 그래프', '인과 다이어그램', '충격 전파', '경제 흐름도'.
whenToUse:
  - 시나리오 그래프
  - 인과 다이어그램
  - 충격 전파
  - 경제 흐름도
  - mermaid
linkedSkills:
  - engines.macro
  - engines.viz
  - recipes.macro.tailRiskScenarioScan
  - recipes.macro.historicalPositioning
toolRefs:
  - EngineCall
  - RunPython
  - CompileVisual
requiredEvidence:
  - skillRef
  - sourceRef
  - executionRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

gap:
  primary:
    - macro
    - viz
testUniverse:
  market: US
  asOfPolicy: latest
falsifier:
  description: "시나리오 이름 또는 충격 경로가 없으면 다이어그램을 만들지 않는다."
expectedNovelty:
  - scenarioDiagram
  - causalPath
  - visualNarrative
forbidden:
  - 원인과 결과가 검증되지 않은 임의 노드를 추가하지 않는다.
  - 시나리오 다이어그램을 실제 예측 경로로 단정하지 않는다.
  - 너무 많은 노드로 읽기 어려운 그래프를 만들지 않는다.
failureModes:
  - scenario meta에 transmission이 없어 일반 경로를 사용해야 함.
  - 다이어그램이 설명보다 장식으로 쓰임.
  - 조건부 충격 경로를 확률 예측으로 오해.
examples:
  - 2008 금융위기 충격 전파를 다이어그램으로 보여줘
  - 인플레이션 충격이 금리와 신용으로 가는 흐름도
  - 달러 스트레스 인과 그래프
lastUpdated: '2026-05-13'
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
---

## 공개 호출 방식

```python
import dartlab
from dartlab.viz import emitDiagram

scenarioName = "2008 금융위기"
market = "KR"

# 1) 시나리오 meta — 충격 유형·transmission 경로 후보
try:
    scenario = dartlab.macro("scenario", scenarioName, market=market)
except Exception as exc:
    scenario = {"error": str(exc), "meta": {"description": scenarioName, "type": "신용 충격"}}
meta = scenario.get("meta") if isinstance(scenario, dict) else {}
scenarioType = (meta or {}).get("type") or "조건부 충격"
transmission = (meta or {}).get("transmission") or []

# 2) 현재 매크로 환경 — 시나리오 출발점 확인
try:
    rates = dartlab.macro("금리", market=market)
    cycle = dartlab.macro("사이클", market=market)
except Exception:
    rates, cycle = {}, {}

# 3) 메커니즘 노드 6 개 이하 — meta.transmission 있으면 그것, 없으면 default
default_path = [
    (scenarioType, "스프레드·금리 충격 + 200~300bp T+0"),
    ("금융상태 긴축", "TED·신용 스프레드 +150bp T+1Q"),
    ("실물 경기 둔화", "PMI < 48 / 소매판매 -3% YoY T+2Q"),
    ("시장 가격 재평가", "PER 18× → 12× / 장기채 변동성 T+3Q"),
    ("방어/취약 분기", "방어 (현금흐름 안정) -15%p / 취약 (고부채·성장주) -28%p"),
]
nodes = transmission or default_path

# 4) mermaid graph LR — 각 노드 라벨에 *수치 임계* 포함
lines = [f'  A["{scenarioName}"]']
prev_id = "A"
for i, (label, threshold) in enumerate(nodes[:5]):
    nid = chr(ord("B") + i)
    lines.append(f'  {nid}["{label}<br/>{threshold}"]')
    lines.append(f"  {prev_id} --> {nid}")
    prev_id = nid
source = "graph LR\n" + "\n".join(lines)

emitDiagram("mermaid", source, title=f"{scenarioName} 충격 전파")

# 5) 후속 모니터링 표 — 답변 5 단의 핵심 산출물
monitoring = [
    {"지표": "TED spread", "현재값": rates.get("ted"), "임계값": "+200bp", "review": "주간"},
    {"지표": "ISM PMI", "현재값": cycle.get("pmi"), "임계값": "< 48", "review": "월간"},
    {"지표": "신용 스프레드 BBB", "현재값": rates.get("creditSpread"), "임계값": "+150bp", "review": "주간"},
]

emit_result(
    table=monitoring,
    values={"scenarioName": scenarioName, "scenarioType": scenarioType, "nodeCount": len(nodes)},
    date=meta.get("asOf"),
)
```

## 호출 동작 — 5 단 분석 구조

본 recipe 의 답변은 시스템 프롬프트의 분석 5 단 (결론 / 근거 / 메커니즘 / 반례·한계 / 후속 모니터링) 과 1:1 매핑된다. 다이어그램은 *메커니즘 3 단의 시각 형태* 일 뿐, 그 단독 답안이 아니다.

### 1. 결론 도출

시나리오 X 의 *충격 전파 강도* + *영향 섹터 분기* + *시간 horizon* 을 정량 한 문장으로 산출.

좋은 결론 예시:
- "2008 금융위기형 신용 충격은 KR 시장 peak-to-trough -38% (18 개월), 회복 +15 개월. 방어 (현금흐름 안정 + 부채비율 50% 이하) 가 상대 -15%p 우위, 취약 (부동산·리츠·고부채 성장주) 가 -28%p 열위."

금지 — "긍정적 영향", "주의 필요", "심각한 충격" 같은 추상 단어 단독 사용. 반드시 숫자·시점·방향 동반.

### 2. 핵심 근거 수집

3 종 ref 모두 답변에 명시 인용 (`requiredEvidence: skillRef + sourceRef + executionRef`).

- **skillRef**: `engines.macro` (이 recipe 진입점), `engines.macro` (역사 위기 사례), `engines.scan` (방어/취약 섹터 현재 분포). 답변 결론·메커니즘 단에서 *어느 skill 출처* 인지 명시.
- **sourceRef**: `dartlab.macro("scenario", ...)` 가 반환한 시나리오 meta (description / type / transmission / historicalCases). 시점 (asOf) 포함.
- **executionRef**: RunPython 안 계산 결과 (위 monitoring 표·values dict). 답변에 "RunPython 실행 결과: ref:N" 형식 인용.

진입점 엔진: `engines.macro` (axis 별 호출) (시나리오 정의) + `engines.viz` (다이어그램 emit). 도구 호출: `RunPython` (조합 계산) + `CompileVisual` (대안 시각화).

### 3. 메커니즘 분석

원인 → 중간 → 결과 인과 경로를 **6 개 이하** mermaid graph LR 노드로 작성. 각 노드 라벨에 *수치 임계* 부착 (`<br/>` 으로 줄바꿈).

기본 5 단 경로 (transmission meta 없을 때):
1. 초기 충격 — 시나리오 type (신용·금리·환율·정치) + 정량 (`+300bp` / `KRW 1,400`).
2. 금융상태 — TED·credit spread·외환보유고 등 (T+1Q).
3. 실물 — PMI·소매판매·산업생산 (T+2Q).
4. 자산가격 — PER 멀티플 압축·장기채 변동성 (T+3Q).
5. 섹터 분기 — 방어 vs 취약 상대 수익률 (T+4Q+).

노드 간 edge label 에 **시간 지연** (T+1Q / T+2Q) 명시 권장. transmission meta 가 있으면 그 경로 우선 (정확도 ↑).

### 4. 반례·한계

- **Falsifier**: 시나리오 이름 또는 충격 경로 (type/transmission) 가 없으면 다이어그램을 만들지 않는다. type 도 추정 못 하면 "조건부 충격" 중립 레이블로 emit 후 답변에 한계 명시.
- **역사 평균 경로 한계**: 다이어그램은 *과거 평균 transmission* 이라 현 사이클 미반영. 예 — Fed 조기 피벗 시 충격이 단기 (1 quarter) 로 마감, 다이어그램의 T+2Q~T+4Q 단계가 압축됨.
- **확률 단정 금지**: edge "A → B" 는 *조건부 경로* 이지 *확률 예측* 아님. "B 가 반드시 일어난다" 식 답변 금지.
- **노드 수 가드**: 6 개 초과 시 가독성 손실. 더 세분화는 별도 `recipes.macro.tailRiskScenarioScan` 으로 분리.
- **장식화 회피**: 다이어그램이 *설명 보조* 가 아니라 *답변 채우기 장식* 으로 쓰임 — 본문 텍스트가 다이어그램과 같은 정보만 담으면 다이어그램 생략하고 표·텍스트로 답.

### 5. 후속 모니터링

답변 끝에 **모니터링 지표 표** 를 다음 형태로:

| 지표 | 현재값 | 임계값 | 리뷰 주기 |
|---|---|---|---|
| TED spread | (RunPython 결과) | +200bp | 주간 |
| ISM PMI | (RunPython 결과) | < 48 | 월간 |
| 신용 스프레드 BBB | (RunPython 결과) | +150bp | 주간 |

추가 연계 절차:
- 여러 시나리오 정량 비교 → `recipes.macro.tailRiskScenarioScan`
- 역사적 유사 사례 비교 → `recipes.macro.historicalPositioning`
- 차트형 수치 (PER 압축·섹터 베타) 비교 → `recipes.macro.stressMatrixChart`

재호출 트리거 발화: "고금리 장기화 시나리오 그래프", "2008 충격 전파 다이어그램", "달러 스트레스 인과 그래프".

## 대표 반환 형태

- `diagramSpec` — mermaid graph LR, 5~6 노드, 각 노드 라벨에 임계값 포함.
- `tableRef` — 후속 모니터링 3~5 행 표 (지표/현재값/임계값/리뷰주기).
- `valueRef` — `{scenarioName, scenarioType, nodeCount}` dict.
- `executionRef` — RunPython 실행 결과 id (답변 인용 키).

## 연계 절차

1. 여러 scenario 정량 비교는 `recipes.macro.tailRiskScenarioScan`.
2. 역사적 사건 비교는 `recipes.macro.historicalPositioning`.
3. 차트형 수치 비교는 `recipes.macro.stressMatrixChart`.
4. 회사 단위 충격 영향 추정은 `recipes.macro.companyMacroPathProjection`.

## 기본 검증

- 노드는 6 개 이하 (가독성 + 노드별 임계 부착 부담).
- scenario type 이 없으면 "조건부 충격" 중립 레이블 사용 + 한계 명시.
- 다이어그램은 설명 보조 — 본문 텍스트와 동일 정보면 다이어그램 생략.
- 결론 단은 *반드시 정량* (숫자 + 시점 + 방향) — 추상 평가 단어 단독 사용 금지.
