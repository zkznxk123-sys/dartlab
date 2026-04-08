# Review Audit

종목별 `c.review()` 실측 audit으로 발견된 버그와 fix 기록. 같은 함정 반복 방지용.

## 진행 절차

1. `c.review()` 단일 섹션씩 호출(메모리 안전), 표/숫자 line by line 읽기
2. 의심점 → `c.show("IS"/"BS"/"CF"/"inventory" 등)` 직접 호출로 교차검증
3. 진짜 버그면 아래 표에 등록 → 보수적 fix → 재검증
4. 종목 1개 끝나면 다음 종목으로 커버리지 확장

## 단위 함정 (Plan v4 root fix 후 — 회귀 차단됨)

- `c.show("inventory" 등)` notes 모두 **원 단위** 노출 (Plan v4 P1 후)
  - 4 분산 parser (costByNature/tangibleAsset/segment/affiliate) 도 `normalizeFromUnitScale` 경유
  - notes 내부 표준은 백만원이지만 노출 시점에 ×1_000_000
- `c.show("IS"/"BS"/"CF")` → **원**
- 새 parser 추가 시 raw `*= unit` 금지 (sentinel `test_no_global_raw_unit_multiply` 차단)

## Q4 컬럼 함정 (Plan v4 root fix 후 — 자동 해결)

- Plan v4 Layer A 후 `c.show("IS"/"CIS"/"CF")` 가 분기 컬럼 + **annual 컬럼 (`{year}`)** 자동 노출
- calc 가 `row['2025']` 직접 read 하면 연간값 (Q1+Q2+Q3+Q4 합)
- `row['2025Q4']` 는 Q4 단독값 (분기 단독)
- ttmSum/getFlowValue/_annualizeFlow 헬퍼 모두 제거됨 (Plan v5)
- 새 calc 작성 시 sentinel `test_no_q4_literal_in_subscript` + `test_no_q4_literal_assigned_to_var` 가 직접 read 차단

## 종목별 발견 버그

### 2026-04-07 — SK하이닉스(000660)

#### 1막~2막 (이전 세션)

| # | 위치 | 증상 | 원인 | Fix | 상태 |
|---|---|---|---|---|---|
| 1 | `review/builders.py::_notesDetailBlocks` | 비용성격별 "원재료사용 1,210만" (실제 12.1조) | notes 가 백만원 단위 노출 → 6자리 축소 표시 | Plan v4 Layer 1: 4 분산 parser 가 `normalizeFromUnitScale` 경유, 모든 notes 원 단위 노출 | ✅ root fix |
| 2 | 영업레버리지(DOL) | 2024Q4/2023Q4/2018Q4 None | 부호 전환(음→양) 시 직관적 해석 불가로 의도적 None 가능성 큼 | — | ⏸ 보류 |
| 3 | 수익성 — 매출총이익률 표 | 본문 60.4% vs 표 57.3%→68.8% | 재현 불가 (이전 세션 오인) | — | ❌ 무효 |
| 4 | `review/narrative.py` 7 detector | "매출 +66.1% / 영업이익률 40.9%→58.4%" — 표 (46.8%/35.5%→48.6%) 와 불일치 | DART IS/CF Q4 컬럼이 분기 단독값인데 detector 가 연간값으로 오인 | Plan v4 Layer A: pivot 결과에 annual 컬럼 자동 노출 → `row['2025']` 직접 read | ✅ root fix |

#### 3막 (현금전환)

| # | 위치 | 증상 | 원인 | 우선순위 |
|---|---|---|---|---|
| 5 | `cashflow.calcCashFlowOverview` 재무CF 2025 | `-` (결손) | 재무활동현금흐름 snakeId 매핑 누락 가능 또는 분기 데이터 부족 | 중간 |

#### 4막 (안정성)

