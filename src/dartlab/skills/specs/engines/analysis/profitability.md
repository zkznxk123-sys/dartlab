---
id: engines.analysis.profitability
title: Analysis — 수익성 (profitability)
kind: curated
scope: builtin
status: observed
category: engines
purpose: 단일 기업의 *수익성* 축 분석 — 영업이익률·순이익률·ROE·ROA·ROIC 시계열과 peer 대비 위치를 검증한다. analysis 엔진의 22 축 중 financial 그룹의 핵심 entry.
whenToUse:
  - 수익성
  - profitability
  - 영업이익률 분석
  - ROE/ROA/ROIC
runtimeCompatibility:
  pyodide:
    status: supported
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
capabilityRefs:
  - dartlab.Company.analysis
---

# Analysis — 수익성 (profitability)

본 spec 은 `analysis("financial", "수익성")` 호출 결과의 구조와 의미를 서술. 상세는 `engines.analysis` (`SKILL.md`) 의 전체 22 축 표 참고.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")
result = c.analysis("financial", "수익성")
# → dict with keys: kpi, peer, timeline, flags, etc.
```

## 호출 동작

1. `_AXIS_REGISTRY["수익성"]` 의 calc 함수 (`dartlab.analysis.financial.profitability` 류) 호출.
2. company.select("IS") 로 손익계산서 가져옴 + ratios 컬럼 추출.
3. peer benchmark (`scan` 호출) 와 비교 → percentile / rank 산출.
4. timeline (최근 5 분기 + 5 년) + flags (positive / risk) 합성.

## 대표 반환 형태

```python
{
  "kpi": {"opMargin": 0.21, "netMargin": 0.17, "roe": 0.14, ...},
  "peer": {"opMargin": {"self": 0.21, "p50": 0.12, "p75": 0.18, "rank": "top quartile"}, ...},
  "timeline": pl.DataFrame(...),  # 기간 × 지표
  "flags": [Flag("positive", "finance", "건전한 수익구조"), ...],
}
```

## 기본 검증

- 반환 dict 의 `kpi` 키 존재 + 비율 -1 ~ 1 범위 (음수 적자 허용).
- `peer.opMargin.rank` 가 ("top quartile" / "above median" / "below median" / "bottom quartile") 중 하나.
- timeline 의 기간 컬럼 sortable.

## 관련

- [engines.analysis](/skills/engines.analysis) — 전체 22 축
- [engines.scan](/skills/engines.scan) — peer benchmark backing
- [engines.credit](/skills/engines.credit) — 수익성 + 자본구조 결합 신용 평가
