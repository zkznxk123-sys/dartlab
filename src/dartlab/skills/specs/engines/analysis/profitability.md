---
id: engines.analysis.profitability
title: 수익성 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 매출, 마진, 이익의 변화를 기간·섹터 맥락과 함께 분석한다.
whenToUse:
  - 수익성 분석
  - 이익률 추세
  - 마진 추세
  - 영업이익 개선 원인
  - ROE
  - ROA
  - 매출총이익률
  - 영업이익률
  - 순이익률
  - 산업 평균 비교
inputs:
  - 기업명 또는 종목코드
outputs:
  - profitability thesis
  - 수익성 표
  - 원인과 한계
capabilityRefs:
  - Company.analysis
  - Company.show
  - scan.profitability
  - scan.quality
  - macro
datasetRefs:
  - dart.scan
  - dart.scan.finance-lite
  - edgar.finance
toolRefs:
  - search_reference
  - EngineCall
  - RunPython
  - finalize_answer
knowledgeRefs:
  - financialStatementConcepts
  - dartlabCausalSixActs
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - profitability thesis
  - 기간별 수익성 표
  - 업황/섹터 연결
  - 한계
visualGuidance:
  - 매출, 영업이익률, 순이익률 같은 시계열 표가 있을 때만 chart를 만든다.
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
    dataSources:
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data edgar/finance/{ticker}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - Company 재무 snapshot 또는 finance-lite prebuild를 먼저 확인한다.
    limitations:
      - live macro 보강은 서버 환경에서 수행한다.
failureModes:
  - 매출 증가만 보고 수익성 개선 단정 — 단가 vs 물량 vs mix 분리 필요
  - 같은 기간이 아닌 마진 비교 — Q vs YTD vs 연환산 혼용 시 답변에 period 명시
  - 산업 분기 미고려 — 제조 평균 ROE 8% / 금융 7% / IT 12% / 바이오 음수. peer 비교 시 같은 industryHint 한정
  - finance-lite 계정명을 확인하지 않고 고정 계정 id만 가정 — normalizeColumn(topic, hint) 사용
  - 단일 기업 질문에서 scan prebuild만 보고 Company.analysis 확인을 생략
  - 외화 매출 회사 (수출 비중 50%+) 의 환율 영향 미분리
  - table ref 는 만들었지만 material claim 을 해당 table/value ref 에 직접 묶지 않아 최종 검산 실패
forbidden:
  - 숫자 없는 수익성 판단 금지
  - 결손값을 0 으로 대체 금지 — 빈 분기는 skip 또는 flag 표시
  - 단일 종목 수익성 질문을 저평가·후보 발굴 screen 으로 바꿔 답하기 금지
  - ROE 분모를 평균자본/기말자본 미명시 답변 금지 — 정의 명시 필수
  - stale 기간 (3 분기 전) 데이터를 *현재* 로 단정 금지 — dataAsOf 명시
examples:
  - 삼성전자 수익성 분석
  - 영업이익률이 좋아졌는지 분기별 추세
  - 반도체 peer ROE 비교 (삼성전자 vs SK하이닉스)
  - 매출 증가 vs 이익률 정체 원인 분리
  - 분기별 마진 변화와 원자재 영향
  - 산업 평균 ROE 대비 위치
