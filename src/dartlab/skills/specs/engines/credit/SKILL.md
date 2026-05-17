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
  - migration matrix
  - 등급 전이 행렬
  - PD ladder
  - 누적 부도확률
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
  - migration matrix (등급 전이 확률 — credit.migration.buildTransitionMatrix)
  - forward PD ladder (등급별 1y/3y/5y 누적 부도확률 — credit.migration.forwardPdLadder)
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

### 시간축 — 등급 이력 → 현재 dCR → 누적 PD

`credit.migration` 모듈이 등급 전이 행렬과 forward PD ladder 를 제공한다. 학술 기반 — CreditMetrics (J.P. Morgan, 1997) Cohort 접근, Basel III IRB 표준. 관측 등급 변경 → row-stochastic transition matrix → 행렬 거듭제곱 (M^h) → 등급별 h 년 누적 부도확률.

```python
from dartlab.credit.scoring.migration import buildTransitionMatrix, forwardPdLadder

matrix = buildTransitionMatrix()  # data/credit/transition.json 자동 로드
ladder = forwardPdLadder(horizons=(1, 3, 5))
# → DataFrame: rating · 1yPD · 3yPD · 5yPD (D 등급은 absorbing → PD = 1.0)
```

forecast precision = stable (observed transitions, 점예측 X). story 6 막에서 '등급 이력 회고 → 현재 dCR → n 년 누적 PD' 시간 narrative 결합.

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

### Company.show 응답에 dcrBadge 자동 부착 — 단일 종목 답변의 권장 경로

`Company.show(topic)` (또는 `EngineCall(apiRef="Company.show")`) 의 반환 `data` dict 에 `dcrBadge` 가 자동 부착된다 (Track G). `dcrBadge.axes` 는 **7 축 완전 형태** — 각 항목 `{name, weight, score}` 가 들어있다. 신용·약점 질문이 단일 종목 한정이면:

| 시나리오 | 권장 호출 | 비권장 |
| --- | --- | --- |
| "삼성전자 신용도 어때?" | `Company.show("IS")` 1 회 → `data.dcrBadge` 인용 | `EngineCall("credit")` 별도 호출 |
| "7 축 약점은?" | `Company.show("IS").data.dcrBadge.axes` 그대로 분해 | `EngineCall("credit", stockCode, axis)` 7 회 |
| 등급 transition / migration matrix | `credit.migration.buildTransitionMatrix()` (별도 모듈) | dcrBadge 만으로 X |
| 외부 신평 비교 / 표본 79 개사 검증 | 본 skill 의 `detail=True` 호출 | dcrBadge 만으로 X |

**회귀 가드** — 7 축 점수가 이미 `dcrBadge.axes` 에 있는데 `EngineCall("credit")` 재호출하면 axis 가이드 metadata (axis · label · description · group) 만 반환되어 "데이터 부족" 환각 (2026-05-17 OAuth P5 probe 재현). 약점 분해는 본문의 [기본 실행 순서](#기본-실행-순서) 가 정공.

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

**단일 종목 신용·약점 분석 (chat-native 권장 경로)** — `Company.show("IS")` 1 회 호출 후 `data.dcrBadge.axes` 의 7 축을 직접 분해. 약점 순위는 *가중위험기여 = weight × score* 로 정렬:

```text
재무신뢰성  10% × 25.00 → 기여 2.50  (1 순위)
채무상환   25% × 6.77  → 기여 1.69  (2 순위)
사업안정성  10% × 13.75 → 기여 1.38  (3 순위)
유동성     15% × 4.04  → 기여 0.61
자본구조   20% × 2.20  → 기여 0.44
현금흐름   15% × 0.00  → 기여 0.00
공시리스크   5% × N/A   → 평가 공백
```

각 축 안 세부 지표 (예: 채무상환 축의 EBITDA/이자비용 · Debt/EBITDA · FFO/총차입금) 는 `dcrBadge.axes[i].metrics` (detail 모드) 에 시계열. 단일 종목이면 본 경로로 충분 — 추가 `credit()` 호출 불필요.

**심층 / 외부 신평 비교 / migration 시계열** — 다음 경로 (별도 capability):

1. 종목코드 확정 (`dartlab.searchName("회사명")` 또는 사용자 입력).
2. `dartlab.credit("005930", detail=True)` 으로 7 축 상세 + 모든 지표 시계열 + narrative.
3. `analysis` 의 안정성·현금흐름 축과 교차 검증.
4. `credit.migration.buildTransitionMatrix()` + `forwardPdLadder(horizons=(1, 3, 5))` 로 등급 전이 행렬 + 1y/3y/5y 누적 PD.
5. 외부 신평 비교 시 시점·표본·정성 요소 차이를 답변에 명시.

## 기본 검증

스킬은 공개 실행 문서다. `dartlab.credit()` / `Company.credit()` 의 호출 시그니처·반환 키·7 축 가중치가 바뀌면 본 파일과 [engines.credit.creditRisk](/skills/engines.credit.creditRisk) 응용 skill 을 같은 변경에서 갱신한다.