| # | 위치 | 증상 | 원인 | 우선순위 |
|---|---|---|---|---|
| 6 | `notes.borrowings` 차입금 구성 표 | 2022 이전 모두 `-` (4년만 시계열) | DART notes 시계열 확장 부족 + parser 가 일부 sub-row 헤더를 데이터 row 로 잘못 추출 | 중간 |
| 7 | `notes.borrowings` 표에 "OAT Nego, Banker's Usance, 일반대출" 등 sub-row 헤더가 데이터 row 로 잘못 노출 | 모든 값 `-` | parser 가 heading row + data row 구분 못 함 | 낮음 |
| 8 | `notes.lease` 표 | "기말장부금액" 200억 (2025) vs 13억 (2024) 큰 변동, "감가상각 -90억 / 기초 13억" 불일치 | parser 가 분기 데이터 + 연간 데이터 혼합 가능 | 낮음 |

#### 5막 (자본배분)

| # | 위치 | 증상 | 원인 | 우선순위 |
|---|---|---|---|---|
| 9 | `capitalAllocation.calcDividendPolicy` 배당성장률 +8600.8% (2022) | 2021 47억 → 2022 4126억 base effect | 작은 base 에서 큰 base 전환 — 통계적 정상이지만 사용자 오인 | 낮음 — cap 또는 표시 보강 |

#### 6막 (가치평가)

| # | 위치 | 증상 | 원인 | 우선순위 |
|---|---|---|---|---|
| 10 | 6막 두 모델 결과 큰 괴리 | 종합 적정가 19.7만원 vs 확률가중 목표가 129.7만원 (6배 차이) | 종합 적정가 = DCF/DDM/RIM 평균 (보수적) / 확률가중 목표가 = 시나리오 baseline (낙관적). 두 모델 통합 부재 | **높음** — 사용자 혼란 |
| 11 | 6막 RIM 적정가 199,304 vs DCF 174,422 | 자릿수 같으나 단위 표시 (원/주당) 불명확 | 사용자가 19.9만원 또는 199,304천원 오인 가능 | 낮음 |

### 2026-04-08 — 5종목 빠른 스캔 (B 단계)

#### 005930 삼성전자
- ✅ 1막~5막 정상 (매출 +10.9%, 영업이익률 10.9→13.1%, 배당 9.9조 8년 연속, 자사주 8.2조)
- ⚠ 6막: 종합 적정가 5.7만원 vs 확률가중 14.0만원 vs 현재가 19.6만원 — **#10 패턴 재확인** (모델 괴리)
- 종합 판정: 고평가 (-247% DCF 안전마진)

#### 011200 HMM
- ⚠ 배당성장률 +2913.9% (2019) — **#9 패턴 재확인** (small base effect)
- ⚠ 6막: 가중 목표가 51,100 vs 현재가 20,150 (업사이드 +154%) — 사이클 회복 시나리오

#### 042660 한화오션
- ✅ 배당 없음 (정상)
- ⚠ 6막: 가중 목표가 139,018 vs 현재가 120,900 (정상 범위)

#### 373220 LG에너지솔루션
- ⚠ 배당성장률 -100.0% (2023) — 배당 중단 또는 데이터 결손
- ⚠ 6막: 가중 목표가 51,754 vs 현재가 408,500 (**업사이드 -87%**, 큰 괴리)
- 종합 판정 vs 시장가 큰 괴리 — IPO 후 미실현 회사 valuation 한계

#### 모든 종목 공통

| # | 위치 | 증상 | 원인 | 우선순위 |
|---|---|---|---|---|
| 12 | 모든 종목 BS 로딩 시 stderr | `BS: 동의어 계정 1건 병합 (먼저 나온 값 우선, snakeId 유실 가능): ['매출채권및기타채권']` 경고 매번 출력 | mapper 가 한국어 `매출채권및기타채권` 을 여러 snakeId 에 매핑 (`trade_and_other_receivables` + `trade_and_other_current_receivables`) → 병합 시 snakeId 유실 | 중간 — alias 정합성 fix 필요 |
| 13 | `capitalAllocation.calcDividendPolicy` 배당성장률 | 작은 base 에서 큰 값 전환 시 +수천% (3 종목 확인) | base effect — 통계적 정상 | 낮음 — cap 또는 fmt 보강 |
| 14 | 6막 가치평가 종합 vs 확률가중 모델 괴리 | 5 종목 모두 두 모델 결과 차이 큼 | 종합 = DCF/DDM/RIM 평균 (보수적), 확률가중 = 시나리오 baseline (다른 가정) | **높음** — review 모듈 구조 |
