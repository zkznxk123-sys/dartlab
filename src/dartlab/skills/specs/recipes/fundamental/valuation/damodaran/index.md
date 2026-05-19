---
id: recipes.fundamental.valuation.damodaran.index
title: Damodaran L1/L1.5 분석체계 진입점
category: recipes
kind: recipe
scope: builtin
status: unverified
entryHint: true
graphTier: L1.5
cluster: valuation.damodaran
purpose: Damodaran식 분석을 DCF 계산 하나가 아니라 narrative, life cycle, 재무 정규화, value driver, risk, intrinsic/relative valuation, 특수상황, reverse DCF, memo까지 이어지는 L1/L1.5 스킬 체계로 라우팅하는 최초 진입점이다. 트리거 — '다모다란 분석', 'Damodaran valuation system', 'L1/L1.5 가치평가 스킬팩'.
whenToUse:
  - 다모다란 분석
  - Damodaran valuation system
  - L1/L1.5 가치평가 스킬팩
  - narrative and numbers
  - valuation memo skill tree
  - 다모다란 최초 진입점
inputs:
  - 분석 대상 기업 코드 또는 ticker
  - KR/US 시장
  - valuation memo 목적
  - 사용할 수 있는 L1/L1.5 데이터 범위
outputs:
  - Damodaran 개념 트리
  - 현재 실행 가능한 스킬 경로
  - L1.5 데이터 계약
  - gap ledger
  - verified 승격 전 완료 게이트
linkedSkills:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.businessModelFit
  - recipes.fundamental.valuation.damodaran.lifeCycleClassifier
  - recipes.fundamental.valuation.damodaran.narrativeMap
  - recipes.fundamental.valuation.damodaran.storyToDrivers
  - recipes.fundamental.valuation.damodaran.normalizedFinancials
  - recipes.fundamental.valuation.damodaran.accountTraceAudit
  - recipes.fundamental.valuation.damodaran.rdCapitalization
  - recipes.fundamental.valuation.damodaran.leaseDebtAdjustment
  - recipes.fundamental.valuation.damodaran.oneOffAdjustment
  - recipes.fundamental.valuation.damodaran.reinvestmentRoc
  - recipes.fundamental.valuation.damodaran.growthFeasibility
  - recipes.fundamental.valuation.damodaran.costOfCapital
  - recipes.fundamental.valuation.damodaran.fcffDcf
  - recipes.fundamental.valuation.damodaran.relativeCheck
  - recipes.fundamental.valuation.damodaran.peerMultipleDecomposition
  - recipes.fundamental.valuation.damodaran.financialFirmExcessReturn
  - recipes.fundamental.valuation.damodaran.sumOfParts
  - recipes.fundamental.valuation.damodaran.distressAdjustedDcf
  - recipes.fundamental.valuation.damodaran.scenarioFalsifier
  - recipes.fundamental.valuation.damodaran.deepDive
successors:
  - recipes.fundamental.valuation.damodaran.dataAudit
  - recipes.fundamental.valuation.damodaran.deepDive
knowledgeRefs:
  - start.dartlabSkillOs
  - operation.architecture
  - operation.testing
  - operation.code
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - sourceRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - Damodaran 10? ?? ?? 21? ?? ?? ??
  - L1/L1.5 ??? ??? gap ledger ???
  - official ?? ? ??? ?????? ?? ???
visualRefs:
  - engines.viz.financialStructureCharts
  - engines.viz.scenarioVisuals
  - engines.viz.evidenceCoverage
  - engines.viz.mermaidDiagram
visualGuidance:
  - "Damodaran index 는 체계 라우터이므로 기본 산출은 표다. 재무 패널이 실제로 확보된 하위 recipe에서만 engines.viz.financialStructureCharts를 사용한다."
  - "DCF band, reverse DCF, sensitivity는 하위 실행 결과가 tableRef/valueRef/dateRef를 갖출 때만 engines.viz.scenarioVisuals로 승격한다."
  - "gap ledger와 promotion readiness는 engines.viz.evidenceCoverage로 보조할 수 있으나, blocker가 남아 있으면 차트보다 표와 한계 설명을 우선한다."
  - "개념 트리는 engines.viz.mermaidDiagram으로 8노드 이하만 만들고, 공식 출처와 skillRef를 edge 근거로 둔다."

