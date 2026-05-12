---
id: recipes.macro.dollarFundingStress
title: 달러 펀딩 스트레스 원자료 점검
category: recipes
kind: recipe
scope: builtin
status: drafted
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
  - engines.gather.macro
  - engines.macro.crisis
  - engines.macro.assets
  - engines.macro.summary
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
  - valueRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
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
lastUpdated: '2026-05-12'
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
)
```

## 호출 동작

1. 달러지수, 원달러, VIX, HY spread, NFCI 원자료를 모은다.
2. `macro("crisis", market="US")` 의 dollarSafeHaven 신호를 확인한다.
3. `macro("assets", market="KR")` 와 `summary` 로 한국 시장 반응을 검산한다.
4. 달러 강세가 위험회피인지 금리/성장 차이인지 나눠 설명한다.

## 대표 반환 형태

- `tableRef`: dollar/funding indicator별 원자료.
- `valueRef`: usDollarSafeHaven, krOverall, krScore.
- 답변 본문: 글로벌 달러 압력, 한국 환율 압력, 위험회피 여부.

## 연계 절차

1. 달러 압력이 유동성 문제라면 `recipes.macro.globalLiquidityPulse` 로 원인을 확인한다.
2. 한국 시장 영향은 `recipes.macro.koreaMacroStressMap` 또는 `recipes.macro.koreaExportCycleNowcast` 로 연결한다.
3. 신용위험이 같이 커지면 `recipes.credit.cycleStressMap` 으로 확장한다.

## 기본 검증

- 글로벌 지표와 KR 양자 환율을 분리해 표시한다.
- VIX/HY가 안정적인데 USDKRW만 오르면 한국/금리차 요인 가능성을 남긴다.
