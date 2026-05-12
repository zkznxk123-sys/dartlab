---
id: recipes.credit.creditQuantConsensus
title: 신용 dCR × 퀀트 부도 모델 3-source 합의 위험 종목
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 단일 회사 부도 위험을 dCR (정성·정량 종합) + Altman Z″ + Ohlson O + Beneish M 4-source 동시 평가. 단일 모델 false positive 줄이고 triple-agreement 시 강한 위험 신호. credit ↔ quant 격리 메우는 조합. 트리거 — '신용 퀀트 합의', '부도 4 모델', 'distress consensus'.
whenToUse:
  - 신용 퀀트 합의
  - 부도 4 모델
  - 다중 모델 부도
  - quant credit 합의
linkedSkills:
  - engines.company
  - engines.credit
  - recipes.credit.creditDistressDual
  - engines.quant.altman
  - engines.quant.beneish
  - engines.quant.piotroski
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
gap:
  primary:
    - credit
    - quant
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
  description: TripleAgreement 그룹의 24 개월 default 율이 Safe 그룹보다 낮으면 모델 inverted
  pythonCheck: |
    assert default_rate(triple_agreement) > default_rate(safe)
expectedNovelty:
  - consensusLabel
  - sourceAgreementCount
forbidden:
  - 4 모델 중 1 개 신호로 부도 임박 단정 금지.
  - 1968/1980 미국 표본 thresholds 를 KR 시장에 그대로 적용 금지.
  - 금융업 (은행·보험) 에 본 recipe 적용 금지 — 모델 대상 외.
failureModes:
  - dCR 등급과 quant model 의 시간 frequency 차이 (분기 vs 연간).
  - Beneish M 의 원자재기업 false positive (정상 inventory 변동을 분식 신호로 오인).
examples:
  - 삼성전자 4 모델 부도 합의
  - HMM dCR + Altman + Ohlson + Beneish 일치
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import math

c = dartlab.Company("005930")

# 1. dCR 등급 + 7 axis (정성 + 정량 종합)
credit = c.credit(detail=True)
dcr_grade = credit["grade"]
dcr_distress = dcr_grade in ("CCC", "CC", "C", "D", "BB-")

# 2. Altman Z″ (비제조업 변형) — recipes.credit.creditDistressDual 본문 참조
bs = c.show("BS", freq="Y")
is_df = c.show("IS", freq="Y")

def fetch(df, snake, year="2024"):
    row = df.filter(pl.col("snakeId") == snake).select(year)
    return float(row.to_numpy()[0][0]) if row.height > 0 else 0.0

ca = fetch(bs, "current_assets")
cl = fetch(bs, "current_liabilities")
ta = fetch(bs, "total_assets")
re = fetch(bs, "retained_earnings")
liab = fetch(bs, "total_liabilities")
equity = fetch(bs, "total_stockholders_equity")
ebit = fetch(is_df, "operating_profit")
ni = fetch(is_df, "net_income")

z_score = (
    6.56 * ((ca - cl) / ta if ta else 0)
    + 3.26 * (re / ta if ta else 0)
    + 6.72 * (ebit / ta if ta else 0)
    + 1.05 * (equity / liab if liab else 0)
)
altman_distress = z_score < 1.10

# 3. Ohlson O (1980 logit 휴리스틱)
size = math.log(ta) if ta > 0 else 0
tlta = liab / ta if ta else 0
nita = ni / ta if ta else 0
ohlson_o = -1.32 - 0.407 * size + 6.03 * tlta - 2.37 * nita
ohlson_prob = 1 / (1 + math.exp(-ohlson_o)) if ohlson_o > -50 else 0
ohlson_flag = ohlson_prob > 0.5

# 4. Beneish M-Score 휴리스틱 (간이 — 5 변수)
ar = fetch(bs, "trade_receivables")
sales = fetch(is_df, "revenue")
ar_prev = fetch(bs, "trade_receivables", "2023")
sales_prev = fetch(is_df, "revenue", "2023")

dsri = (ar / sales) / (ar_prev / sales_prev) if sales and sales_prev and ar_prev else 1
gmi = 1.0  # 간이 — 본 wave 에서는 placeholder.
m_score = -4.84 + 0.92 * dsri + 0.528 * gmi
beneish_flag = m_score > -1.78

# 5. 합의 — 4 source 중 몇 개 동시 적신호?
sources_flagged = sum([dcr_distress, altman_distress, ohlson_flag, beneish_flag])
if sources_flagged >= 3:
    consensus = "TripleAgreement"
elif sources_flagged == 2:
    consensus = "DualAgreement"
elif sources_flagged == 1:
    consensus = "SingleAgreement"
else:
    consensus = "Safe"

emit_result(
    table=[{
        "stockCode": "005930",
        "year": "2024",
        "dcrGrade": dcr_grade,
        "dcrDistress": dcr_distress,
        "altmanZ": round(z_score, 2),
        "altmanDistress": altman_distress,
        "ohlsonProb": round(ohlson_prob, 3),
        "ohlsonFlag": ohlson_flag,
        "beneishM": round(m_score, 2),
        "beneishFlag": beneish_flag,
        "sourcesFlagged": sources_flagged,
        "consensus": consensus,
    }],
    values={"consensus": consensus, "sourcesFlagged": sources_flagged},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.credit(detail=True)` — dCR 등급 + 7 axis. BB- 이하 distress 표시.
2. `c.show("BS"|"IS", freq="Y")` 로 raw → Altman Z″ 직접 계산.
3. 동일 raw → Ohlson O logit + 부도 확률.
4. AR / Sales 비율 변화 → Beneish M-Score 분식 신호.
5. 4 source 합의 — 3 개 이상 = TripleAgreement.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `dcrGrade : str` · `dcrDistress : bool`
- `altmanZ : float` · `altmanDistress : bool`
- `ohlsonProb : float` · `ohlsonFlag : bool`
- `beneishM : float` · `beneishFlag : bool`
- `sourcesFlagged : int` (0~4)
- `consensus : str` — Safe / SingleAgreement / DualAgreement / TripleAgreement

## 연계 절차

1. 본 recipe → 4 source 합의 결과.
2. consensus = TripleAgreement → `recipes.credit.creditMacroStress` 와 결합 — 매크로 충격 시 추가 악화 위험.
3. consensus = DualAgreement → `engines.analysis.earningsQuality` 로 분식 의심 별도 검증.
4. universe 적용은 `recipes.credit.distressCandidateScreen` 와 결합.