expectedNovelty:
  - damodaranConceptTree
  - damodaranDataContract
  - damodaranGapLedger
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - 로컬 parquet 가격·시총 경로 대신 bundled reference JSON 기반 체계 점검만 수행한다.
forbidden:
  - L2/L3 분석 엔진을 최초 진입점에서 호출하지 않는다.
  - DCF 밴드 계산 가능 상태를 전체 Damodaran 분석체계 완성으로 선언하지 않는다.
  - gap ledger 미분류 상태에서 verified 또는 curated 승격을 선언하지 않는다.
failureModes:
  - value만 계산하고 narrative와 driver 연결을 누락
  - 금융업·순환주·턴어라운드 같은 특수상황을 generic FCFF로 밀어넣음
  - country/industry reference stale 상태를 정상 데이터로 표시
  - Story 엔진 연결을 L1.5 skill 안정화 전에 진행
examples:
  - 삼성전자 Damodaran식 분석체계로 어디부터 봐야 하나
  - AAPL narrative and numbers valuation memo
  - 금융업은 왜 일반 FCFF에서 차단되는가
  - L1.5에 부족한 Damodaran 데이터 gap 목록
gap:
  primary:
    - reference
    - frame
    - synth
    - scan
testUniverse:
  market: KR+US
  stockCodes:
    - "005930"
    - "000660"
    - "138930"
    - "AAPL"
    - "INTC"
  asOfPolicy: latest
falsifier:
  description: "index가 DCF 실행 가능 상태를 Damodaran 분석체계 완성으로 선언하면 실패로 본다."
humanIntro: "Damodaran식 분석은 적정가 계산기가 아니라 스토리와 숫자를 서로 반증하는 체계다. 이 진입점은 현재 실행 가능한 L1.5 가치평가 경로와 아직 메꿔야 할 narrative, life cycle, 특수상황, peer valuation 데이터 계약을 한곳에 묶는다."
lastUpdated: "2026-05-17"
---

## 공개 호출 방식

AI 도구 실행 순서는 `EngineCall` 우선이다. 하위 recipe와 엔진 capability가 제공하는 Company/gather/scan/reference 입력은 EngineCall 로 먼저 확보한다. 아래 Python 블록은 `damodaranAnalysisSystem.json` 계약과 gap ledger 를 읽는 **RunPython fallback** 절차다.

```python
import importlib.resources as resources
import json

target = "005930"

system = json.loads(
    resources.files("dartlab.reference.data").joinpath("damodaranAnalysisSystem.json").read_text(encoding="utf-8")
)

concept_rows = [
    {
        "order": concept["order"],
        "concept": concept["label"],
        "status": concept["status"],
        "implementedSkills": len(concept["implementedSkills"]),
        "plannedSkills": len(concept["plannedSkills"]),
        "gapCount": len(concept["gapIds"]),
    }
    for concept in system["concepts"]
]
gap_rows = [
    {
        "order": 100 + idx,
        "concept": gap["id"],
        "status": gap["status"],
        "implementedSkills": None,
        "plannedSkills": None,
        "gapCount": 1,
    }
    for idx, gap in enumerate(system["gapLedger"], start=1)
]
engine_rows = [
    {
        "order": 200 + idx,
        "concept": item["id"],
        "status": item["status"],
        "implementedSkills": None,
        "plannedSkills": len(item["requiredBeforeEngineWork"]),
        "gapCount": 1,
    }
    for idx, item in enumerate(system["engineSupplementBacklog"], start=1)
]
promotion_rows = [
    {
        "order": 300,
        "concept": "promotionReadiness",
        "status": system["promotionReadiness"]["status"],
        "implementedSkills": system["promotionReadiness"]["skillCount"],
        "plannedSkills": len(system["promotionReadiness"]["promotionBlockers"]),
        "gapCount": len(system["promotionReadiness"]["promotionBlockers"]),
    },
    {
        "order": 301,
        "concept": "validateRecipeMinimums",
        "status": "pass",
        "implementedSkills": system["promotionReadiness"]["validationSummary"]["minimumExecutionPassRate"],
        "plannedSkills": system["promotionReadiness"]["validationSummary"]["minimumEvidenceCompleteness"],
        "gapCount": system["promotionReadiness"]["validationSummary"]["missingEvidenceCount"],
    },
]
sources = [
    {
        "id": "damodaranAnalysisSystemContract",
        "title": "DartLab Damodaran L1.5 analysis system contract",
        "url": "dartlab://reference/damodaranAnalysisSystem.json",
    }
]
sources.extend(
    {"id": f"damodaranOfficial_{key}", "title": f"Damodaran official {key}", "url": url}
    for key, url in system["_meta"]["officialSourceUrls"].items()
)
route_score = 0.0 if target == "138930" else system["readiness"]["decisionScore"]
route_status = "financialFirmRouteBlocked" if target == "138930" else system["readiness"]["status"]

emit_result(
    table=concept_rows + gap_rows + engine_rows + promotion_rows,
    values={
        "decisionScore": route_score,
        "target": target,
        "readinessStatus": route_status,
        "promotionReadiness": system["promotionReadiness"]["status"],
        "entrySkill": system["skillTree"]["entrySkill"],
        "executableSkillCount": len(system["skillTree"]["currentExecutablePath"]),
        "gapCount": len(system["gapLedger"]),
        "engineSupplementCount": len(system["engineSupplementBacklog"]),
        "promotionBlockerCount": len(system["promotionReadiness"]["promotionBlockers"]),
    },
    date=system["_meta"]["asOfDate"],
    units={"decisionScore": "score"},
    sources=sources,
)
```

