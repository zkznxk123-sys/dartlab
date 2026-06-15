# 00 — 유니버스 4종 실현가능성 판정

> 이 문서가 make-or-break. "여러 유니버스 백분위"가 실제로 계산 가능한지, 무엇이 라이브이고 무엇이 막혔는지 코드로 판정한다.

## 판정 요약

| 유니버스 | 판정 | 빌드 경로 | 분포곡선(band) |
|---|---|---|---|
| ① 업종 (industry / KSIC 섹터) | **✅ 이미 라이브** | 현 `industryPercentile` 그대로 | ✅ industryStats |
| ② 소속시장 (KOSPI/KOSDAQ) | **✅ 라이브 (새 데이터 0)** | `EcoNode.market` 필터 | ✅ 노드 배열에서 라이브 5분위 |
| ③ 전체상장사 (all listed) | **✅ 라이브 (cross-sector caveat 강제)** | `raw.eco.nodes` 전체 | ✅ 노드 배열에서 라이브 5분위 |
| ④ 소속지수 (KOSPI200·코스닥150 등) | **❌ BLOCKED** | 구성종목 멤버십 데이터 부재 | — |

---

## ①②③ — 왜 라이브로 가능한가 (결정적 증거)

브라우저 engine 이 받는 `raw.eco.nodes` 배열은 **전 종목**에 대해 13개 정량 축 raw 값을 이미 싣는다 — [types.ts:111-152 `EcoNode`](../../ui/packages/surfaces/src/terminal/lib/types.ts): `roe·opMargin·netMargin·roa·debtRatio·icr·currentRatio·assetTurnover·ccc·accrualRatio·govScore·revCagr·netIncomeCagr`. 그리고 노드마다 `market` 필드(KOSPI/KOSDAQ/KONEX)가 있다(types.ts:116, `buildIndustryMap.py` 의 KRX listing `marketName` 조인 산물).

현 [engine.ts:303-336 `industryPercentile`](../../ui/packages/surfaces/src/terminal/lib/engine.ts) 는:
```
const peers = industryNodes(node.industry);     // ← 모집단을 업종 peer 로 고정
const col = (f) => peers.map(n => n[f] ?? null);
... pctRank(col('opMargin'), node.opMargin) ...  // 순수함수, 모집단 무관
```
즉 **모집단(`peers`) 한 줄만 바꾸면** 같은 코드가 다른 유니버스로 돌아간다:
- `'industry'`: `industryNodes(node.industry)` (현행, engine.ts:144 = `byIndustry[industry]`)
- `'market'`: `(raw.eco?.nodes ?? []).filter(n => n.market === node.market)`
- `'all'`: `raw.eco?.nodes ?? []`

`pctRank`(engine.ts:88-95)는 `(arr, v, lowerBetter?)` 만 받는 **유니버스 무관 순수함수**라 그대로 재사용. lowerBetter(부채비율·CCC·발생액비율)도 자동 보존되어 "상위 N%" 가 항상 우수를 뜻한다. **engine 이 받는 raw 에 전종목 모든 축 값이 이미 있다** — industryStats band 만 있는 게 아니다(band 는 분포곡선 렌더 보조).

### 비용
약 2,664 노드 × 13축 × 3유니버스 = O(10만) 정수 비교. 회사 전환마다 즉시(이미 `byIndustry` 인덱스 1회 구축 패턴 존재, engine.ts:142-144). **백분위 자체는 프리빌드 불필요.**

