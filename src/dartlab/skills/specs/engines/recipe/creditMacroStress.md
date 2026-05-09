---
id: engines.recipe.creditMacroStress
title: 신용×매크로 스트레스 — 금리 +200bp 충격 시 dCR 등급 유지 가능성
category: engines
kind: recipe
scope: builtin
status: drafted
purpose: 단일 회사의 신용등급 (dCR + 7 axis) 가 매크로 충격 (금리 +200bp / 환율 +10% / 영업이익 -20%) 에서 유지 가능한지, 어떤 axis 가 먼저 깨지는지 판정. credit ↔ macro 격리 메우는 조합 — 정상 보고 dCR 은 시점 1 회 산출이라 미래 시나리오에서 어떻게 변하는지 보여주지 못한다. 트리거 — '신용 매크로 스트레스', '금리 충격 dCR', 'credit stress'.
whenToUse:
  - 신용 매크로 스트레스
  - 금리 충격 dCR
  - 매크로 시나리오 신용
  - 차입 금리 stress
  - 부도 위험 매크로
linkedSkills:
  - engines.company
  - engines.credit
  - engines.macro
  - engines.analysis.macroSensitivity
  - engines.analysis.financing
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - 매크로 시계열 일부 한정
gap:
  primary:
    - credit
    - macro
  secondary:
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: shocked dCR == base dCR for ≥ 90% of KOSPI200 → recipe 노이즈
  pythonCheck: |
    assert not all(shocked_grade == base_grade for shocked_grade, base_grade in zip(shocked_list, base_list))
expectedNovelty:
  - shockedGrade
  - bindingAxis
  - axisDelta
forbidden:
  - 단일 시나리오 (200bp) 결과만 절대 단정 금지 — 100/200/300 다중 강도 비교.
  - macro 환경 변수 (금리만) 1 차원 충격 단정 금지 — 환율·영업이익 함께 흔들기.
  - 1 분기 충격으로 dCR 영구 하락 단정 금지 — 회복 경로 (지속 vs 일시) 구분.
failureModes:
  - 금리 sensitivity 가 회사 specifics (변동/고정 비율) 무시한 단순 평균.
  - dCR 7 axis 중 어느 axis 가 binding 인지 분석 없이 등급만 보고.
  - macroSensitivity elasticity 가 회사별 추정 신뢰도 차이.
examples:
  - 삼성전자 금리 +200bp 충격에서 dCR 유지?
  - 현대차 환율 +10% 시 신용 axis 어디 깨지나
  - HMM 영업이익 -20% 시 dCR 등급 변동
lastUpdated: '2026-05-10'
---

## 학술 근거

### Stress Testing 기본
- **CCAR (Comprehensive Capital Analysis and Review)** — 미연방 은행 감독 매크로 시나리오 기반 자본 충분성 평가. 본 recipe 는 단일 비금융기업 적용 변형.
- **EBA Stress Test** — 유럽은행감독청. baseline + adverse 두 path 비교 + 자본비율 시계열.
- **Standard & Poor's Macro Sensitivity** — 신용등급 회사 cycle 위치 + 매크로 베타 종합.

### 적용 한계
- 비금융기업 stress test 는 학계·실무 통합 표준 없음. 본 recipe 는 dCR 7 axis 별 elasticity → shocked metric → 등급 재계산 휴리스틱.
- 금리 충격 → 이자비용 ↑ → 영업이익 ↓ → 채무상환 axis 약화 + 현금흐름 axis 약화 → dCR 등급 ↓.
- 환율 충격 → 원자재·수출비중 별 EBIT 변동 → 사업안정성 axis + 채무상환 axis 동시 영향.

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

# 1. 기본 dCR + 7 axis subscores
base_credit = c.credit(detail=True)
base_grade = base_credit["grade"]
base_axes = base_credit["axes"]

# 2. 매크로 sensitivity (금리 / 환율 / 영업이익 elasticity)
sensitivity = c.analysis("macro", "매크로민감도")

# 3. 금리 +200bp 충격 시 EBIT / Interest / Coverage 재계산
is_df = c.show("IS", freq="Y")
bs_df = c.show("BS", freq="Y")

def fetch(df, snake, year):
    row = df.filter(pl.col("snakeId") == snake).select(year)
    return float(row.to_numpy()[0][0]) if row.height > 0 else 0.0

ebit = fetch(is_df, "operating_profit", "2024")
interest_expense = fetch(is_df, "interest_expense", "2024")
borrowings = fetch(bs_df, "total_borrowings", "2024")
total_assets = fetch(bs_df, "total_assets", "2024")
total_liabilities = fetch(bs_df, "total_liabilities", "2024")
equity = fetch(bs_df, "total_stockholders_equity", "2024")

rate_shock_bp = 200
shocked_interest = interest_expense + (borrowings * rate_shock_bp / 10000)
shocked_ebit = ebit  # 1 차 wave: operating margin 직접 충격은 별도 시나리오에서.

base_icr = ebit / interest_expense if interest_expense else 0
shocked_icr = shocked_ebit / shocked_interest if shocked_interest else 0
icr_delta = shocked_icr - base_icr