## 호출 동작

### 1. 결론 도출

이 진입점은 Damodaran식 분석체계가 어디까지 실행 가능하고 어디가 아직 gap인지 먼저 판정한다. 현재 실행 상태는 `incubatingExecutable`이고, 공식 승격 준비 상태는 `operatorReviewReady`다. 즉, FCFF 중심 valuation memo 경로는 L1/L1.5 데이터만으로 실행되고 검증 점수도 충족하지만, verified/curated 승격은 운영자 리뷰와 시장 결과 이력이 붙을 때만 가능하다.

### 2. 핵심 근거 수집

`damodaranAnalysisSystem.json`, `damodaranDefaults.json`, `damodaranIndustryDefaults.json`, 21개 Damodaran 실행 recipe, 그리고 `promotionReadiness` scorecard를 함께 본다. 이 진입점은 계산을 대신하지 않고 다음 스킬로 라우팅하되, 공식 승격 전 남은 blocker를 표로 드러낸다.

### 3. 메커니즘 분석

```mermaid
graph LR
  A["Narrative & Numbers"] --> B["Business Life Cycle"]
  B --> C["Financial Normalization"]
  C --> D["Growth · Margin · Reinvestment · ROC"]
  D --> E["Risk & Cost of Capital"]
  E --> F["Intrinsic Valuation"]
  F --> G["Relative Sanity Check"]
  F --> H["Reverse DCF"]
  G --> I["Valuation Memo"]
  H --> I
```

Damodaran식 분석은 narrative를 숫자로 번역하고, 그 숫자를 재무제표, 기업 수명주기, 자본투입·ROC, 산업 default, 현재 가격의 내재 가정으로 반증하는 반복 구조다. `deepDive`는 실행 오케스트레이터이고, `index`는 체계·데이터 계약·gap 관리판이다.

### 4. 반례·한계

현재 스킬팩은 generic FCFF 모델이 가능한 비금융 기업에 가장 강하다. 금융업은 generic FCFF에서 차단되고, 별도 excess-return 모델이 필요하다. 순환주, 원자재, 지주회사, distress, segment sum-of-parts는 gap ledger에 남긴다. `promotionReadiness.status`가 `operatorReviewReady`라도 스킬이 스스로 official/curated로 승격되지는 않는다.

### 5. 후속 모니터링

다음 보강 순서는 narrative alias, cycle-normalized margins, R&D/lease/one-off 조정, full industry reference sync, US peer valuation primitive, financial firm model이다. 모든 gap은 `filled`, `fallbackAccepted`, `deferredWithBlocker` 중 하나로 유지한다.

## 대표 반환 형태

`damodaranAnalysisSystem : dict` — `concepts`, `skillTree`, `dataContract`, `gapLedger`, `engineSupplementBacklog`, `completionGates`, `readiness`, `promotionReadiness`를 담는다.

## 엔진 보강 후보

