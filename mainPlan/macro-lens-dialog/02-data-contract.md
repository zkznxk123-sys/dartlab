# 02. 데이터 계약

상태: 구현 v0.4
범위: Macro Lens 다이얼로그가 읽는 데이터, 매크로 전파 엔진 산출물, 향후 확장 계약.

---

## 1. 재사용 데이터

첫 구현은 새 수집 없이 다음 자산을 재사용한다.

| 데이터 | 위치 | 용도 |
|---|---|---|
| macro regime | `dashboards/macro.json` | KR/US phase, quadrant, sectorTailwind |
| macro observations | `macro/{fred,ecos}/observations.parquet` | 지표 최신값·스파크라인·차트 오버레이 |
| macro catalog | `ui/packages/contracts/src/macro.ts::MACRO_SERIES` | 지표명·단위·소스·그룹 |
| macro transmission | `src/dartlab/macro/transmission/transmission.py` | driver → sector → financial line → valuation lever edge |
| company tailwind | `ui/packages/surfaces/src/terminal/lib/engine.ts::tailwindOf` | 선택 종목 업종의 blended tailwind |
| sector tailwinds | `eng.sectorTailwinds()` | 좌측 순풍/역풍 섹터 목록 |
| co-movement | `ui/packages/surfaces/src/terminal/lib/coMovement.ts` | 종목 월수익률과 거시 1차차분 상관 |
| price/finance snapshot | terminal `Company` shape | 회사 checkpoint 표시 |
| sector priors | `src/dartlab/providers/mappers/.../sectorPriors.json` | 전파 edge 초기 prior 후보 |
| macro sensitivity | `src/dartlab/analysis/financial/_signalsMacroSensitivity.py` | 회사 노출·회귀 품질 후보 |

주의: `MACRO_SERIES.id`를 canonical macro id로 둔다. `KRW_USD`, `PMI`처럼 기존 prior나 분석 코드에 남은 레거시/외부 id는 registry에서 명시적으로 매핑하거나 사용하지 않는다.

---

## 2. `MacroLensSnapshot` 계약

UI view-model의 권장 형태다. 첫 구현은 런타임 산출물을 조합해 클라이언트에서 만든다.

```typescript
export interface MacroLensSnapshot {
  asOf: {
    macro: string | null;
    price: string | null;
    finance: string | null;
  };
  company: {
    code: string;
    name: string;
    industry: string;
    industryName: string | null;
  };
  marketPhase: {
    kr: MacroPhaseView | null;
    us: MacroPhaseView | null;
  };
  drivers: MacroDriverView[];
  topPressures: MacroDriverView[];
  transmissionEdges: MacroTransmissionEdgeView[];
  companyCheckpoints: MacroCheckpointView[];
  sectorBinding: {
    tailwind: Tailwind | null;
    top: MacroSectorBinding[];
    bottom: MacroSectorBinding[];
  };
  exposureQuality: MacroExposureQuality;
  evidenceGates: MacroEvidenceGate[];
  falsifiers: MacroFalsifierView[];
  scenarios: MacroScenarioView[];
  sourceRefs: string[];
  missing: MacroMissing[];
}
```

필드 의미:

- `marketPhase`: `macro.json`의 KR/US phase와 quadrant.
- `drivers`: canonical driver id, series binding, 방향성 의미, 단위, 기본 lag, freshness, co-movement 후보.
- `topPressures`: 첫 화면 pulse/matrix에 우선 노출할 driver. UI 라벨은 투자 압박이 아니라 검토 우선순위로 번역한다.
- `transmissionEdges`: driver가 sector/financial line/valuation lever로 전파되는 후보 경로.
- `companyCheckpoints`: 회사 재무 checkpoint. 예: 부채비율, 영업이익률, CFO/NI 등 이미 terminal `Company`가 가진 값만 사용한다.
- `sectorBinding`: `co.tailwind`와 `eng.sectorTailwinds()` 기반 섹터 순풍/역풍.
- `exposureQuality`: 회사별 민감도·회귀를 노출할 수 있는지 판단하는 품질 라벨.
- `evidenceGates`: 첫 화면의 시계열/경로/동행/회사노출/민감도 gate. UI가 재계산하지 않는다.
- `falsifiers`: 상관, peer dispersion, 회귀 품질, stale data처럼 thesis를 약하게 만드는 조건.
- `scenarios`: 시나리오 이름과 affected driver만. 손익 산출은 하지 않는다.
- `missing`: 결손·미배선·표본 부족·stale 가능성.

---

## 3. 엔진 산출물 계약

`MacroLensSnapshot`은 UI 계약이고, 강한 분석의 원천은 아래 산출물이다.

