---
id: recipes.credit.distressCandidateScreen
title: dCR 등급 전월비 하락 + 퀀트 sentiment 동시 약세 종목
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KOSPI200 universe 안에서 (1) dCR 등급이 전월 대비 1 notch 이상 하락 (credit migration) + (2) quant sentiment z-score ≤ -1.5 (시장 신호 약세) 동시 발현 종목 발굴. 단일 신호는 false positive 많지만 cross-source 합의는 강함. credit ↔ quant ↔ scan 격리 메우는 조합. 트리거 — 'distress candidate', '신용 sentiment 약세', 'credit migration screen'.
whenToUse:
  - distress candidate
  - 신용 sentiment 약세
  - credit migration
  - dCR 하락 종목
linkedSkills:
  - engines.scan.profitability
  - engines.credit
  - engines.quant.sentiment
  - recipes.credit.creditQuantConsensus
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
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
    - scan
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
  description: flagged 그룹의 6m 미래수익률이 unflagged 보다 높으면 신호 inverted
  pythonCheck: |
    assert forward_6m_return(flagged) < forward_6m_return(unflagged)
expectedNovelty:
  - gradeDelta
  - sentimentZ
  - distressFlag
forbidden:
  - 단일 등급 하락 (1 notch) 으로 부도 임박 단정 금지.
  - sentiment z 음수 = 자동 매도 단정 금지 — credit migration 동반 필요.
failureModes:
  - 1 개월 dCR archive 가 매번 운영자 manual 실행 (자동 monthly snapshot 필요).
  - sentiment z 의 lookback (60m vs 36m) 차이.
examples:
  - KOSPI200 distress candidate
  - dCR 하락 + sentiment 약세
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. KOSPI200 base universe
base = dartlab.scan("profitability", market="KR")
if isinstance(base, pl.DataFrame):
    universe = base
elif isinstance(base, list):
    universe = pl.DataFrame(base)
else:
    universe = pl.DataFrame()

# 2. 종목별 dCR + sentiment 평가 (1 차 wave: 단일 시점 — 등급 delta 는 archive 의존이라 placeholder)
results = []
for stock_code in universe["stockCode"].to_list()[:50] if "stockCode" in universe.columns else []:
    try:
        c = dartlab.Company(stock_code)
        credit = c.credit()
        grade = credit.get("grade") if isinstance(credit, dict) else None
        # grade_delta 는 archive 의존 — 1 차 wave 에선 BB- 이하면 distress 표시.
        distress_grade = grade in ("BB-", "B+", "B", "B-", "CCC", "CC", "C", "D")

        sentiment = c.quant("sentiment")
        sent_z = sentiment.get("zScore", 0) if isinstance(sentiment, dict) else 0
        weak_sentiment = sent_z <= -1.5

        flag = distress_grade and weak_sentiment
        if flag:
            results.append({
                "stockCode": stock_code,
                "dcrGrade": grade,
                "distressGrade": distress_grade,
                "sentimentZ": round(sent_z, 2),
                "weakSentiment": weak_sentiment,
                "distressFlag": flag,
            })
    except Exception:
        continue

emit_result(
    table=results,
    values={"flaggedCount": len(results)},
    date="2024-12-31",
)
```

## 호출 동작

1. `dartlab.scan("profitability", market="KR")` — KOSPI universe.
2. 종목별 `c.credit()` — dCR 등급. BB- 이하면 distress.
3. `c.quant("sentiment")` — z-score ≤ -1.5 약세.
4. 양쪽 동시 적신호 종목만 결과.

## 대표 반환 형태

`pl.DataFrame` — 컬럼 (flagged 종목만):
- `stockCode : str`
- `dcrGrade : str` · `distressGrade : bool`
- `sentimentZ : float` · `weakSentiment : bool`
- `distressFlag : bool`

## 연계 절차

1. 본 recipe → 동시 적신호 종목 목록.
2. 각 종목 → `recipes.credit.creditQuantConsensus` 4-source 합의 추가 검증.
3. shocked stress → `recipes.credit.creditMacroStress` 매크로 충격 추가 영향.
4. 자동 alert → 운영자 review (chat-native 흐름, status 자동 변경 X).