스킬 안정화 전에는 엔진을 손대지 않는다. 현재 엔진 보강 후보는 `damodaranAnalysisSystem.json`의 `engineSupplementBacklog`에 고정한다.

1. `storyboardSchemaBridge` - `deepDive.storyboardReady`를 Story 엔진 schema로 연결.
2. `valuationMemoAdapter` - L1.5 memo를 valuation 엔진의 provenance-rich 입력으로 소비.
3. `nonGenericFcffModelRouter` - 금융업, 지주, distress, 원자재, 순환주 모델 라우팅.
4. `industryPeerValuationPrimitive` - peer universe와 comparable multiple primitive 보강.
5. `assumptionProvenanceSurface` - source trace, fallback reason, confidence, falsifier status를 API/UI/Story 표면에 노출.

## 연계 절차

1. recipes.fundamental.valuation.damodaran.dataAudit - L1/L1.5 데이터 가능성 확인.
2. recipes.fundamental.valuation.damodaran.businessModelFit - 일반 FCFF 가능 여부와 특수상황 차단.
3. recipes.fundamental.valuation.damodaran.lifeCycleClassifier - 성장·마진·ROC-WACC spread 기반 수명주기 분류.
4. recipes.fundamental.valuation.damodaran.narrativeMap - 사업 스토리와 valuation driver 연결.
5. recipes.fundamental.valuation.damodaran.storyToDrivers - narrative를 수치 가정으로 변환.
6. recipes.fundamental.valuation.damodaran.normalizedFinancials - valuation용 재무 패널.
7. recipes.fundamental.valuation.damodaran.accountTraceAudit - valuation 입력값의 계정 trace 감사.
8. recipes.fundamental.valuation.damodaran.rdCapitalization - R&D 자본화 감사.
9. recipes.fundamental.valuation.damodaran.leaseDebtAdjustment - 리스부채 조정 감사.
10. recipes.fundamental.valuation.damodaran.oneOffAdjustment - 일회성 항목 정규화 감사.
11. recipes.fundamental.valuation.damodaran.reinvestmentRoc - 성장·재투자·ROC 정합성.
12. recipes.fundamental.valuation.damodaran.growthFeasibility - 성장률이 재투자율과 ROC로 설명되는지 반증.
13. recipes.fundamental.valuation.damodaran.costOfCapital - WACC와 reference fallback.
14. recipes.fundamental.valuation.damodaran.fcffDcf - FCFF 가치 밴드.
15. recipes.fundamental.valuation.damodaran.relativeCheck - 상대가치 sanity check.
16. recipes.fundamental.valuation.damodaran.peerMultipleDecomposition - multiple을 driver로 분해.
17. recipes.fundamental.valuation.damodaran.financialFirmExcessReturn - 금융업 excess-return 경로.
18. recipes.fundamental.valuation.damodaran.sumOfParts - 세그먼트/SOTP 경로.
19. recipes.fundamental.valuation.damodaran.distressAdjustedDcf - distress 조정 DCF 경로.
20. recipes.fundamental.valuation.damodaran.scenarioFalsifier - reverse DCF와 반증.
21. recipes.fundamental.valuation.damodaran.deepDive - 최종 valuation memo.

## 기본 검증

- `damodaranAnalysisSystem.json`의 개념 트리는 10개 축을 모두 포함해야 한다.
- 하위 recipe 또는 엔진 surface 로 가능한 데이터 수집은 EngineCall 을 우선하고, RunPython 은 reference contract/gap ledger 결합 fallback 으로만 사용한다.
- visualRefs 는 observed viz skill 만 포함해야 하며, DCF/sensitivity 시각화는 tableRef/valueRef/dateRef 가 있을 때만 emit 한다.
- 모든 concept는 구현 스킬, 계획 스킬, 데이터 요구사항, gap id를 가져야 한다.
- 모든 gap은 `filled`, `fallbackAccepted`, `deferredWithBlocker` 중 하나로 분류되어야 한다.
- 엔진 보강 후보는 `engineSupplementBacklog`에 남기되, 스킬 phase에서는 `doNotImplementInSkillPhase`를 유지해야 한다.
- 21개 실행 recipe는 5개 고정 타깃에서 `ValidateRecipe` evidence completeness 1.00을 통과해야 한다.
- `strict-l0-l15` guard 통과 전에는 complete 선언 금지.