# 4. 7 axis 중 채무상환 (icr 의존) + 현금흐름 (CFO 의존) axis 점수 재계산 — 단순 휴리스틱:
#    icr 50% 이상 하락 시 채무상환 axis 1 notch ↓.
shocked_axes = dict(base_axes)
binding_axis = None
if base_icr and shocked_icr / base_icr < 0.5:
    binding_axis = "채무상환"
    if isinstance(shocked_axes.get("채무상환"), dict):
        shocked_axes["채무상환"]["score"] = max(0, shocked_axes["채무상환"].get("score", 50) - 15)

# 5. shocked dCR 등급 — 7 axis 가중 평균 → 등급 mapping (간이).
def gradeOf(score):
    if score >= 85: return "AA"
    if score >= 75: return "A"
    if score >= 65: return "BBB"
    if score >= 55: return "BB"
    if score >= 45: return "B"
    return "CCC"

base_score = sum(a.get("score", 0) for a in base_axes.values() if isinstance(a, dict)) / max(1, len(base_axes))
shocked_score = sum(a.get("score", 0) for a in shocked_axes.values() if isinstance(a, dict)) / max(1, len(shocked_axes))
shocked_grade = gradeOf(shocked_score)

# 6. emit_result — table + values + date.
emit_result(
    table=[{
        "year": "2024",
        "rateShockBp": rate_shock_bp,
        "baseGrade": base_grade,
        "shockedGrade": shocked_grade,
        "baseICR": round(base_icr, 2),
        "shockedICR": round(shocked_icr, 2),
        "icrDelta": round(icr_delta, 2),
        "bindingAxis": binding_axis or "(none)",
    }],
    values={"baseGrade": base_grade, "shockedGrade": shocked_grade, "icrDelta": icr_delta},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.credit(detail=True)` — 현재 시점 dCR + 7 axis subscores.
2. `c.analysis("macro", "매크로민감도")` — 금리 / 환율 elasticity.
3. `c.show("IS"|"BS", freq="Y")` — EBIT / interest / borrowings 추출.
4. 금리 +200bp × 차입금 → shocked interest expense 계산.
5. shocked ICR (Interest Coverage Ratio) = EBIT / shocked interest.
6. ICR 가 base 대비 50% 이상 하락하면 채무상환 axis -15 점 (간이 매핑).
7. 7 axis 가중 평균 → 등급 재계산.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `year : str`
- `rateShockBp : int` — 충격 강도 (default 200bp)
- `baseGrade : str` — 기본 dCR 등급
- `shockedGrade : str` — 충격 후 등급
- `baseICR : float` — 기본 Interest Coverage Ratio
- `shockedICR : float` — 충격 후 ICR
- `icrDelta : float` — ICR 변동
- `bindingAxis : str` — 가장 먼저 깨지는 axis 이름 (없으면 "(none)")

## 한계

- **휴리스틱 등급 mapping** — 본 recipe 의 score → 등급 변환은 간이. 실 dCR 알고리즘은 axis 가중 + 산업·규모 조정 더 복잡.
- **단일 시나리오 (200bp)** — 100/200/300 강도별 sensitivity curve 가 운영 가치. 본 recipe 는 단일 충격 prototype.
- **rate sensitivity** — 차입금 전체에 같은 충격 가정. 실제는 변동/고정 비율 + 만기 분포 별 영향 차등.
- **EBIT 일정 가정** — 실제 금리 ↑ 시 매출 / 마진 동시 압박. EBIT 변동 추가 시나리오 필요.

## 한국 / 미국 시장 차이

- **한국**: chaebol 그룹 보증 / 자금 지원 변수 — 단일 회사 ICR 만으로 신용 단정 위험. 그룹 차원 stress 별도.
- **미국**: 회사채 시장 발달 → 금리 충격 즉시 회사채 spread 반영. ICR 보다 spread-based stress 가 더 빠른 신호.

## 연계 절차

1. 본 recipe → shockedGrade + bindingAxis 산출.
2. shockedGrade 가 BB 이하로 떨어지면 `engines.recipe.creditCovenantStressTest` 와 결합 — 차입약정 위반 가능성 함께 점검.
3. bindingAxis = 채무상환 → `engines.analysis.financing` 으로 차입 만기 schedule + 변동/고정 비율 상세.
4. bindingAxis = 사업안정성 → `engines.recipe.creditQuantConsensus` 와 결합 — Altman / Beneish / Piotroski 합의 부도 신호 동반 검증.
5. 5 종목 실행 후 `engines.recipe.distressCandidateScreen` 으로 universe 확장.

## 기본 검증

- 5 시나리오 강도 (100/200/300/400/500bp) sensitivity curve 그려 — 등급 변동이 단조 (monotonic) 여야 정상.
- shockedGrade 가 baseGrade 와 항상 동일하면 sensitivity 가 작동하지 않음 — recipe 거짓 OK.
- shockedGrade 가 거의 모든 종목 6 등급 이상 폭락하면 mapping 휴리스틱 과민.
- 외부 신용평가 (KIS / NICE / S&P) 의 actual 매크로 stress 결과와 본 recipe 의 shockedGrade 추세 일치도 ≥ 60%.
