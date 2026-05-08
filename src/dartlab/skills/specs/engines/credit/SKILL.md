---
id: engines.credit
title: Credit (dCR)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Credit (dCR) 엔진은 단일 기업의 신용 위험을 7 축 (채무상환·자본구조·유동성·현금흐름·사업안정성·재무신뢰성·공시리스크) 으로 평가해 종합 등급 (dCR-AA+ ~ dCR-D) 을 산출한다. 트리거 — '신용 분석', '부도 위험', '신용등급', 'dCR'.
whenToUse:
  - Credit
  - credit
  - dCR
  - 신용등급
  - 신용 분석
  - 부도 위험
  - 부실 위험
  - 채무상환
  - 자본구조
  - 이자보상배율
  - 부채비율
  - 외부 신평 비교
inputs:
  - stockCode 또는 Company
  - axis (7 축 중 하나 또는 미지정)
  - basePeriod
  - detail
outputs:
  - 종합 등급 dict (grade · score · axes · outlook)
  - 축별 dict (axis · score · weight · metrics)
  - 가이드 DataFrame (axis 미지정 + stockCode 미지정)
  - tableRef · valueRef · dateRef · executionRef
capabilityRefs:
  - credit
  - Company.credit
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.analysis
sourceRefs:
  - dartlab://skills/engines.credit
