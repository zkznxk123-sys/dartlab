---
id: "engines.analysis.revenueStructure"
title: "Analysis - 수익구조"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 수익구조 축 응용 — 이 회사는 무엇으로 돈을 버는가."
whenToUse:
  - "analysis"
  - "수익구조"
  - "이 회사는 무엇으로 돈을 버는가"
inputs:
  - "Company 또는 종목코드"
  - "기준 기간"
outputs:
  - "축별 dict"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.revenueStructure"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "tableRef"
  - "valueRef"
  - "dateRef"
  - "executionRef"
expectedOutputs:
  - "공개 호출"
  - "대표 반환 형태"
  - "검증 결과"
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
  - 근거 없는 숫자를 만들지 않는다.
  - 결손값을 0 으로 채우지 않는다.
  - 단일 axis 결과를 최종 투자 결론으로 제시하지 않는다.
  - 사업부별 / 지역별 / 제품별 매출 분리 미명시 답변 금지.
  - 외화 매출 비중 무시 금지 — 환율 변동 영향 별도 표기.
failureModes:
  - 사업부 segment 정의 변경 (회사 재편) 시 시계열 단절 미반영
  - 지역별 매출 분리에서 *수출* vs *해외 자회사* 차이 무시
  - 제품 mix 변화 (신제품 출시) 영향을 가격 변동으로 오해
  - 일회성 대형 계약 (M&A 인수 후 매출 통합) 영향 미분리
  - 외화 매출 환율 영향 (환산 vs 거래) 미명시
examples:
  - 삼성전자 사업부별 매출
  - 지역별 매출 (수출 비중)
  - 제품 mix 변화 (반도체 vs 모바일 vs 가전)
  - 환율 영향 분리
  - 신규 사업 매출 비중 추세
linkedSkills:
  - engines.analysis.revenueForecast
  - engines.analysis.growth
  - engines.analysis.macroSensitivity
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 수익구조 축 응용 skill — 이 회사는 무엇으로 돈을 버는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "수익구조")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "수익구조", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 수익구조 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

## 대표 반환 형태

dict 반환. 공통 키:

- `items`: 축별 계산 항목과 결과
- `history`: 기간별 시계열
- `displayHints`: 표/차트 표시 힌트
- `turningPoints`: 전환점 (해당 시)
- `dataAsOf`, `assumptions`, `flags`: 데이터 기준일, 가정, 결손/이상 신호
- `_summary`: 사람이 읽을 요약
- `tableRef` / `valueRef` / `dateRef` / `executionRef`: evidence 참조

전체 반환 키는 base SKILL `engines.analysis` 표 + `_analysisImpl` docstring 으로 검산.

## 기본 실행 순서

