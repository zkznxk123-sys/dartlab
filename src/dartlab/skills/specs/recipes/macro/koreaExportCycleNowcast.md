---
id: recipes.macro.koreaExportCycleNowcast
title: 한국 수출 사이클 원자료 나우캐스트
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: ECOS/FRED/KRX 원자료와 macro.trade 해석을 묶어 한국 수출 경기의 현재 방향을 빠르게 점검하는 절차. macro 축에 없는 반도체·원화·KOSPI 반응 proxy를 gather로 보강한다. 트리거 — '한국 수출', '수출 사이클', '반도체 경기', '교역조건'.
whenToUse:
  - 한국 수출
  - 수출 사이클
  - 반도체 경기
  - 교역조건
  - export nowcast
linkedSkills:
  - engines.gather
  - engines.macro
  - engines.scan
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
  description: "macro.trade 또는 KR 원자료가 모두 결손이면 한국 수출 nowcast로 쓰지 않는다."
expectedNovelty:
  - exportProxyTable
  - tradeMacroBridge
  - koreaCycleNowcast
forbidden:
  - KOSPI 지수만으로 수출 경기를 단정하지 않는다.
  - 반도체 proxy를 전체 한국 경제로 과잉 일반화하지 않는다.
  - 교역조건과 수출금액을 같은 의미로 쓰지 않는다.
failureModes:
  - ECOS 지표 코드별 제공 기간/빈도 차이.
  - 반도체 proxy와 전체 수출의 시차.
  - 환율 효과가 수출 물량과 원화 매출에 반대로 작용할 수 있음.
examples:
  - 한국 수출 사이클 지금 개선 중인가
  - 반도체 경기와 교역조건 같이 확인
  - 원달러와 KOSPI로 수출주 환경 봐줘
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

market = "KR"
macroIndicators = ["EXPORT", "USDKRW", "CPI"]
rows = []
for indicator in macroIndicators:
    try:
        data = dartlab.gather("macro", indicator)
        rows.append({"indicator": indicator, "data": data, "ok": True})
    except Exception as exc:
        rows.append({"indicator": indicator, "error": str(exc), "ok": False})

try:
    kospi = dartlab.gather("krxIndex", "close", market="KOSPI")
    rows.append({"indicator": "KOSPI.close", "data": kospi, "ok": True})
except Exception as exc:
    rows.append({"indicator": "KOSPI.close", "error": str(exc), "ok": False})

trade = dartlab.macro("trade", market=market)
corporate = dartlab.macro("corporate", market=market)
try:
    summary = dartlab.macro("summary", market=market)
except Exception as exc:
    summary = {"error": str(exc)}

emit_result(
    table=rows,
    values={
        "market": market,
        "tradeDirection": ((trade.get("termsOfTrade") or {}).get("direction") if isinstance(trade, dict) else None),
        "summaryOverall": summary.get("overall") if isinstance(summary, dict) else None,
        "summaryScore": summary.get("score") if isinstance(summary, dict) else None,
    },
    date=summary.get("latestAsOf") if isinstance(summary, dict) else None,
    sources=["dartlab://macro/summary", "dartlab://macro/trade", "dartlab://macro/corporate", "dartlab://gather/macro", "dartlab://gather/krxIndex"],
)
```

## 호출 동작

### 1. 결론 도출

EXPORT + USDKRW + KOSPI + tradeDirection 결합 단정. 예: "KR EXPORT YoY +8.2% (3M 연속 +) / USDKRW 1340 (-1.5% MoM) / KOSPI +4.2% MoM / tradeDirection=improving → 수출 사이클 개선 phase (수출 + 교역조건 + 주식 동조)."

### 2. 핵심 근거 수집

- KR EXPORT YoY, USDKRW, CPI (ECOS) — gather macro 3 시리즈
- KOSPI close (gather krxIndex) — 시장 반응 proxy
- macro('trade').termsOfTrade.direction — 교역조건 방향 (improving / deteriorating / flat)
- macro('corporate') — 기업이익 집계
- macro('summary') overall + score — KR 거시 종합

### 3. 메커니즘 분석

```
4 source → 수출 사이클 phase
  EXPORT YoY > +5% (3M 연속) + tradeDirection=improving
     → 회복 phase
  USDKRW 약세 + KOSPI 상승 (수출주 우세)
     → 환율-주식 동조 confirm
  EXPORT YoY < 0 (2M 연속) + tradeDirection=deteriorating
     → 수축 phase
   ↓
4 신호 동조 → 결론 강함
2-3 동조 → 방향성 약함 (보완 필요)
1 이하 동조 → 결론 보류 (혼재)
```

USDKRW 강세 + EXPORT 증가 = 가격 효과 (물량 둔화 가능). USDKRW 약세 + EXPORT 증가 = 물량 + 가격 모두 회복.

### 4. 반례·한계

- 반도체 export 비중 20%+ → 반도체 사이클 ≠ 전체 수출 사이클 (시차).
- USDKRW 효과는 수출물량 (단기) vs 원화매출 (즉시) 반대.
- ECOS EXPORT 는 월간 + 발표 lag 20 일 — 실시간 nowcast 약함.
- COVID/원자재 충격 시 base effect 왜곡.

### 5. 후속 모니터링

- 회복 phase + 반도체 강세 → `recipes.industry.sectorMomentumLeadership` 로 sector leader 확인.
- 환율 약세 + 수출 약세 (이중악재) → `recipes.macro.dollarFundingStress` 로 외인 자금 압박 점검.
- 교역조건 악화 지속 → `recipes.macro.koreaMacroStressMap` 으로 KR 거시 종합 stress 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `indicator` | EXPORT / USDKRW / CPI / KOSPI.close |
| `data` | 시계열 원자료 |
| `ok` | gather 성공 여부 |

## 연계 절차

1. 환율 압력이 핵심이면 `recipes.macro.dollarFundingStress` 로 연결한다.
2. 한국 전체 스트레스 지도는 `recipes.macro.koreaMacroStressMap` 으로 확장한다.
3. 종목/업종 후보 발굴은 `engines.scan` 또는 `engines.scan` 으로 넘긴다.

## 기본 검증

- 원자료 코드 실패는 실패 행으로 남긴다.
- `macro.trade` 결과 없이 KOSPI만으로 수출 사이클을 판단하지 않는다.
