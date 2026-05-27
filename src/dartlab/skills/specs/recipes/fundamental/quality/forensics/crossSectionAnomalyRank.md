---
id: recipes.fundamental.quality.forensics.crossSectionAnomalyRank
title: Cross Section Anomaly Rank
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: incubator.forensics
purpose: scan.quality, scan.audit, scan.disclosureRisk 같은 L1.5 횡단 primitive를 포렌식 후보 발굴에만 사용하고, 단일 기업 결론은 원표 selfRun으로 다시 검증하게 만든다. 트리거 — '포렌식 이상치 랭킹', 'scan primitive 이상치'.
whenToUse:
  - 포렌식 이상치 랭킹
  - scan primitive 이상치
  - 공시리스크 상위 후보
  - 이익의 질 횡단 후보
inputs:
  - scan quality rows
  - scan audit rows
  - scan disclosureRisk rows
outputs:
  - anomaly candidate rows
  - candidate status
capabilityRefs:
toolRefs:
  - RunPython
  - EngineCall
sourceRefs:
  - dartlab://skills/recipes.fundamental.quality.forensics.crossSectionAnomalyRank
requiredEvidence:
  - skillRef
  - universe
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
expectedOutputs:
  - scan primitive 기반 후보 표
  - universe와 axis
  - 단일 기업 검증으로 넘길 target
linkedSkills:
  - recipes.fundamental.quality.forensics.deepDive
  - recipes.fundamental.quality.forensics.engineCandidateMemo
  - engines.company
gap:
  primary:
    - scan
    - synth
falsifier:
  description: "횡단면 이상치가 단일 기업 원표 검증에서 반복되지 않으면 엔진 후보로 승격하지 않는다."
forbidden:
  - scan 후보를 분석 결론으로 확정하지 않는다.
  - universe, 기준일, axis 없이 후보를 나열하지 않는다.
failureModes:
  - scan column 이름이 축마다 달라 score 추출 실패
  - 후보 상위권이 데이터 결손 회사로 채워짐
examples:
  - 공시리스크 이상치 후보 뽑고 원표로 검증
  - scan quality 기반 포렌식 후보
lastUpdated: "2026-05-15"
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
testUniverse:
  market: KR
  stockCodes:
    - "005930"
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
  - "engines.viz.tableBackedChart"
---

## 공개 호출 방식

```python
import dartlab
from dartlab.synth.evidenceForensics import buildEvidenceForensicsMemo

target = "005930"
scanRows = []
for axis in ("quality", "audit", "disclosureRisk"):
    try:
        df = dartlab.scan(axis)
        rows = df.head(5).to_dicts() if hasattr(df, "head") else []
        for row in rows:
            row["axis"] = axis
        scanRows.extend(rows)
    except Exception:
        pass

memo = buildEvidenceForensicsMemo(
    target=target,
    market="KR",
    companyName=target,
    scanRows=scanRows,
)

emit_result(
    table=memo["tables"]["crossSectionAnomalyRank"],
    values={"target": target, "candidateRows": len(memo["tables"]["crossSectionAnomalyRank"])},
    date=memo["asOf"],
    sources=memo["sources"],
)
```

## 호출 동작

### 1. 결론 도출

scan primitive는 후보 발굴만 한다. 결과는 `candidate` 또는 `watch` row이며 단일 기업 위험 결론이 아니다.

### 2. 핵심 근거 수집

`dartlab.scan("quality")`, `dartlab.scan("audit")`, `dartlab.scan("disclosureRisk")` 같은 L1.5 횡단 primitive의 상위 row를 받는다.

### 3. 메커니즘 분석

횡단면 이상치는 selfRun 타깃 선택에 유용하다. 하지만 개별 회사의 원표와 공시 본문 검증을 통과해야 엔진 후보 신호가 된다.

### 4. 반례·한계

prebuilt scan 기준일, 결손값, 축별 score 정의가 다르다. 후보 row에는 universe와 axis를 반드시 남긴다.

### 5. 후속 모니터링

상위 후보는 `deepDive`를 통해 Company.show 원표 기반으로 다시 실행한다.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `rank` | 후보 순위 |
| `target` | 종목 코드 또는 ticker |
| `name` | 회사명 |
| `metric` | scan axis 또는 metric |
| `score` | 후보 score |
| `status` | candidate/watch |

## 연계 절차

1. engines.scan - quality, audit, disclosureRisk primitive로 후보를 발굴한다.
2. recipes.fundamental.quality.forensics.deepDive - 후보별 원표 검증.
3. recipes.fundamental.quality.forensics.engineCandidateMemo - 반복 성공 신호만 승격 후보.

## 기본 검증

- scan 결과가 비면 빈 후보를 그대로 드러낸다.
- candidate row를 투자 판단처럼 쓰지 않는다.
