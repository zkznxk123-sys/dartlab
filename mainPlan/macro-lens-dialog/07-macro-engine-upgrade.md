# 07. 매크로 엔진 강화 트랙

상태: 설계 v0.2
범위: Macro Lens를 분석 코어로 만들기 위해 필요한 macro/analysis 엔진 개선 계획.

---

## 1. 결론

매크로 엔진은 개선한다. 다만 새 독립 엔진을 만들지 않는다.

목표 구조:

```text
macro.transmission
  └─ 시장·섹터 레벨 driver/edge/source 산출

analysis macro exposure quality
  └─ 회사 레벨 노출·회귀 품질 산출

macroLens view-model 또는 L2.5 조합기
  └─ 공개 산출물만 합쳐 다이얼로그 계약 생성
```

이 구조가 필요한 이유는 단순하다. `macro`가 회사 분석을 직접 알면 L2 경계가 깨지고, UI가 숨은 수학을 만들면 검증이 불가능하다. 따라서 강한 분석은 **역할 분리 + 표준 산출물 + 품질 라벨**로 만든다.

---

## 2. `macro.transmission`

### 목적

시장 국면과 지표를 사람이 읽는 문장으로 끝내지 않고, 기계가 추적할 수 있는 전파 edge로 만든다.

예:

```text
USDKRW ↑
  → KR export-heavy sectors revenue translation
  → revenue growth / operating margin
  → growth assumption / multiple risk
```

### 산출물

- `MacroDriver`: canonical id, source series, group, unit, direction semantics, default lag.
- `TransmissionEdge`: driver → market/sector/industry → financial line → valuation lever.
- `RegimeEvidence`: 국면 판단의 핵심 지표, 방향, 기준일, freshness.
- `SourceLineage`: source/date/value/path.

### 허용 입력

- `MACRO_SERIES` canonical id.
- `dashboards/macro.json`.
- `macro/{fred,ecos}/observations.parquet`.
- sector prior/industry prior.
- 기존 macro 축의 공개 결과.

### 금지 입력

- company 객체.
- `src/dartlab/analysis` 내부 함수.
- terminal UI state.
- L4 prompt/lens 자산.

---

## 3. Analysis Macro Exposure Quality

### 목적

회사별로 매크로 driver가 실제로 의미 있는지 판단할 최소 품질 정보를 만든다.

이미 있는 후보:

- `calcMacroSensitivity(company, basePeriod=None)`
- `calcMacroRegression(company, basePeriod=None)`

강화해야 할 출력:

- canonical driver id.
- `nObs`, `rSquared`, `window`, `frequency`, `lag`, `degreesOfFreedom`.
- `coverage`: `company`, `sectorOnly`, `missing`.
- `status`: `open`, `qualitativeOnly`, `blocked`.
- `blockedReason`: 표본 부족, 낮은 R², 결손, id 미배선, 기준일 불일치.
- line item binding: revenue, grossMargin, operatingMargin, interestExpense, cashFlow, inventory.

정책:

- `lowN` 또는 `lowR2`면 beta 숫자를 UI에 공개하지 않는다.
- sector prior만 있으면 "섹터 정성 경로"로 표시한다.
- 회사별 회귀가 좋아도 추천/목표가/수혜 확정으로 번역하지 않는다.

---

## 4. Canonical Driver Registry

분석 코어의 가장 큰 실패 모드는 id 혼선이다.

규칙:

- UI와 엔진이 보는 canonical macro id는 `MACRO_SERIES.id`다.
- FRED/ECOS 원본 id는 `sourceSeriesId`다.
- 레거시 id는 alias registry로만 허용한다.
- alias가 없으면 해당 edge는 `notWiredYet`로 내려간다.

초기 점검 대상:

| 위치 | 리스크 | 조치 |
|---|---|---|
| `sectorPriors.json` | `KRW_USD` 같은 레거시 id | `USDKRW` alias 또는 canonical 치환 |
| `sectorPriors.json` | `PMI`처럼 카탈로그에 없는 id | 신규 series 계약 전까지 미배선 |
| analysis macro sensitivity | static beta와 regression beta 혼재 | 품질 라벨과 id normalization 추가 |
| UI co-movement | 1차차분 상관이 영향처럼 읽힘 | falsifier로만 표시 |

---

## 5. Attempts Gate

엔진 강화는 바로 `src`에 넣지 않는다.

먼저 만든다:

```text
tests/_attempts/macroLensEngine/
  README.md
  driverRegistry.sample.json
  transmissionEdges.sample.json
  exposureQuality.sample.json
  failureCases.md
```

attempts 수용 기준:

- 최소 5개 driver: `USDKRW`, `BASE_RATE`, `CPI`, `EXPORT`, `DCOILWTICO`.
- 최소 5개 sector edge: 반도체, 자동차, 은행, 화학, 유틸리티.
- 각 edge에 `sign`, `lagMonths`, `confidence`, `evidenceLevel`, `sourceRefs`가 있다.
- 실패 케이스가 있다: id 미배선, 회사 증거 결손, 낮은 회귀 품질, stale macro.
- public terminal에서 필요한 `MacroLensSnapshot`으로 손실 없이 변환 가능하다.

graduation 조건:

- attempts 산출물에서 계약이 흔들리지 않는다.
- targeted tests가 있다.
- architecture guard에서 import cycle이 없다.
- `source/date/value` reference가 빠지지 않는다.

---

## 6. 후보 API

최종 이름은 구현 전 재검토한다. 방향만 고정한다.

```python
dartlab.macro("transmission", market="KR")
```

반환 후보:

```python
{
    "market": "KR",
    "asOf": "2026-06-17",
    "drivers": [...],
    "edges": [...],
    "regimeEvidence": [...],
    "sourceRefs": [...],
    "missing": [...]
}
```

analysis 공개 surface 후보:

```python
company.analysis("macro", "매크로민감도")
```

반환 후보:

```python
{
    "company": {"code": "...", "sectorKey": "..."},
    "driverExposure": [...],
    "quality": {...},
    "blocked": [...]
}
```

UI는 위 산출물을 직접 계산하지 않고 `MacroLensSnapshot`으로만 변환한다.

---

## 7. 강한 분석의 기준

강한 분석은 더 많은 숫자가 아니다.

강한 분석의 조건:

1. driver가 canonical id로 고정된다.
2. source/date/value가 trace된다.
3. 전파 edge가 financial line과 valuation lever까지 이어진다.
4. 회사 고유 노출과 섹터 prior가 분리된다.
5. 회귀/민감도에는 품질 라벨이 붙는다.
6. co-movement는 반증 도구로 표시된다.
7. 결손과 낮은 설명력은 분석을 닫는 이유가 된다.

이 기준을 통과하면 `경제지표분석`은 지표 표가 아니라 종목 분석의 매크로 축이 된다.