1. 대상, 기간, 원천 데이터 확정.
2. 위 공개 호출을 그대로 실행.
3. `dataAsOf`, 결손 값, `flags`, `assumptions` 점검.
4. 숫자 claim 은 `tableRef` / `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 보고서 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 대표 반환 키, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 설계 깊이 (운영 SSOT)

### 데이터 소스 3

| 소스 | 접근 | 내용 | 한계 |
|------|----------|------|------|
| **segments** | `c.segments()` (K-IFRS 주석) | 부문별 매출 / 영업이익 / 감가상각 | 연간만, 당기/전기 2 년뿐. sections 미노출 |
| **salesOrder** | `c.salesOrder()` (매출실적/수주) | 제품 / 서비스별 매출 · 수주잔고 | 컬럼명 v1/v2/v3 문제, 50~60% 커버리지 |
| **IS (finance)** | `c.show("IS")` (XBRL) | 매출액 / 매출원가 / 영업이익 분기 | 연결 합산만, 부문 분해 불가 |

핵심 — `segments().tables` 에 데이터가 이미 다 있는데 revenue DataFrame 만 만들고 나머지를 버리고 있었다. allTables 완전 활용 시 segment 영업이익 / 영업이익률 / region / product 분해 모두 가능.

### 부문 표준화 — 업계 조사

같은 회사도 연도별 부문 재편 (삼성전자 2022 "CE/IM/반도체/DP/Harman" → 2024 "DX/DS/SDC/Harman"). **완전 자동 솔루션은 어디에도 없다**:

| 주체 | 접근법 |
|------|--------|
| FactSet RBICS | 섹터 전문 애널리스트 수작업 매핑 (~45,000 사, 연 1 회) |
| S&P Capital IQ | "As Reported" + "Standardized" 이중, 표준화 수작업 |
| Refinitiv | 35 년+ 수작업 |
| Compustat | "considerable measurement error/noise" 인정 |
| OpenBB / FinanceToolkit | 데이터 제공자 의존 |
| EdgarTools | concept 매핑만, segment member 변경 추적 없음 |

XBRL dimension member 도 해결 못 함 — `CESegmentMember` → `DXSegmentMember` 자동 연결 정보 없음.

**회계 기준의 무기 — recast (재작성)** — IFRS 8 / ASC 280 의무. 2024 년 Filing 의 "전기" 는 이미 DX/DS 기준으로 재작성. **Filing 내 recast 데이터가 가장 신뢰할 수 있는 연결 고리**.

### dartlab 해결 방안

1. **recast 우선** — 같은 Filing 의 당기/전기를 1 차 시계열로 사용 (이미 구조 맞춤)
2. **Filing 간 연결** — 연도별 당기 매출 이어 붙이되 부문명 변경 시 **break 를 명시적으로 표시**
3. **강제 연결 금지** — DX ≠ CE+IM 자동 매핑 안 함. 업계 표준 "사람이 매핑" 인데 코드로 억지로 하면 오류
4. **변경 감지** — 부문 목록 바뀌면 "부문 재편 감지" 플래그
5. **수작업 매핑 테이블** — 주요 기업의 알려진 변경은 `sectionMappings.json` 패턴처럼 점진 축적

**한 줄 원칙** — break 를 숨기지 않는다. 업계 표준이 수작업인 영역을 코드로 억지 자동화하면 신뢰성을 잃는다.

### 9 calc 함수 (Phase 1 완료)

`src/dartlab/analysis/financial/revenue.py` 위 9 함수가 "이 회사는 무엇으로 돈을 버는가" 질문에 답한다:

1. **calcCompanyProfile** — 업종 / 주요제품 맥락
2. **calcSegmentComposition** — 부문별 매출 / 비중 / 영업이익률
3. **calcSegmentTrend** — 다년간 부문별 매출 추이 + YoY
4. **calcBreakdown(sub)** — 지역별 / 제품별 매출 분해
5. **calcRevenueGrowth** — 매출 YoY · 3Y CAGR · 분기 시계열
6. **calcGrowthContribution** — 부문별 성장 기여 분해
7. **calcConcentration** — HHI · 1 위 비중 · 내수 비중
8. **calcRevenueQuality** — 영업CF / 순이익 · 매출총이익률 추세
9. **calcFlags** — 경고 / 기회 플래그

데이터 접근 — `company.select("segments")` / `company.select("IS", [...])` / `company.finance.ratios` / `company.finance.ratioSeries` / `company.sector`. gather import 없음.

### review 출력 설계

review = 뷰어. 보기 좋아야 한다. 데이터 나열이 아닌 판단이 있는 보고서.

**기간** — 부문별 구조: 최근 연간 1~2 년 / 전체 손익 추이: 최근 4~8 분기 / 영업이익률: 최근 4~8 분기.
**금액 단위** — 조 / 억 (원 단위 아님). `_formatAmount()` 활용.

**지면 제약**:
- 부문 테이블 — 최대 8 행 (8 초과 시 상위 7 + "기타" 합산)
- 분기 추이 — 최근 4~8 분기 (전체 40 분기 나열 금지)
- 서술 — 2~3 문장 핵심 판단
- Flag — 최대 3 (경고 2 + 기회 1)

### 불가능한 분석

| 분석 | 이유 |
|------|------|
| 부문별 분기 매출 | K-IFRS 주석은 연간 보고서만 부문 공시 |
| 고객 집중도 | DART 미공시 (SEC 10-K 한정) |
| Price / Volume / Mix | 가격 / 물량 분리 데이터 없음 |
| Organic vs Inorganic | M&A 매출 분리 불가 |
| 부문별 ROIC | 일부 회사만 부문별 투하자본 공시 (영업이익률로 대체) |

### Phase 2 향후 확장

- 제품별 매출 (salesOrder 데이터 품질 개선 후)
- 지역별 매출 (segments 에서 지역 테이블 추출)
- 다년간 부문 추이 (여러 보고서 기간 파싱)
- 부문별 성장 기여도 분해

## 변경 이력

- 2026-03-26 — 수익구조 분석 설계 + 9 calc 함수 Phase 1 구현
- 2026-05-07 — skill spec lock (axis API wrapper)
- 2026-05-12 — `analysis/financial/_01_revenueStructure.md` → 본 spec "설계 깊이" 섹션 통합 (Skill OS 운영 SSOT 승격)