linkedSkills:
  - engines.scan.profitability
  - engines.analysis.growth
  - engines.analysis.cashflow
  - engines.analysis.macroSensitivity
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 단일 기업 수익성 질문은 Company 경로가 기본이다. 먼저 Company.analysis와 Company.show capability에서 수익성 관련 축과 원자료 topic을 찾는다.
- Company snapshot 또는 Company.analysis가 가능하면 그것을 1차 근거로 둔다. `dart.scan/finance-lite.parquet`는 횡단 비교·후보 발굴·Company 원자료 부재 시의 보조 근거로만 사용한다.
- 질문이 “수익성 분석”이면 저평가/후보 scan skill로 목적을 바꾸지 않는다. screen은 peer 위치나 후보 발굴이 명시될 때만 보조로 연결한다.
- finance-lite를 쓰는 경우 `stockCode`, 연결/별도, 손익계산서 구분, 기간 구분을 먼저 확인하고 매출·영업이익·순이익 계정 후보를 실제 계정명으로 좁힌다.
- Polars에서 wide table을 만들 때 lazy pivot을 가정하지 말고 collect 후 eager pivot을 사용한다. 현재 Polars는 pivot 축에 `on`을 쓰는 경로가 안전하다.
- 매출, 영업이익률, 순이익률, 현금성 보조 지표를 같은 기간 기준으로 만들고, 실행 결과는 숫자 metric이 검산 가능한 table/value ref가 되도록 남긴다.
- 최종 material claim은 기간·metric·값을 포함하되, 각 claim이 해당 table/value ref를 직접 참조하게 한다. evidence refs만 나열하고 claim refs를 비워 두면 숫자 검산을 통과하지 못한다.
- scan 또는 macro 맥락이 있으면 업황과 기업 수익성 변화를 연결한다.
- claim은 기간, metric, table 또는 value ref에 묶는다.

## 다중 종목 비교 (2~3 사) 의 권장 경로

"A vs B 영업이익률 비교" / "A · B · C 중 누가 마진 더 좋아" 류 질문은 **`CompareCompanies(stockCodes=["A","B","C"])` 1 회 호출이 정공**. 종목별 `Company.show` 를 N 회 호출하지 마라 (LLM 이 종목마다 별도 turn 으로 분리해 시퀀셜 → CompareCompanies 1 회 대비 2~3 배 느림). CompareCompanies 결과는 wide-format DataFrame + 종목별 `dcrBadge` · `industryBadge` 자동 부착이라 헤더에 양사 chip 동시 노출 가능.

추가 계산이 필요한 경우 (예: QoQ 변화 분리, peer 평균 차이) 만 결과 wide table 을 RunPython 으로 가공.

## OPM (영업이익률) 표준 정의 — 답변 양식

영업이익률 = `operating_profit / sales` (분기 기준). 명시할 것:

- 단위 통일: 표 한 컬럼 안 단위 (조원 · 억원 · %) 행마다 통일. `1.471 억` 과 `1 조 1,163 억` 같이 7,500 배 스케일 차이를 같은 컬럼에 섞지 마라 — 큰 단위 (조) 로 환산.
- 기간 명시: `2025Q4` 같은 quarter 라벨. 연환산/YTD/단일분기 혼용 금지.
- 연결/별도: `Company.show("IS").data.summary` 의 `consolidation` 또는 별도 명시 없으면 "전사 연결 기준" default.
- 환율 영향: 수출 비중 50% 이상 회사 (반도체·자동차·조선 등) 는 환율 시나리오 미반영 사실을 한계로 표기.

## ROE 표준 정의

ROE = `net_income / equity`. 분모는 **기말 자본 default** (가장 단순). 평균 자본 (기초+기말/2) 을 쓰면 그 사실을 답변에 명시. ROE 100% 같은 극단값은 자본금 잠식 / 자기주식 / 회계 기저 효과 의심 — 그대로 인용하지 말고 sanity 표시.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "수익성")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "수익성", company=c)
```

## 호출 동작

- Company 재무 snapshot과 표준 계정 매핑을 읽어 단일 기업의 재무 축을 계산한다. 인자 없이 호출하면 사용 가능한 axis/subaxis 가이드 DataFrame을 반환한다. 데이터가 없으면 값을 만들지 않고 None 또는 데이터 부재 메시지로 제한한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- 주로 DataFrame 또는 dict-like 결과를 반환한다. 핵심 컬럼/키는 period, metric/account, value, unit, basis, comment이며 금액 단위는 원/백만원, 비율은 % 또는 배수다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