```typescript
export interface MacroDriverView {
  id: string;              // canonical: MACRO_SERIES.id 또는 registry id
  label: string;
  group: 'fx' | 'rates' | 'inflation' | 'growth' | 'credit' | 'commodity' | 'market';
  seriesId: string | null;
  unit: string | null;
  directionSemantics: string;
  defaultLagMonths: number | null;
  sourceRef: string;
  sourceLineage?: {
    source: 'ECOS' | 'FRED';
    sourceSeriesId: string;
    date: string | null;
    value: number | null;
    unit: string | null;
    artifactPath: string;
    asOfPolicy: string;
    status: 'observed' | 'missing';
  };
}

export interface MacroTransmissionEdgeView {
  driverId: string;
  market: 'KR' | 'US' | 'GLOBAL';
  sectorKey: string;
  industryKey?: string;
  channel: 'revenue' | 'margin' | 'balanceSheet' | 'cashFlow' | 'valuation';
  financialLine: string;
  valuationLever?: 'discountRate' | 'growth' | 'margin' | 'multiple' | 'riskPremium';
  sign: 'positive' | 'negative' | 'mixed' | 'unknown';
  lagMonths: [number, number] | null;
  confidence: 'high' | 'medium' | 'low' | 'blocked';
  evidenceLevel: 'observed' | 'sectorPrior' | 'template';
  evidenceLabel?: 'OBS' | 'PRIOR' | 'TPL' | 'LOCK';
  requiredCompanyEvidence: string[];
  falsifiers?: string[];
  sourceRefs: string[];
}

export interface MacroExposureQuality {
  status: 'qualitativeOnly' | 'blocked';
  reason: string;
  blockedReason: string;
  missingEvidence: string[];
  sourceRef: string;
  nObs: number | null;
  rSquared: number | null;
  window: string | null;
  frequency: 'monthly' | 'quarterly' | 'annual' | null;
  lagMonths: number | null;
  coverage: 'company' | 'sectorOnly' | 'missing';
}

export interface MacroEvidenceGate {
  id: 'macroData' | 'path' | 'comove' | 'company' | 'quant';
  labelKr: string;
  labelEn: string;
  value: string;
  detailKr: string;
  detailEn: string;
  status: 'ok' | 'watch' | 'blocked';
  sourceRef: string;
  blocks: string[];
}

export interface MacroMissing {
  id: string;
  status: 'missing' | 'partial' | 'notWiredYet' | 'staleRisk';
  reason: string;
  sourceRef: string;
}

export interface MacroFalsifierView {
  type: 'coMovement' | 'peerDispersion' | 'regressionQuality' | 'staleData' | 'missingCompanyEvidence';
  driverId?: string;
  label: string;
  severity: 'info' | 'warning' | 'blocker';
  detail: string;
  sourceRef?: string;
}
```

원칙:

- `macro.transmission`은 `MacroDriverView`와 `MacroTransmissionEdgeView`를 낸다. 현재 공개 호출은 `dartlab.macro("transmission", market="KR", sectorKey="semiconductor")`다.
- 기존 analysis macro 표면은 `MacroExposureQuality`와 회사별 checkpoint를 낸다.
- UI는 두 산출물을 합쳐 보여주되 숨은 수학을 만들지 않는다.
- `blocked` edge는 숨기지 않고 이유를 표시한다.

---

## 4. Canonical ID 규칙

경제지표 id 혼선은 Macro Lens 신뢰도를 깨는 1순위 리스크다.

- canonical id는 `ui/packages/contracts/src/macro.ts::MACRO_SERIES`를 따른다.
- ECOS/FRED 원본 series id는 `sourceSeriesId`로만 둔다.
- prior/analysis 코드의 레거시 id는 registry alias로 명시한다.
- alias가 없는 id는 `notWiredYet`로 내리고 driver edge에 쓰지 않는다.

예상 부채:

| 레거시 id | canonical 후보 | 처리 |
|---|---|---|
| `KRW_USD` | `USDKRW` | alias 필요 |
| `PMI` | 없음 또는 신규 series 필요 | 미배선 처리 |
| `BASE_RATE_KR`류 | `BASE_RATE` | alias 필요 |

---

## 5. 결손과 신뢰도

결손값은 0으로 대체하지 않는다.

| 상태 | 의미 | UI 문구 |
|---|---|---|
| `missing` | 데이터 자체 없음 | 데이터 없음 |
| `partial` | 일부 기간/시리즈만 있음 | 부분 데이터 |
| `notApplicable` | 업종/회사에 적용 부적합 | 해당 없음 |
| `notWiredYet` | 로컬/심화 연산 미배선 | 아직 연결 전 |
| `staleRisk` | 기준일 오래됨 | 기준일 확인 필요 |
| `lowN` | 표본 부족 | 표본 부족 |
| `lowR2` | 회귀 설명력 낮음 | 회귀 신뢰 낮음 |

회귀 기반 값은 다음 라벨 없이는 노출하지 않는다.

- `nObs`
- `rSquared`
- `window`
- `frequency`
- `targetMetric`
- `sourceRef`

---

## 6. 향후 새 산출물

새 산출물이 필요해도 per-company artifact는 만들지 않는다. 시장 단위 artifact만 허용한다.

후보:

```text
macro/lens/kr.json
macro/lens/us.json
macro/lens/transmission.json
landing/dashboards/macroLens.json
```

허용 내용:

- macro axis별 최신 신호 압축
- 지표 그룹별 상태
- driver registry와 canonical id alias
- sectorTailwind 계산 근거
- transmission edge
- quality/freshness summary
- source/date/freshness

금지 내용:

- 종목별 매크로 점수 precompute
- 회사별 추천/수혜/피해 라벨
- raw 원문 또는 외부 API 응답 복제
- `analysis` 내부 계산을 macro artifact에 섞는 것
- 회사별 회귀 결과를 시장 artifact에 섞는 것

생성 경계:

- sync는 online 가능.
- prebuild는 offline only, HF 다운로드만.
- 터미널은 public/local 공통배선으로 읽는다.

---

## 7. 출처 표기

다이얼로그 하단 또는 출처 탭에는 다음을 노출한다.

- `출처: 한국은행 ECOS · FRED (St. Louis Fed)` (`MACRO_ATTRIBUTION`)
- HF artifact path
- `macro.asOf`
- 지표별 `seriesId`
- 갱신주기: 일배치/월별/분기별 등 가능한 범위
- `상관은 인과가 아님`
- `배치 데이터이며 실시간 투자판단 아님`
