---
id: recipes.macro.dollarFundingStress
title: 달러 펀딩 스트레스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 달러인덱스, 원달러 환율, VIX, HY spread, 금융상태지수 원자료를 gather로 확인해 글로벌 위험회피와 달러 펀딩 압력이 커지는지 판단하는 절차. 트리거 — '달러 스트레스', '달러 펀딩', 'DXY', 'USDKRW', '위험회피'.
whenToUse:
  - 달러 스트레스
  - 달러 펀딩
  - DXY
  - USDKRW
  - 위험회피
  - dollar funding stress
linkedSkills:
  - engines.gather
  - engines.macro
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.scenarioVisuals"
  - "engines.viz.tableBackedChart"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "stress·민감도·충격 전파는 engines.viz.scenarioVisuals를 사용하고 assumption grid 또는 수치 임계가 없으면 scenario table로 낮춘다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

gap:
  primary:
    - gather
    - macro
testUniverse:
  market: KR
  asOfPolicy: latest
falsifier:
  description: "DXY/USDKRW와 VIX/HY 중 한쪽 묶음만 있으면 달러 펀딩 스트레스로 단정하지 않는다."
expectedNovelty:
  - dollarStressTable
  - safeHavenCheck
  - krFxPressure
forbidden:
  - 원달러 상승을 항상 한국 고유 위험으로 해석하지 않는다.
  - DXY와 USDKRW를 같은 지표처럼 합산하지 않는다.
  - 위험회피와 금리차 요인을 구분하지 않고 결론 내리지 않는다.
failureModes:
  - DXY, VIX, HY spread는 US/글로벌 지표이고 USDKRW는 KR 양자 환율.
  - 환율 데이터 source별 기준시각 차이.
  - 달러 강세가 성장 호조와 위험회피 양쪽에서 발생 가능.
examples:
  - 달러 펀딩 스트레스 확인
  - DXY와 원달러가 같이 오르는 이유 점검
  - 위험회피성 달러 강세인지 봐줘
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
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab

indicators = ["DTWEXBGS", "DEXKOUS", "VIXCLS", "BAMLH0A0HYM2", "NFCI", "FEDFUNDS"]
rows = []
for indicator in indicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

usCrisis = dartlab.macro("crisis", market="US")
krAssets = dartlab.macro("assets", market="KR")
try:
    krSummary = dartlab.macro("summary", market="KR")
except Exception as exc:
    krSummary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "usDollarSafeHaven": ((usCrisis.get("dollarSafeHaven") or {}).get("status") if isinstance(usCrisis, dict) else None),
        "krOverall": krSummary.get("overall") if isinstance(krSummary, dict) else None,
        "krScore": krSummary.get("score") if isinstance(krSummary, dict) else None,
    },
    date=krSummary.get("latestAsOf") if isinstance(krSummary, dict) else None,
    sources=["dartlab://macro/crisis", "dartlab://macro/assets", "dartlab://macro/summary", "dartlab://gather/macro"],
)
```

## 호출 동작

### 1. 결론 도출

6 indicator 원자료 + dollarSafeHaven + krOverall 단정. 예: "DXY +2.4% 1M / USDKRW +1.8% / VIX 22 (정상 14-18 위) / HY spread 4.1% (3M+) / NFCI +0.3 (loose→tight 전환) → 달러 펀딩 스트레스 phase 진행 (4 of 5 위험 신호 동조)."

### 2. 핵심 근거 수집

- DTWEXBGS (US trade-weighted dollar), DEXKOUS (USDKRW), VIXCLS (VIX), BAMLH0A0HYM2 (HY spread), NFCI (Chicago Fed FCI), FEDFUNDS (정책금리) — gather macro 6 시리즈
- macro('crisis', US) dollarSafeHaven status (safeHaven / strengthOnGrowth / normal)
- macro('summary', KR) overall + score — KR 시장 동조 신호

### 3. 메커니즘 분석

```
6 source → 압력 합산
  DXY MoM > +1.5% + USDKRW MoM > +1%
     ↓
  VIX > 20 + HY spread > 4%
     ↓
  NFCI tightening (+ 추세) + dollarSafeHaven=safeHaven
     ↓
4 of 5 신호 동조 → 달러 펀딩 스트레스 phase
1-3 신호 → mixed (성장 호조 vs 위험회피 분리 필요)
0-1 신호 → normal
```

스트레스 phase + krOverall<0 = KR 시장 동조. 스트레스 phase + krOverall>0 = decoupling (KR 펀더멘털 우위).

### 4. 반례·한계

- DXY 와 USDKRW 동시 상승 = 달러 강세 우세, but 한쪽만 = 양자 요인.
- VIX/HY 안정 + USDKRW 만 상승 → 한국 고유 위험 (정치/지정학) — 글로벌 달러 stress 아님.
- 금리차 (Fed-BOK spread) 확대 시 USDKRW 자연 상승 — 위험회피 아닐 수 있음.
- NFCI 는 weekly, 즉시 신호 약함.

### 5. 후속 모니터링

- safeHaven phase 지속 → `recipes.macro.koreaMacroStressMap` 으로 KR 시장 전이 확인.
- HY spread 확대 일관 → `recipes.fundamental.credit.cycleStressMap` 으로 신용 사이클 확인.
- DXY 약세 + USDKRW 강세 (decoupling) → `recipes.macro.koreaExportCycleNowcast` 로 KR 수출 사이클 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | DTWEXBGS / DEXKOUS / VIXCLS / BAMLH0A0HYM2 / NFCI / FEDFUNDS |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 달러 압력이 유동성 문제라면 `recipes.macro.globalLiquidityPulse` 로 원인을 확인한다.
2. 한국 시장 영향은 `recipes.macro.koreaMacroStressMap` 또는 `recipes.macro.koreaExportCycleNowcast` 로 연결한다.
3. 신용위험이 같이 커지면 `recipes.fundamental.credit.cycleStressMap` 으로 확장한다.

## 기본 검증

- 글로벌 지표와 KR 양자 환율을 분리해 표시한다.
- VIX/HY가 안정적인데 USDKRW만 오르면 한국/금리차 요인 가능성을 남긴다.
