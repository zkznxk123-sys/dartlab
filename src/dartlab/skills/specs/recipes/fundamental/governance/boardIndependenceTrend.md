---
id: recipes.fundamental.governance.boardIndependenceTrend
title: 이사회 독립성 추세 (사외이사 비중 + 다선 history)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 사외이사 비중 + 평균 임기 + 동시 다선 (다른 회사 이사회 동시 재직) 횟수의 연도별 추세. 단순 사외이사 비율이 아닌 *실질적 독립성* 측정. governance ↔ analysis 격리.
whenToUse:
  - 이사회 독립성 추세
  - 사외이사 비중
  - 다선 history
  - 거버넌스 점검
examples:
  - 005930 사외이사 비중 추세 연도별
  - 이사회 독립성 — 다선 동시재직 횟수
  - 거버넌스 실질 독립성 평가
expectedOutputs:
  - 사외이사 비중 5y 시계열 + YoY 변화
  - 평균 임기 + 동시 다선 (interlocking) 카운트
  - 라벨 (강 / 중 / 약 — 비중 + 다선 임계)
linkedSkills:
  - engines.company
  - engines.analysis
  - recipes.fundamental.governance.audit
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.mermaidDiagram"
  - "engines.viz.tableBackedChart"
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
gap:
  primary:
    - analysis
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "이사회 명부 raw 누락 회사는 결론 X. 다선 회수가 0 인데 사외이사 비중만 본 결론은 *실질적 독립성* 미증명."
lastUpdated: "2026-05-22"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    board_rows = c.gather("boardComposition").to_dicts()
except Exception:
    board_rows = []

audit = []
for r in sorted(board_rows, key=lambda x: str(x.get("year") or "")):
    total = int(r.get("totalDirectors") or 0)
    indep = int(r.get("independentDirectors") or 0)
    avg_tenure = float(r.get("avgTenureYears") or 0)
    multi_seat = int(r.get("multiSeatCount") or 0)
    audit.append({
        "year": r.get("year"),
        "independentPct": indep / total if total else None,
        "avgTenureYears": avg_tenure,
        "multiSeatCount": multi_seat,
    })

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"year": pl.Utf8, "independentPct": pl.Float64,
            "avgTenureYears": pl.Float64, "multiSeatCount": pl.Int64}
)

emit_result(
    table=table,
    values={"years": table.height},
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://gather/boardComposition"],
)
```

## 호출 동작

### 1. 결론 도출

3 축 시계열 + 실질 독립성 단정. 예: "최근 5y: 사외이사 비중 0.55 → 0.60 (개선) / 평균 임기 4.2y → 6.8y (악화 — 6y 초과) / multiSeat 0 → 2 (이사 2 명이 다른 이사회 동시 재직) → 표면 비중 ↑ but 실질 독립성 약화 (임기 + multiSeat 동시 악화)."

### 2. 핵심 근거 수집

- Company.gather('boardComposition') 연도별 row
- 연도별 (total / independent / avgTenure / multiSeat) 4 컬럼
- independentPct = independent / total
- 한국 상장사 권장 임계: 비중 ≥ 0.5 + 임기 ≤ 6 + multiSeat = 0

### 3. 메커니즘 분석

```
3 축 시계열 → 5y 추세
   independentPct YoY  ↑ → 비중 개선
   avgTenureYears 추세 ↑ → 임기 길어짐 (장기화 = 회사 의존도 ↑)
   multiSeatCount 추세  ↑ → 다선 (다른 이사회 동시) = 시간/주의 분산
   ↓
실질 독립성 = 3 축 결합:
   비중 ≥ 0.5 + 임기 ≤ 6 + multi=0 → 강
   2/3 충족                      → 중
   1/3 이하                      → 약 (실질 독립성 우려)
   ↓
표면 vs 실질 분리:
   비중만 보면 ↑ but 임기 + multiSeat 악화 → 실질 ↓
   (사외이사가 형식만 채우고 *실질 감시 기능* 약화)
```

KR governance — 한국 상장사 ≥ 4 인 사외이사 의무 (총 7 인 이사회 시 비중 0.57). 비중 0.5 임계는 *최소* — 실질 독립성은 임기 + multiSeat 결합 필요.

### 4. 반례·한계

- 다선 (multiSeat) 회수 0 이어도 임원-주주 관계 (혈연/사외 컨설팅) 미커버.
- 임기 ≤ 6y 권장은 KR 모범 기준 — US/EU 기준 다름.
- boardComposition raw 누락 시 결론 불가 (forensic 추정 X).
- 사외이사 *전문성* (회계 / 산업 / 법무) 분리 안 됨 — *비중* 만 측정.

### 5. 후속 모니터링

- 실질 독립성 약 → `recipes.fundamental.governance.audit` 로 거버넌스 종합 audit.
- multiSeat ↑ → `recipes.fundamental.governance.chaebolEntityNetwork` 로 그룹 내 이사 cross-holding 점검.
- 임기 ↑ + 보상 ↑ → `recipes.fundamental.quality.forensics.executiveCompensationAudit` 로 보상-이사회 정합.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `independentPct` | 사외이사 비중 |
| `avgTenureYears` | 평균 임기 |
| `multiSeatCount` | 다선 횟수 |

## 연계 절차

1. recipes.fundamental.governance.audit - 거버넌스 종합 audit.
2. recipes.fundamental.quality.forensics.executiveCompensationAudit - 보상-이사회 정합.

## 기본 검증

- 이사회 명부 raw 누락 시 결론 X.
- 다선 회수 0 이라도 *실질적 독립성* 측정엔 임원-주주 관계 추가 검증 필요.
- 비중 단독 결론 금지 — 3 축 분리 표기.
