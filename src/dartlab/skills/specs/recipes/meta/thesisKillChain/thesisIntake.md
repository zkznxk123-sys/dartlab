---
id: recipes.meta.thesisKillChain.thesisIntake
title: Thesis Kill-Chain Thesis Intake
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: incubator.thesisKillChain
purpose: 사용자 thesis를 받아 growth, margin, cash, balance sheet, valuation, event, macro, governance theme으로 파싱하는 pre-mortem 시작 절차다.
whenToUse:
  - thesis intake
  - 투자 thesis 파싱
  - 프리모템 시작
inputs:
  - 사용자 thesis
  - optional assumptions
outputs:
  - thesisIntake table
capabilityRefs:
  - Company.show
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - operation.skillDevelopmentLoop
sourceRefs:
  - dartlab://skills/recipes.meta.thesisKillChain.thesisIntake
requiredEvidence:
  - skillRef
  - tableRef
  - sourceRef
  - executionRef
expectedOutputs:
  - thesis text
  - parsed themes
visualRefs:
  - engines.viz.kpiRibbon
visualGuidance:
  - "themeCount는 kpiRibbon chart의 보조 숫자로만 표시하고 thesis 원문 table을 보존한다."
linkedSkills:
  - recipes.meta.thesisKillChain.assumptionLedger
  - recipes.meta.thesisKillChain.deepDive
  - engines.company
gap:
  primary:
    - synth
    - gather
falsifier:
  description: "thesis가 비어 있는데 scenario를 만들면 실패로 본다."
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
    status: limited
forbidden:
  - thesis 없이 투자 결론을 만들지 않는다.
failureModes:
  - thesis 원문을 잃고 일반 분석으로 전환
examples:
  - 이 thesis를 깨는 관점으로 파싱
audiences:
  llm: thesis 원문을 먼저 보존하고, theme은 보조 분류로만 사용한다.
  agent: thesisIntake가 missing이면 사용자에게 thesis 보강을 요구한다.
  human: 내가 믿는 문장을 testable assumption으로 바꾸는 첫 단계다.
humanIntro: "thesisIntake는 프리모템의 입력 잠금이다. 원문을 잃으면 이후 시나리오는 일반 분석으로 흐른다."
lastUpdated: "2026-05-17"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 아래 Python 블록은 확보한 L1/L1.5 근거를 `buildThesisKillChainMemo`로 묶는 **RunPython fallback** 절차다.

```python
from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

target = "005930"
thesis = "매출 성장과 현금 전환이 유지되어 valuation discount가 해소된다"

memo = buildThesisKillChainMemo(target=target, thesis=thesis)

emit_result(
    table=memo["tables"]["thesisIntake"],
    values=memo["headline"],
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

thesis 원문 + 파싱 themes 단정. 예: "thesis='매출 성장과 현금 전환이 유지되어 valuation discount 가 해소된다' → themeCount=4 / themes=[growth, cash, valuation, balanceSheet] / status=ok. 사용자 thesis 원문 보존 + 4 theme 파싱 (8 종 카테고리 중 4 종 매칭) — kill chain 진입 준비 완료."

### 2. 핵심 근거 수집

- 사용자 thesis 원문 (필수 입력)
- 키워드 매칭 8 theme: growth / margin / cash / balanceSheet / valuation / event / macro / governance
- buildThesisKillChainMemo() → thesisIntake table
- status: ok (≥ 1 theme) / missing (thesis 비어 있음)

### 3. 메커니즘 분석

```
thesis 원문 → 키워드 파싱
   "성장" / "매출" / "확장"           → growth theme
   "마진" / "수익성" / "OPM"           → margin theme
   "현금" / "FCF" / "전환"             → cash theme
   "부채" / "유동성" / "balance sheet" → balanceSheet theme
   "valuation" / "할인" / "multiple"   → valuation theme
   "촉매" / "이벤트" / "공시"           → event theme
   "금리" / "환율" / "거시"             → macro theme
   "거버넌스" / "이사회" / "지배구조"   → governance theme
   ↓
status 판정:
   themeCount ≥ 1  → ok (kill chain 진입 가능)
   themeCount = 0  → missing (thesis 보강 요구)
   ↓
원문 보존 강제:
   thesis 원문이 table 에 남아 있어야 함 (forensic 추적 가능)
   parsed theme 은 *보조 분류* — 원문 의미 대체 X
```

intake = pre-mortem 의 입력 잠금. 원문 잃으면 이후 scenario 가 일반 분석으로 흐름 (forbidden). theme 파싱은 보조 분류 — 인과/우선순위 단정 X.

### 4. 반례·한계

- thesis 비어 있는데 scenario 생성 → forbidden 위반.
- thesis 원문 잃고 일반 분석 전환 → failureMode 발동.
- 키워드 매칭 false positive (예: "현금 영수증" → cash theme 오인) 가능.
- theme 카테고리 8 종 외 영역 (예: ESG / 정치) 미커버 — 8 종 강제.

### 5. 후속 모니터링

- status=ok + themeCount ≥ 2 → `recipes.meta.thesisKillChain.assumptionLedger` 로 testable assumption 전환.
- status=missing → 사용자에게 thesis 보강 요구 (다른 recipe 진입 차단).
- themeCount ≥ 4 → `recipes.meta.thesisKillChain.deepDive` 로 전체 kill chain 실행.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `thesis` | 사용자 thesis 원문 |
| `themeCount` | 파싱된 theme 수 |
| `themes` | growth/margin/cash 등 |
| `status` | ok/missing |

## 연계 절차

1. recipes.meta.thesisKillChain.assumptionLedger - theme을 testable assumption으로 전환.
2. recipes.meta.thesisKillChain.deepDive - 전체 pre-mortem 실행.

## 기본 검증

- thesis 원문이 table에 남아 있어야 한다.
- missing이면 scenarioStoryboard를 확정하지 않는다.
