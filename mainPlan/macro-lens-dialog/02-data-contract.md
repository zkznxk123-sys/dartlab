# 02. 데이터 계약

상태: 설계 v0.1
범위: Macro Lens 다이얼로그가 읽는 데이터와 향후 확장 산출물 계약.

---

## 1. 재사용 데이터

첫 구현은 새 수집 없이 다음 자산을 재사용한다.

| 데이터 | 위치 | 용도 |
|---|---|---|
| macro regime | `dashboards/macro.json` | KR/US phase, quadrant, sectorTailwind |
| macro observations | `macro/{fred,ecos}/observations.parquet` | 지표 최신값·스파크라인·차트 오버레이 |
| macro catalog | `ui/packages/contracts/src/macro.ts::MACRO_SERIES` | 지표명·단위·소스·그룹 |
| company tailwind | `ui/packages/surfaces/src/terminal/lib/engine.ts::tailwindOf` | 선택 종목 업종의 blended tailwind |
| sector tailwinds | `eng.sectorTailwinds()` | 좌측 순풍/역풍 섹터 목록 |
| co-movement | `ui/packages/surfaces/src/terminal/lib/coMovement.ts` | 종목 월수익률과 거시 1차차분 상관 |
| price/finance snapshot | terminal `Company` shape | 회사 checkpoint 표시 |

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
  observables: MacroObservableView[];
  sectorBinding: MacroSectorBinding | null;
  companyBinding: MacroCompanyBinding;
  coMovement: MacroCoMovementView[];
  scenarioEntrypoints: MacroScenarioEntrypoint[];
  sourceRefs: MacroSourceRef[];
  missing: MacroMissing[];
}
```

필드 의미:

- `marketPhase`: `macro.json`의 KR/US phase와 quadrant.
- `observables`: `MACRO_SERIES` + `MacroPort.getLatest()`에서 온 최신 지표.
- `sectorBinding`: `co.tailwind`와 `eng.sectorTailwinds()` 기반 섹터 순풍/역풍.
- `companyBinding`: 회사 재무 checkpoint. 예: 부채비율, 영업이익률, CFO/NI 등 이미 terminal `Company`가 가진 값만 사용한다.
- `coMovement`: 차트에서 계산한 종목-거시 동행상관.
- `scenarioEntrypoints`: 시나리오 이름과 affected driver만. 손익 산출은 하지 않는다.
- `missing`: 결손·미배선·표본 부족·stale 가능성.

---

## 3. 결손과 신뢰도

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

## 4. 향후 새 산출물

새 산출물이 필요해도 per-company artifact는 만들지 않는다. 시장 단위 artifact만 허용한다.

후보:

```text
macro/lens/kr.json
macro/lens/us.json
landing/dashboards/macroLens.json
```

허용 내용:

- macro axis별 최신 신호 압축
- 지표 그룹별 상태
- sectorTailwind 계산 근거
- source/date/freshness

금지 내용:

- 종목별 매크로 점수 precompute
- 회사별 추천/수혜/피해 라벨
- raw 원문 또는 외부 API 응답 복제
- `analysis` 내부 계산을 macro artifact에 섞는 것

생성 경계:

- sync는 online 가능.
- prebuild는 offline only, HF 다운로드만.
- 터미널은 public/local 공통배선으로 읽는다.

---

## 5. 출처 표기

다이얼로그 하단 또는 출처 탭에는 다음을 노출한다.

- `출처: 한국은행 ECOS · FRED (St. Louis Fed)` (`MACRO_ATTRIBUTION`)
- HF artifact path
- `macro.asOf`
- 지표별 `seriesId`
- 갱신주기: 일배치/월별/분기별 등 가능한 범위
- `상관은 인과가 아님`
- `배치 데이터이며 실시간 투자판단 아님`