requiredEvidence:
  - target
  - period
  - metric
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - 종합 등급 (grade · score)
  - 7 축 점수
  - 핵심 지표 (debtRatio · interestCoverage · OCF/부채)
  - 외부 신평 비교 한계
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
  - 외부 신평 (Moody's·KIS·NICE) 과 1:1 비교로 단정
  - 시스템적 중요성·정성 요소를 dCR 단독으로 판단
  - basePeriod 명시 없이 등급을 *현재* 로 단정
  - 7 축 점수만 보고 종합 등급 추정 (가중치·notch 보정 무시)
forbidden:
  - 외부 공식 신용평가를 대체한다고 주장하지 않는다.
  - basePeriod·source 없이 등급 숫자를 답한다.
  - analysis 엔진을 직접 import 해서 결합한다 (필요 시 Company / core 에서 직접 데이터 로드).
  - 공개 API 호출 방식·반환 형태가 바뀌었는데 본 skill 갱신 없이 완료 처리한다.
examples:
  - 삼성전자 신용 등급 산출
  - SK하이닉스 7 축 분석
  - 채무상환 축 단독 점수
  - 외부 신평 등급과 dCR 비교 (표본 79 개사)
  - 종합 등급 + 전망 (outlook)
  - detail=True 로 모든 지표 시계열 + narrative
procedure:
  - 종목코드 또는 Company 인스턴스 확보 (`dartlab.Company("005930")` 또는 직접).
  - 종합 등급은 `dartlab.credit("005930")` 또는 `c.credit()`. 가이드만이면 인자 없이.
  - 축 단독은 `dartlab.credit("005930", "채무상환")` 또는 `c.credit("자본구조")`.
  - 결과의 `grade` · `score` · `axes` · `outlook` · `metrics` 검증 후 답변에 묶음.
  - 외부 신평과 비교 시 표본 한계·정성 요소·시점 차이를 함께 명시.
linkedSkills:
  - engines.credit.creditRisk
  - engines.company
  - engines.analysis
  - engines.story
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
---

## 엔진 역할

`credit` 은 단일 기업의 부도 위험·재무 건전성을 독립 평가하는 L2 엔진이다. 79 개사 검증 (대기업 87% · 중대형 82%) 의 dCR 등급 (dCR-AA+ ~ dCR-D) 을 DART 공시 기반으로 산출한다. 외부 신평사 (Moody's · KIS · NICE) 가 반영하는 시스템적 중요성·정성 요소는 dCR 만으로 판단하지 않는다.

`analysis` 엔진의 안정성·현금흐름 축과 상호 보완. credit 종합 등급 → analysis 로 인과 깊게, 또는 analysis 안정성 점수 → credit 으로 외부 신평 보정 비교.

## 공개 호출 방식

```python
import dartlab

# 1. 가이드 (7 축 목록)
guide = dartlab.credit()

# 2. 종합 등급 (axis 미지정)
verdict = dartlab.credit("005930")
# → {"grade": "dCR-AA+", "score": 12.4, "axes": [...], "outlook": "안정적"}

# 3. 축 단독 (7 축 중 하나)
repayment = dartlab.credit("005930", "채무상환")
leverage = dartlab.credit("005930", "자본구조")
# 영문 alias 도 지원: dartlab.credit("005930", "repayment")

# 4. 상세 모드 — 모든 지표 시계열 + narrative
detailed = dartlab.credit("005930", detail=True)

# 5. Company 바인딩
c = dartlab.Company("005930")
verdict = c.credit()
repayment = c.credit("채무상환")
```

## 호출 동작

`stockCode` 미지정 → 7 축 가이드 DataFrame (axis · label · description · example · group).

`stockCode` 만 지정 → 종합 등급 dict — 3-Track 모델 (일반·금융·지주) + Notch Adjustment + CHS 시장 보정 적용. `grade` (dCR 등급), `score` (위험 점수 0~100), `healthScore` (100-score), `axes` (7 축 list), `outlook` (안정적·긍정적·부정적).

`stockCode` + `axis` → 해당 축 dict — `axis` (축 풀네임), `score` (해당 축 위험 점수), `weight` (가중치 %), `metrics` (개별 지표 name·value·score).

`detail=True` → 7 축 상세 + 모든 지표 시계열 (YoY · 5 년 평균) + `narrative` (한국어 인과 문장, story 블록 재료).

데이터 부족 (재무 결손·신생 상장·연결재무제표 부재) 시 결손을 0 으로 채우지 않고 `riskFlags` 와 제한 메시지로 표현.

## 7 축 목록

| axis | label | weight | 핵심 지표 |
| --- | --- | --- | --- |
| 채무상환 | 이자보상·DSCR | 25% | interestCoverage · DSCR · OCF/Debt |
| 자본구조 | 부채비율·차입금/자본 | 20% | debtRatio · debtToEquity · netDebt/EBITDA |
| 유동성 | 단기 지급능력 | 15% | currentRatio · quickRatio · cashRatio |
| 현금흐름 | OCF 안정성 | 15% | ocfMargin · ocfYoY · fcfPositive |
| 사업안정성 | 매출/이익 변동성 | 10% | revenueCV · operatingMarginCV |
| 재무신뢰성 | 회계 보수성·이상치 | 10% | accrualRatio · auditOpinion |
| 공시리스크 | 공시 변화 선행 신호 | 5% | disclosureChangeScore |

영문 alias: `repayment` · `leverage` · `liquidity` · `cashflow` · `businessStability` · `financialReliability` · `disclosureRisk`.

## 대표 반환 형태

```text
dartlab.credit("005930")
→ dict
   grade : str           # "dCR-AA+" 등 dCR 등급
   score : float         # 0=최우량 ~ 100=최위험 (점)
   healthScore : float   # 100 - score (점)
   axes : list[dict]     # 7 축 상세 (name · score · weight · metrics)
   eCR : str | None      # 현금흐름등급 (별도 산출)
   outlook : str         # "안정적" / "긍정적" / "부정적"
```

```text
dartlab.credit("005930", "채무상환")
→ dict
   axis : str            # "채무상환"
   score : float         # 해당 축 위험 점수 (점)
   weight : int          # 가중치 (% — 7 축 합 100)
   metrics : list[dict]  # name · value · score · unit
```

`detail=True` 시 추가 키:
- `metrics[].history` — 시계열 (YoY · 5 년 평균)
- `narrative` — 한국어 인과 문장 (story 조립용)

## evidence 기준

신용 답변은 `target` (종목코드) · `basePeriod` · 7 축 score · 핵심 지표 valueRef · `dataAsOf` 를 남긴다. 외부 신평과 비교 시 비교 시점 dateRef + 표본 79 개사 한계를 함께 명시.

## 기본 실행 순서

1. 종목코드 확정 (`dartlab.searchName("회사명")` 또는 사용자 입력).
2. `dartlab.credit("005930")` 으로 종합 등급 확인.
3. score 가 50+ 이면 weak 축 식별 → 해당 축 단독 호출 (`dartlab.credit("005930", "채무상환")`).
4. `analysis` 의 안정성·현금흐름 축과 교차 검증.
5. 외부 신평 비교 시 시점·표본·정성 요소 차이를 답변에 명시.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.credit()` / `Company.credit()` 의 호출 시그니처·반환 키·7 축 가중치가 바뀌면 본 파일과 [engines.credit.creditRisk](/skills/engines.credit.creditRisk) 응용 skill 을 같은 변경에서 갱신한다.