### 분포곡선(DistCurve band) — 전 유니버스 라이브 (prebuild 불필요)
`raw.industryStats`(types.ts:169-174)는 산업 단위 분포(p10~p90)를 *미리* 담지만, **시장/전체 분포곡선은 사전계산이 필요 없다.** DistCurve 는 `{p10,p25,median,p75,p90}` 만 받는데, 백분위 계산에 쓰는 *바로 그 모집단 배열*(market 필터/전체 노드)을 정렬해 5분위를 그 자리에서 뽑으면 된다. 비용 = 정렬 ~2664값 × 지표 × 유니버스, 다이얼로그 열 때 1회 → 무시 가능.
- 업종 유니버스: 기존 `industryStats` 밴드 유지(scan-grade 다이얼로그 미회귀).
- 시장/전체 유니버스: **같은 모집단에서 라이브 5분위 산출** → 백분위와 자기일관. 백분위·곡선이 한 빌드에 함께 나온다(단계 분할 없음).

---

## ④ 소속지수 — BLOCKED (정직 판정)

KRX 지수 데이터는 **OHLCV 전용**이다 — `IDX_NM`(지수명) + 종가/시총 포인트뿐, "어느 종목이 KOSPI200 에 속하는가" 라는 **구성종목 멤버십이 데이터 전체에 없다**(`gather/krx/krxIndex.py`, 빌더 `buildKrxIndexData.py` 모두 OHLCV 만 push). 코드 전역의 "코스피200/코스닥150" 은 전부 OHLCV 행의 지수 *이름*이지 편입 리스트가 아니다. KRX OpenAPI `idx` endpoint 도 멤버십을 안 준다.

→ 새 데이터 소스(별도 구성종목 API/수집) 확보 전엔 BLOCKED. **흔한 우회 — "시총 상위 N개 = KOSPI200 근사" 는 부정확한 위조라 정공법 위반**(02 KILL #5). 이 유니버스는 Phase 3 에서 *구성종목 수집 졸업게이트 선행* 후에만 열거나, 영구히 지수로의 **link-only**(백분위 미산출)로 둔다.

---

## 정성(범주형) 지표 — "백분위 성립 안 함"

거버넌스 A~E·자본환원 분류·부채위험 4단계·이익질 등급은 순위가 아니라 *분류*다. 백분위처럼 0~100 으로 색칠하면 가짜 정량화(02 KILL #3). 처리:
- **연속 점수가 있으면**(예: `govScore`) 그걸로 진짜 백분위, 등급은 라벨로만.
- **순수 범주**(자본환원 분류 등)는 백분위 칸을 비우고 **등급 칩 + 동급 비중**("이 유니버스 중 B등급 28%")만. 등급→서열 매핑이 필요하면 [engine.ts:104 `gradeScore`](../../ui/packages/surfaces/src/terminal/lib/engine.ts) 재사용(0~1, 이미 존재).

---

## 재발명 금지 — 재사용 헬퍼

| 헬퍼 | 위치 | 재사용 |
|---|---|---|
| `pctRank` | engine.ts:88 | 4유니버스 전부(유니버스 무관 순수함수) |
| `industryPercentile` 패턴 | engine.ts:303 | 모집단 필터만 교체해 일반화 |
| 5분위 산출 로직 | `_distribution`(`industry/.../buildIndustryMap.py:1112`) 동형 | 시장/전체 band 라이브 산출 — 브라우저에서 정렬+인덱스 |
| `gradeScore` (등급→0~1) | engine.ts:104 | 정성 지표 서열 |
| `DistCurve` | terminal/panels/DistCurve.svelte | 분포곡선(band 있는 유니버스) |

파이썬측 `calcPeerPosition`/`getScanPosition` 은 parquet 직접 스캔·캐시 기반이라 브라우저 다이얼로그엔 부적합(다운로드 유발). 차용할 건 *컨셉*(범주형은 분포, 연속은 순위)이지 함수 자체가 아니다.

## 한 줄 판정

③ 업종은 이미 됨, ①시장·②전체는 **engine 이 받는 EcoNode raw 에 전종목 13축 + market 이 있어 새 데이터 0 · 라이브 즉시 가능**, ④소속지수는 **구성종목 멤버십 데이터 자체가 없어 BLOCKED**(별도 수집 선행 없이는 빼거나 link-only). 정성지표는 백분위 대신 *등급 칩 + 동급 비중*.
