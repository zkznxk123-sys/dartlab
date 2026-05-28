---
id: engines.company.flow
title: Company KRX Flow (외국인/기관/개인)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Company.flow — KRX 외국인/기관/개인 종목별 일별 net-buy. 한국 unique disclosure (US 시장은 종목별 net-buy 공개 X). Company.gather("flow") wrapper. KOSPI/KOSDAQ 외국인 수급의 가장 중요한 daily signal.
whenToUse:
  - 외국인 net-buy
  - 외국인 매수세
  - 외국인 매도
  - 기관 net-buy
  - 기관 매수
  - 개인 매수
  - 일별 수급
  - foreign netbuy
  - institution netbuy
  - flow
  - 수급 추세
  - 외국인 보유
  - 한도소진율
  - KRX flow
inputs:
  - 종목코드 (KR 한정)
outputs:
  - pl.DataFrame (date · foreignNet · institutionNet · individualNet)
capabilityRefs:
  - Company.flow
  - Company.gather
knowledgeRefs:
  - engines.company
  - engines.company.koreanDisclosure
  - engines.gather
sourceRefs:
  - dartlab://skills/engines.company.flow
requiredEvidence:
  - target
  - date
  - tableRef
  - sourceRef
expectedOutputs:
  - 일별 외국인/기관/개인 net-buy DataFrame
  - 누적 추세 (cumsum)
  - 외국인 매수/매도 패턴 + 기관 동조/역행 context
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
failureModes:
  - 일별 raw flow 전체 dump (답변 본문 — 최근 5~30 일 + 누적 비중만)
  - 외국인 net-buy 단독 신호 해석 (기관 동조/역행 context 동반 필수)
  - KR 외 시장 (US · JP) target 에 호출 (빈 결과 정상 — 시장 제한 명시)
  - 단순 수급 일별 답변 + 종목 펀더멘털 무관계 가정
forbidden:
  - tableRef 또는 sourceRef 없이 수급 수치 인용 금지
  - 일별 raw 데이터 전체 dump 금지 (답변 본문 상위 5~30 일 + 누적만)
examples:
  - 삼성전자 외국인 매수세 - Company.flow
  - 005930 기관 vs 외국인 추세 - Company.flow + 두 컬럼 비교
  - 외국인 순매수 누적 - Company.flow + foreignNet cumsum
  - 최근 30 일 외국인 net-buy - Company.flow + date head 30
  - 외국인 매수 + 기관 매도 분리 신호 - Company.flow + foreignNet vs institutionNet 부호
  - SK하이닉스 일별 수급 - Company.flow + 일별 raw
procedure:
  - 종목코드 - Company 객체 생성 (KR 한정)
  - c.flow() 호출 - Naver flow API 자동
  - 일별 외국인/기관/개인 net-buy DataFrame 확인
  - 누적 추세 (cumsum) 계산
  - 외국인 매수/매도 + 기관 동조/역행 context 동반 분석
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 일별 외국인/기관/개인 net-buy
flow = c.flow()
if not flow.is_empty():
    print(flow.head(30))            # 최근 30 일
    # 누적
    import polars as pl
    cumulative = flow.with_columns([
        pl.col("foreignNet").cum_sum().alias("foreignCum"),
        pl.col("institutionNet").cum_sum().alias("institutionCum"),
    ])
```

## 호출 동작

- target = DART 종목코드 (KOSPI/KOSDAQ). KR 한정 — 외 시장 target 은 빈 DataFrame.
- Company.gather("flow") delegate — 본체 = gather("flow", ...) handler (handleFlow).
- Naver flow API 자동 호출 — daily reshape 후 pl.DataFrame 반환.
- 빈 결과 (KR 외 시장 · 신생 종목 · Naver API 부재) → 빈 DataFrame.
- 일별 EOD (T+1) freshness.

## 대표 반환 형태

```
pl.DataFrame:
  date : Date
  foreignNet : Int64        # 외국인 일별 순매수 (원)
  institutionNet : Int64    # 기관 일별 순매수 (원)
  individualNet : Int64     # 개인 일별 순매수 (원)
  (또는 시장 변경 시 추가 컬럼)
```

## 기본 검증

- 모든 수급 수치 claim 은 tableRef 또는 dateRef 의 sourceRef 에 묶는다.
- 일별 raw flow 전체 dump 금지 — 답변 본문 최근 5~30 일 + 누적 cumsum 또는 비중만 인용.
- 외국인 net-buy 단독 답변 금지 — 기관 동조/역행 context 동반 (둘 다 매수 = 강한 신호 · 외국인 매수+기관 매도 = 분리).
- KR 외 시장 target 호출 시 빈 결과 — 답변 본문에서 "시장 제한 (KR 한정)" 명시.
- 종목 펀더멘털 (실적 · 공시) context 없이 수급만 보고 매매 결론 금지.
- Company.flow() docstring 변경 시 본 skill 의 capabilityRefs · examples · 반환 형태 동기화.
