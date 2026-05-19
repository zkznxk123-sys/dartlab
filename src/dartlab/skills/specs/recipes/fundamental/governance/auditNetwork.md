---
id: recipes.fundamental.governance.auditNetwork
title: 거버넌스 + 계열사밀도 + 감사변경 triple flag (KR chaebol risk)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KOSPI universe 안에서 (1) governance composite (이사회 독립성·특수관계자) + (2) network density (계열사·affiliate ratio) + (3) audit-change (최근 2 년 감사인 변경) 3 신호 동시 적신호 종목 발굴. 한국 chaebol 구조 특유의 transfer-pricing / 일감몰아주기 위험을 단일 신호로 못 잡는 한계 보완. analysis ↔ scan 격리 메우는 cross-sectional 조합. 트리거 — 'governance audit network', 'chaebol risk screen'.
whenToUse:
  - governance audit network
  - chaebol 거버넌스 위험
  - 계열사 + 감사 + 거버넌스
linkedSkills:
  - engines.scan
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "근거 충족도는 engines.viz.evidenceCoverage로 검산/한계 섹션에만 배치하고 결론 차트처럼 해석하지 않는다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

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
    - "005380"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: triple flag 종목의 3y FSS 조사 / 제재 률이 unflagged 보다 낮으면 신호 무효
  pythonCheck: |
    assert fss_action_rate(triple_flagged) > fss_action_rate(unflagged)
expectedNovelty:
  - tripleFlag
  - networkDensity
forbidden:
  - 단일 affiliate 비중 (예: 50%) 만으로 일감몰아주기 단정 금지.
  - chaebol 회사 = 자동 risk 단정 금지 — 동행 신호 (audit + governance) 필수.
failureModes:
  - network density 정의 (단순 affiliate 매출 비중 vs 다층 지배 구조 정량화) 차이.
  - 감사인 rotation 의무 (2018 도입) 시점 이후 감사인 변경이 normal 화 — 임계 재조정.
examples:
  - KOSPI chaebol triple flag screen
  - 계열사 의존도 + 감사인 변경 동행
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. governance composite scan
gov = dartlab.scan("governance", market="KR")
if isinstance(gov, pl.DataFrame):
    gov_df = gov
elif isinstance(gov, list):
    gov_df = pl.DataFrame(gov)
else:
    gov_df = pl.DataFrame()

# 2. network density scan
net = dartlab.scan("network", market="KR")
if isinstance(net, pl.DataFrame):
    net_df = net
elif isinstance(net, list):
    net_df = pl.DataFrame(net)
else:
    net_df = pl.DataFrame()

# 3. audit-change scan
audit = dartlab.scan("audit", market="KR")
if isinstance(audit, pl.DataFrame):
    audit_df = audit
elif isinstance(audit, list):
    audit_df = pl.DataFrame(audit)
else:
    audit_df = pl.DataFrame()

# 4. 종목 단위 join (stockCode 키)
flagged = []
if "stockCode" in gov_df.columns:
    for code in gov_df["stockCode"].to_list()[:100]:
        gov_row = gov_df.filter(pl.col("stockCode") == code)
        net_row = net_df.filter(pl.col("stockCode") == code) if "stockCode" in net_df.columns else None
        audit_row = audit_df.filter(pl.col("stockCode") == code) if "stockCode" in audit_df.columns else None

        gov_amber = False
        if gov_row.height > 0:
            score = float(gov_row["score"][0]) if "score" in gov_row.columns else 50
            gov_amber = score < 40

        net_dense = False
        if net_row is not None and net_row.height > 0 and "affiliateDensity" in net_row.columns:
            net_dense = float(net_row["affiliateDensity"][0]) > 0.5

        audit_changed = False
        if audit_row is not None and audit_row.height > 0 and "auditorChangedRecently" in audit_row.columns:
            audit_changed = bool(audit_row["auditorChangedRecently"][0])

        flag_count = sum([gov_amber, net_dense, audit_changed])
        if flag_count >= 3:
            flagged.append({
                "stockCode": code,
                "govAmber": gov_amber,
                "networkDensity": net_dense,
                "auditChanged": audit_changed,
                "flagCount": flag_count,
                "tripleFlag": True,
            })

emit_result(
    table=flagged,
    values={"tripleFlagCount": len(flagged)},
    date="2024-12-31",
)
```

## 호출 동작

1. `dartlab.scan("governance")` — 거버넌스 composite (이사회 독립성·특수관계자).
2. `dartlab.scan("network")` — 계열사 affiliate density.
3. `dartlab.scan("audit")` — 최근 2 년 감사인 변경 여부.
4. stockCode 키로 join → 3 신호 boolean.
5. flag count = 3 → triple flag.

## 대표 반환 형태

`pl.DataFrame` — 컬럼 (triple flagged 만):
- `stockCode : str`
- `govAmber : bool` · `networkDensity : bool` · `auditChanged : bool`
- `flagCount : int`
- `tripleFlag : bool`

## 연계 절차

1. 본 recipe → triple flag 종목 KR universe 산출.
2. 각 종목 → `recipes.fundamental.quality.cashflowGovernanceDualSignal` 의 회사별 단독 검증.
3. distress 동시 발현 → `recipes.fundamental.credit.distressCandidateScreen` 결과와 교집합.
