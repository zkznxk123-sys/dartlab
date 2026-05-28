---
id: engines.macro.observables
title: Macro — 핵심 Observable 5 축 (observables)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 매크로 답변의 indicator 5 축 (CPI/PMI/금리/환율/유동성) 단일 카탈로그 — 각 축의 source · 갱신 주기 · 단위 · interpretation 정의. cycle/regime/scenario 분류의 1 차 입력 데이터 SSOT.
whenToUse:
  - observable
  - 매크로 지표
  - indicator
  - CPI
  - PMI
  - 금리
  - 환율
  - 유동성
  - M2
  - 매크로 데이터 source
sourceRefs:
  - dartlab://skills/engines.macro.observables
capabilityRefs:
  - macro
knowledgeRefs:
  - engines.macro
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
linkedSkills:
  - engines.macro
  - engines.macro.cycles
  - engines.macro.regimes
---

## 엔진 역할

`macro` 엔진의 *핵심 indicator* 카탈로그 SSOT sub-spec. base SKILL `engines.macro` 의 12 axis 가 *사용하는* indicator 5 축의 source · 갱신 주기 · 단위 · interpretation 단일 정의. cycle/regime/scenario 분류의 1 차 입력.

## 공개 호출 방식

```python
import dartlab

# 1. 단일 indicator 시계열 (axis 자동 분기)
cpi = dartlab.macro("inflation", market="KR")
# → CPI YoY 시계열

pmi = dartlab.macro("cycle", market="KR")
# → PMI / OECD CLI 등 cycle indicator

rates = dartlab.macro("rates", market="KR")
# → 기준금리 / 국고채 curve

fx = dartlab.macro("exchange", market="KR")
# → USD/KRW 시계열

liquidity = dartlab.macro("liquidity", market="KR")
# → M2 / 신용 / 유동성 indicator
```

## 호출 동작

본 sub-spec 은 *카탈로그* — 실제 호출은 base SKILL `engines.macro` 의 12 axis. 본 sub-spec 은 각 axis 가 어떤 indicator 를 어디서 가져와 어떻게 해석하는지 정의.

## 5 축 카탈로그

### 1. 인플레이션 (inflation)

| indicator | market | source | 단위 | 갱신 주기 |
|---|---|---|---|---|
| CPI YoY | KR | 통계청 KOSIS | % | 월 |
| Core CPI | KR | 통계청 | % | 월 |
| PPI | KR | 한국은행 | % | 월 |
| CPI YoY | US | BLS | % | 월 |
| Core PCE | US | BEA | % | 월 |

interpretation: CPI > 3% 인플레이션, < 1% 디플레이션 우려. Core 가 본 신호 (식료품/에너지 제외).

### 2. 경기 (cycle)

| indicator | market | source | 단위 | 갱신 주기 |
|---|---|---|---|---|
| OECD CLI | KR/US/Global | OECD | index (100 분기점) | 월 |
| 한은 BCI | KR | 한국은행 | index | 월 |
| ISM Manufacturing PMI | US | ISM | index (50 분기점) | 월 |
| Markit PMI | KR | S&P Global | index | 월 |
| 산업생산 YoY | KR/US | 통계청/Fed | % | 월 |

interpretation: PMI > 50 확장, < 50 수축. CLI > 100 호황, < 100 침체. 1 차 미분 부호로 phase 전환 (engines.macro.cycles SSOT).

### 3. 금리 (rates)

| indicator | market | source | 단위 | 갱신 주기 |
|---|---|---|---|---|
| 기준금리 | KR | 한국은행 | % | 금통위 |
| FFR | US | Fed | % | FOMC |
| 국고채 1Y/3Y/5Y/10Y | KR | KOFIA | % | 일 |
| US Treasury 1M~30Y | US | Treasury | % | 일 |
| 회사채 (AAA/AA/A/BBB) | KR | KIS평가 | % | 일 |
| TED spread | US | Fed | bp | 일 |

interpretation: 10Y - 3M 또는 10Y - 2Y 가 yield curve 역전 신호 (recession 1~2 년 선행). 스프레드 확대 = 신용 위험 ↑.

### 4. 환율 (exchange)

| indicator | market | source | 단위 | 갱신 주기 |
|---|---|---|---|---|
| USD/KRW | KR | 한국은행 | 원 | 일 |
| USD/JPY | global | BOJ | 엔 | 일 |
| USD/CNY | global | PBOC | 위안 | 일 |
| DXY | US | ICE | index | 일 |
| EUR/USD | global | ECB | 달러 | 일 |
| 실효환율 (NEER/REER) | KR | BIS | index | 월 |

interpretation: KRW 절하 (USD/KRW ↑) = 수출주 alpha + 수입물가 ↑. DXY ↑ = 신흥국 위험 ↑.

### 5. 유동성 (liquidity)

| indicator | market | source | 단위 | 갱신 주기 |
|---|---|---|---|---|
| M2 YoY | KR/US | 한은/Fed | % | 월 |
| 신용잔액 (가계+기업) | KR | 한국은행 | 조원 | 월 |
| Fed 자산 (BS) | US | Fed | 조달러 | 주 |
| ECB 자산 | EU | ECB | 조유로 | 주 |
| 한은 본원통화 | KR | 한국은행 | 조원 | 월 |
| Repo / SOFR | US | Fed | bp | 일 |

interpretation: M2 YoY 가속 = 유동성 확대 → regime "expansion/recovery". 급감 = "contraction/crisis".

## 대표 반환 형태

```text
dartlab.macro(<axis>, market="KR")
→ dict
   axis : str                # "inflation" / "cycle" / "rates" / "exchange" / "liquidity"
   market : str              # "KR" / "US" / "global"
   indicators : list[dict]   # 본 sub-spec 카탈로그 표의 indicator
     - name : str
     - value : float
     - unit : str            # %/bp/index/...
     - dateRef : str         # YYYY-MM 또는 YYYY-MM-DD
     - source : str          # KOSIS / 한은 / OECD / ...
   interpretation : str      # 본 sub-spec 의 해석 룰 적용 결과
   dateRef : str             # 최신 indicator dateRef
```

## evidence 기준

매크로 답변은 indicator 단위 (% / bp / index) + 정확한 dateRef + source 명시. 단위 누락 또는 dateRef 누락 시 답변 거부 (base SKILL `engines.macro` forbidden 룰).

## 기본 검증

- 모든 indicator 의 단위 enum (%/bp/index/원/달러/조원/...) 안.
- dateRef YYYY-MM 또는 YYYY-MM-DD 형식.
- source 가 신뢰 source 카탈로그 (한은/Fed/OECD/KOSIS/BLS/...) 안.
- 동일 axis × market 재호출 시 indicators list 안정 (sort 순서 동일).

본 spec 은 공개 실행 문서다. 5 축 카탈로그 또는 indicator source 가 변경되면 본 파일을 같은 변경에서 갱신한다.

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL (12 axis)
- [engines.macro.cycles](/skills/engines.macro.cycles) — PMI/CLI 가 cycle phase 1 차 입력
- [engines.macro.regimes](/skills/engines.macro.regimes) — liquidity/rates 가 regime 분류 입력
- [engines.macro.scenarios](/skills/engines.macro.scenarios) — overrides schema 가 본 5 축 단위 그대로
