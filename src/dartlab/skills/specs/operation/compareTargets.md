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
  - 토픽·기간 그리드 정의 (예 IS.revenue · 2024Q1~2024Q4)
  - dartlab.scan 또는 Company.panel 반복 호출로 raw 추출
  - XBRL 표준 이름 매핑 적용 (provider canHandle 자동)
  - target × topic × period DataFrame 정규화
  - 결손은 NaN 으로 유지 (0 채움 금지)
  - 차이 비교 + 인과 해석 (필요 시 engines.story 로 위임)
examples:
  - "삼성전자와 SK하이닉스 영업이익률 5 년 비교해줘"
  - "AAPL과 MSFT 부채비율 추이 보여줘"
  - "현대차와 기아 매출 분기별 정렬"
  - "동종 산업 peer 5 개 ROE 순위"
expectedOutputs:
  - Polars DataFrame (target × topic × period)
  - source 컬럼 (DART / EDGAR)
  - 정규화된 표준 이름 (~97% 매핑)
  - 결손 NaN (강제 0 채움 없음)
requiredEvidence:
  - target (종목코드 명시)
  - topic (토픽 이름)
  - period (분기 YYYYQN 또는 연도 YYYY)
  - tableRef (출력 표)
  - valueRef (개별 수치)
  - executionRef (실행 코드)
  - sourceRef
failureModes:
  - 토픽 이름 변종 미정규화 (매출액·영업수익·revenue 가 다른 컬럼으로 분리)
  - 기간 frequency 혼합 (분기 + 연도가 한 표에 섞임)
  - target 일부가 다른 provider (DART/EDGAR) 인데 통화 단위 미환산
  - 결손을 0 또는 직전 분기 값으로 채워 추세 왜곡
forbidden:
  - 결손을 0 으로 채우기
  - source priority 무시
  - 환율 환산 없이 KRW/USD 직접 비교
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

# 2 종목 영업이익률 5 년 분기 비교
df = dartlab.scan(
    targets=["005930", "000660"],
    topics=["IS.operatingMargin"],
    periods=["2020Q1", "2020Q2", "2020Q3", "2020Q4",
             "2021Q1", "2021Q2", "2021Q3", "2021Q4",
             "2022Q1", "2022Q2", "2022Q3", "2022Q4",
             "2023Q1", "2023Q2", "2023Q3", "2023Q4",
             "2024Q1", "2024Q2", "2024Q3", "2024Q4"],
)
print(df.pivot(values="value", index="period", columns="target"))
```

`Company` 진입도 가능:

```python
c1 = dartlab.Company("005930")
c2 = dartlab.Company("000660")
# 각 회사에서 동일 topic 호출 후 join — 명시적 비교
```

## 정공법 — 결손 처리

결손 (특정 분기 미공시 · 회사가 그 시점 비상장) 은 **NaN 유지**. 0 채우기 · 직전 값 forward-fill · 산업 평균으로 imputation 금지. 추세 해석을 왜곡한다.

시각화 시 NaN 은 *공백* 으로 표현 (`pl.col("value").is_null()` 마스킹).

## 통화 단위 — 환산 명시

DART 종목은 KRW, EDGAR 종목은 USD. 한 표에 섞으면 환율 환산 필수:

```python
fx = dartlab.macro("usdKrw", date="2024-12-31")
df_normalized = df.with_columns(
    pl.when(pl.col("source") == "EDGAR")
      .then(pl.col("value") * fx)
      .otherwise(pl.col("value"))
      .alias("value_krw")
)
```

또는 비율 (마진 · 성장률 · 회전율) 만 비교 — 통화 무관.

## 다음 단계

- 비교 결과를 **6 막 인과 서사** 로 묶기 → [operation.sixActsAnalysis](/skills/operation.sixActsAnalysis).
- 산업 평균 + peer 순위 → `engines.scan`.
- 신용등급 동행 비교 → `engines.credit`.

## 무엇을 하지 *않는가*

- 결손 0 채움.
- 회사명 / 티커 변종 혼용 (한 표 안에서 일관 사용).
- 환산 없이 KRW · USD 직접 산술.
- 다른 frequency (분기 + 연) 한 표 안 혼합.

근본: `operation.philosophy` "비교 가능성" 섹션 · `engines.scan` · CLAUDE.md "통합 아키텍처" 섹션.
