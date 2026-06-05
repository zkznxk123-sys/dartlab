---
id: operation.compareTargets
title: 여러 종목 토픽-기간 그리드 비교
category: operation
purpose: 두 종목 이상을 같은 토픽·기간 그리드로 정규화하여 직접 비교한다. XBRL 표준 이름 매핑 ~97% 로 양식이 아닌 기업을 본다.
whenToUse:
  - 여러 종목 비교
  - 종목 묶음 분석
  - "삼성전자 vs SK하이닉스"
  - peer compare
  - "AAPL과 MSFT"
  - 동종 산업 비교
  - cross-target ranking
procedure:
  - 종목 코드 2 개 이상 결정 (한국 6 자리 또는 미국 ticker)
  - 토픽·기간 그리드 정의 (예 bs · 재고 · 2024Q4)
  - dartlab.compare(codes, *, topic, period, scope, freq) 호출
  - 재무제표 topic(bs/is/cf/cis/sce)은 acode 단위 원 환산 셀 비교
  - 주석·서술 topic은 disclosureKey·scope·leafType 정렬키로 row 비교
  - 결손은 NaN 으로 유지 (0 채움 금지)
  - 차이 비교 + 인과 해석 (필요 시 engines.story 로 위임)
examples:
  - "삼성전자와 SK하이닉스 영업이익률 5 년 비교해줘"
  - "AAPL과 MSFT 부채비율 추이 보여줘"
  - "현대차와 기아 매출 분기별 정렬"
  - "동종 산업 peer 5 개 ROE 순위"
expectedOutputs:
  - Polars DataFrame (식별 컬럼 + 회사 셀 컬럼)
  - 재무 topic은 acode·label·scope + 회사별 원 환산값
  - row topic은 chapter·sectionLeaf·blockLeaf·leafType·disclosureKey·scope + 회사별 원문 셀
  - 결손 NaN (강제 0 채움 없음)
requiredEvidence:
  - target (종목코드 명시)
  - topic (토픽 이름)
  - period (분기 YYYYQn 또는 연도 YYYY)
  - tableRef (출력 표)
  - valueRef (개별 수치)
  - executionRef (실행 코드)
  - sourceRef
failureModes:
  - 토픽 이름 변종 미정규화 (매출액·영업수익·revenue 가 다른 컬럼으로 분리)
  - 기간 frequency 혼합 (분기 + 연도가 한 표에 섞임)
  - target 일부가 다른 provider (DART/EDGAR) 인데 같은 표로 비교
  - 결손을 0 또는 직전 분기 값으로 채워 추세 왜곡
forbidden:
  - 결손을 0 으로 채우기
  - source priority 무시
  - KO/US 혼합 직접 비교
  - EDGAR 재무 adapter 확정 전 US finance compare
  - 비교 대상 회사명/티커 영문/한글 변종 혼용
knowledgeRefs:
  - engines.company
  - engines.scan
  - operation.philosophy
linkedSkills:
  - operation.sixActsAnalysis
sourceRefs:
  - dartlab://skills/operation.compareTargets
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
    status: supported
    notes: []
status: observed
lastUpdated: "2026-05-12"
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

# 여러 종목 비교 — 토픽-기간 그리드 정규화

## 무엇을 하나

같은 토픽 (매출·이익률·부채비율·현금흐름 등) 을 여러 종목에 걸쳐 같은 기간 그리드에서 *직접 비교* 가능한 표로 만든다. dartlab 의 첫 번째 사상 — **모든 기간은 비교 가능해야 하고, 모든 회사는 비교 가능해야 한다** — 의 실행 표면.

핵심은 *정규화*. DART 공시는 같은 매출액을 `ifrs-full_Revenue` · `dart_Revenue` · `매출액` · `영업수익` 4 변종으로 표기. provider 의 `canHandle` 체인이 ~97% 표준 이름으로 매핑.

## 공개 호출 방식

```python
import dartlab

# 주석/서술 row 비교 — 행은 disclosureKey·scope·leafType 으로 정렬
notes = dartlab.compare(["005930", "000660"], topic="재고", period="2025Q4")

# 재무제표 셀 비교 — acode 단위, 값은 원 환산
bs = dartlab.compare(["005930", "000660"], topic="bs", period="2025Q4", scope="consolidated")
```

`period=None` 이면 topic 필터 후 최신 공통 시점을 고른다. 공통 시점이 없으면 최신 union 시점을 쓰며,
비교 대상 중 한 회사에 값이 없으면 해당 회사 컬럼은 null 로 남긴다.

`dartlab.compareDiagnostics(...)` 는 같은 입력에 대해 소비자용 반환 계약을 설명한다. `identityColumns` 는 행 식별
컬럼, `cellColumns` 는 회사 값 컬럼, `cellColumnShape` 는 `singlePeriod`/`multiPeriod`/`empty`,
`valueUnit` 은 재무 셀모드에서 `KRW` 다. 뷰어/AI 층은 DataFrame 컬럼명을 재추론하지 않고 이 계약을 먼저
확인한다.

`Company` 단일 진입은 한 회사 원표 확인용이다. 회사 간 비교는 `dartlab.compare(...)`가 공식 표면이다.

## 정공법 — 결손 처리

결손 (특정 분기 미공시 · 회사가 그 시점 비상장) 은 **NaN 유지**. 0 채우기 · 직전 값 forward-fill · 산업 평균으로 imputation 금지. 추세 해석을 왜곡한다.

시각화 시 NaN 은 *공백* 으로 표현 (`pl.col("value").is_null()` 마스킹).

## 통화 단위 — 시장 경계

DART 종목끼리와 EDGAR 종목끼리만 비교한다. KO/US 혼합은 같은 표에서 막는다.
재무제표 셀 비교는 현재 DART(KR) 원 환산 계약만 observed 이며, US finance 는 EDGAR native adapter 확정 전까지 차단한다.

## 다음 단계

- 비교 결과를 **6 막 인과 서사** 로 묶기 → [operation.sixActsAnalysis](/skills/operation.sixActsAnalysis).
- 산업 평균 + peer 순위 → `engines.scan`.
- 신용등급 동행 비교 → `engines.credit`.

## 무엇을 하지 *않는가*

- 결손 0 채움.
- 회사명 / 티커 변종 혼용 (한 표 안에서 일관 사용).
- KO · US 혼합 직접 비교.
- EDGAR 재무 adapter 없이 US finance compare.
- 다른 frequency (분기 + 연) 한 표 안 혼합.

근본: `operation.philosophy` "비교 가능성" 섹션 · `engines.scan` · CLAUDE.md "통합 아키텍처" 섹션.
