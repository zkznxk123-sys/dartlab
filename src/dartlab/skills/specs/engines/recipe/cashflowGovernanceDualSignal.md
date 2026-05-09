---
id: engines.recipe.cashflowGovernanceDualSignal
title: 현금흐름 품질 × 거버넌스 감사 동시 적신호
category: engines
kind: recipe
scope: builtin
status: drafted
purpose: accrual ratio (현금흐름 vs 회계이익 갭) + governance amber (이사회 독립성 / 특수관계자) + audit-change (감사인 변경) 3 신호 동시 발현 시 분식 / 회계 신뢰도 적신호. Dechow et al (2011) "Predicting Material Accounting Misstatements" 학술 결과 적용. analysis ↔ scan 격리 메우는 조합. 트리거 — '분식 의심', '회계 신뢰도', 'accrual governance audit'.
whenToUse:
  - 분식 의심 종목
  - 회계 신뢰도 적신호
  - accrual governance
  - 감사 리스크
linkedSkills:
  - engines.company
  - engines.analysis.earningsQuality
  - engines.analysis.governance
  - engines.scan.audit
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
    - analysis
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
  description: triple flag 종목의 3y 재무재작성 (restatement) 률이 unflagged 보다 낮으면 모델 inverted
  pythonCheck: |
    assert restatement_rate(triple_flagged) > restatement_rate(unflagged)
expectedNovelty:
  - tripleFlag
  - accrualPercentile
forbidden:
  - 단일 신호 (accrual 만) 로 분식 단정 금지.
  - 감사인 변경 = 분식 단정 금지 — 정상 rotation 도 있음.
failureModes:
  - accrual ratio 가 산업 평균 (제조업 vs 서비스) 차이 무시.
  - governance amber 정의가 회사 size / industry 별 thresholds 다름.
examples:
  - 삼성전자 accrual + governance + audit triple
  - HMM 회계 신뢰도 적신호
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

# 1. earnings quality — accrual ratio 계산
eq = c.analysis("earningsQuality", "수익품질")
accrual_ratio = eq.get("accrualRatio") if isinstance(eq, dict) else 0
fcf_ni_ratio = eq.get("fcfToNi") if isinstance(eq, dict) else 1
high_accrual = accrual_ratio > 0.05  # 75th percentile heuristic

# 2. governance — 이사회 독립성 / 특수관계자 비중
gov = c.analysis("governance", "거버넌스")
board_independence = gov.get("boardIndependence", 0.5) if isinstance(gov, dict) else 0.5
related_party = gov.get("relatedPartyRatio", 0) if isinstance(gov, dict) else 0
gov_amber = board_independence < 0.4 or related_party > 0.2

# 3. audit-change in last 2y
audit_scan = c.scan("audit") if hasattr(c, "scan") else None
audit_changed = audit_scan.get("auditorChangedRecently", False) if isinstance(audit_scan, dict) else False

# 4. triple flag
flags = [high_accrual, gov_amber, audit_changed]
triple_flag = all(flags)
flag_count = sum(flags)

emit_result(
    table=[{
        "stockCode": "005930",
        "accrualRatio": round(accrual_ratio, 4),
        "highAccrual": high_accrual,
        "fcfNiRatio": round(fcf_ni_ratio, 2),
        "boardIndependence": round(board_independence, 2),
        "relatedPartyRatio": round(related_party, 2),
        "govAmber": gov_amber,
        "auditChanged": audit_changed,
        "flagCount": flag_count,
        "tripleFlag": triple_flag,
    }],
    values={"flagCount": flag_count, "tripleFlag": triple_flag},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.analysis("earningsQuality")` — accrual ratio + FCF/NI 비율.
2. `c.analysis("governance")` — 이사회 독립성 + 특수관계자 비중.
3. `c.scan("audit")` — 최근 2 년 감사인 변경 여부.
4. 3 신호 boolean 결합 → triple flag.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `accrualRatio : float` · `highAccrual : bool`
- `fcfNiRatio : float`
- `boardIndependence : float` · `relatedPartyRatio : float` · `govAmber : bool`
- `auditChanged : bool`
- `flagCount : int (0~3)` · `tripleFlag : bool`

## 연계 절차

1. 본 recipe → triple flag 종목 식별.
2. tripleFlag = True → `engines.recipe.creditQuantConsensus` 와 결합 — Beneish M-score 분식 신호와 교차 검증.
3. universe 적용 → `engines.recipe.governanceAuditNetwork` 로 cross-sectional flag.
