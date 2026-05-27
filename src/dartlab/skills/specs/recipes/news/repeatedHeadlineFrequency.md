---
id: recipes.news.repeatedHeadlineFrequency
title: 반복 헤드라인 빈도 (같은 사건의 여러 보도 카운트)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 30 일 윈도우 안 같은 회사 관련 헤드라인 중 *제목 키워드 ≥ 3 어 중복* row 를 cluster 로 묶고 cluster 빈도 카운트. 단일 보도가 *여러 매체에 동시 확산* 했는지 정량. evidence-bound 형태 (sentiment 라벨 X).
whenToUse:
  - 반복 헤드라인
  - 같은 사건 보도 빈도
  - 매체 확산
  - 사건 cluster
examples:
  - 005930 같은 사건이 여러 매체에 동시 확산
  - 30일 안 반복 헤드라인 cluster 빈도
  - 매체 확산도 — 같은 사건 보도 수
expectedOutputs:
  - cluster list (제목 키워드 + 매체 수 + 보도 시점)
  - cluster 빈도 단일값 (30d window 안)
  - 가장 확산도 큰 cluster top 3 (보도 수 기준)
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

cluster + repeatCount + 확산도 단정. 예: "30일 뉴스 150 row → cluster 8 개 (≥ 2 매체 중복). top 3: '반도체 가격 인상' repeat=12 / 'AI 협력 발표' repeat=8 / 'CEO 신임' repeat=5 → top cluster repeat=12 → *매체 확산* 강함 (12 매체 동일 사건 보도)."

### 2. 핵심 근거 수집

- Company.gather('news') latest 150 row
- 각 row title 토큰화 (한국어/영어 2자 이상)
- 키워드 매칭: 같은 키워드 ≥ 3 어 중복 → cluster
- cluster × (headline + repeatCount + firstDate + latestDate)

### 3. 메커니즘 분석

```
news 150 → title 토큰화 (한국어/영어 2자+)
   row[i] tokens vs row[j] tokens
   intersection ≥ 3 → same cluster
   ↓
cluster 형성:
   repeatCount = cluster 멤버 수 (≥ 2 필수)
   firstDate / latestDate = 시간 spread
   ↓
확산도 ranking:
   repeatCount ≥ 10 → 매체 확산 강 (top tier)
   repeatCount 3-9  → 보통 확산
   repeatCount 2    → 약한 확산 (noise 가능)
   ↓
정량 사실 (label X):
   확산 자체가 사건 중요도 의미 X
   sentiment / 호재/악재 단정 금지 (forbidden)
```

cluster = *매체 확산* 정량 — 사건 중요도 단정 X. 확산 자체가 정량 사실 (sentiment 라벨 분리). 단순 retweet (같은 source 의 다른 매체 카피) 도 cluster 로 잡힘.

### 4. 반례·한계

- 뉴스 < 10 → 결론 X (coverage 한계).
- 키워드 매칭 3 어 미만 → 별 사건 (false negative).
- 한국어 조사/접속어 (의/은/는/이/가) 미제거 → false positive (의미 없는 매칭).
- 동일 사건 vs 단순 카피 분리 X — 매체 확산만 측정.

### 5. 후속 모니터링

- top cluster repeat ≥ 10 → `recipes.news.disclosureNewsCrosscheck` 로 공시 정합성.
- cluster + 가격 변동 동조 → `recipes.news.eventTimelineFusion` 으로 가격 반응 cluster.
- cluster 본문 → `recipes.news.untrustedToneAudit` 로 untrusted wrap 검증.

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
