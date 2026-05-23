---
id: recipes.news.repeatedHeadlineFrequency
title: 반복 헤드라인 빈도 (같은 사건의 여러 보도 카운트)
category: recipes
kind: recipe
scope: builtin
status: tested
purpose: 30 일 윈도우 안 같은 회사 관련 헤드라인 중 *제목 키워드 ≥ 3 어 중복* row 를 cluster 로 묶고 cluster 빈도 카운트. 단일 보도가 *여러 매체에 동시 확산* 했는지 정량. evidence-bound 형태 (sentiment 라벨 X).
whenToUse:
  - 반복 헤드라인
  - 같은 사건 보도 빈도
  - 매체 확산
  - 사건 cluster
linkedSkills:
  - engines.company
  - engines.gather
  - runtime.untrustedContent
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
  - "engines.viz.evidenceCoverage"
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
    - gather
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
falsifier:
  description: "헤드라인 < 10 표본이면 cluster 결론 X. 키워드 매칭 3 어 미만은 별 사건."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import re
from collections import Counter

target = "005930"
c = dartlab.Company(target)

try:
    news = c.gather("news").head(150).to_dicts()
except Exception:
    news = []

def tokens(title):
    return [w for w in re.findall(r"[가-힣A-Za-z]{2,}", title or "") if len(w) >= 2][:8]

clusters = []
used = set()
for i, n in enumerate(news):
    if i in used: continue
    t_i = set(tokens(n.get("title") or ""))
    if len(t_i) < 3: continue
    members = [i]
    for j in range(i+1, len(news)):
        if j in used: continue
        t_j = set(tokens(news[j].get("title") or ""))
        if len(t_i & t_j) >= 3:
            members.append(j)
            used.add(j)
    used.add(i)
    if len(members) >= 2:
        clusters.append({
            "headline": (news[i].get("title") or "")[:80],
            "repeatCount": len(members),
            "firstDate": news[members[-1]].get("date"),
            "latestDate": news[members[0]].get("date"),
        })

table = pl.DataFrame(clusters) if clusters else pl.DataFrame(
    schema={"headline": pl.Utf8, "repeatCount": pl.Int64, "firstDate": pl.Utf8, "latestDate": pl.Utf8}
)

emit_result(
    table=table,
    values={"clusterCount": table.height, "newsTotal": len(news)},
    date=None,
    sources=["dartlab://gather/news"],
)
```

## 호출 동작

뉴스 헤드라인 토큰화 (한국어/영어 2 자 이상) 후 같은 키워드 3+ 어 중복 row 묶어 cluster. repeatCount = cluster 멤버 수. 큰 cluster = *매체 확산* 강한 사건.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `headline` | cluster 대표 제목 |
| `repeatCount` | 반복 매체 수 |
| `firstDate` | 가장 빠른 보도 |
| `latestDate` | 가장 늦은 보도 |

## 연계 절차

1. recipes.news.disclosureNewsCrosscheck - cluster 의 공시 정합성.
2. recipes.news.eventTimelineFusion - cluster 의 가격 동반 변동.
3. recipes.news.untrustedToneAudit - cluster 본문 untrusted wrap 확인.

## 기본 검증

- 뉴스 < 10 이면 결론 X.
- *매체 확산 * = 중요한 사건 단정 금지 — 확산 자체가 정량 사실일 뿐.
- 토큰 매칭 한국어 (조사·접속어 제외 안 함) noise — 한계 명시.
