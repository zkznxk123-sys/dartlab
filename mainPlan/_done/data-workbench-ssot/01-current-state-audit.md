# 01. 현재 상태 실측 감사

상태: 감사 v0.1 (전문에이전트 3 렌즈 + grep/read 검증). 모든 항목 file 근거.

---

## 1. 오리진 7+종 (URL 을 어디서 만드나)

| 오리진 | URL 구성 | env 게이트 | origin.ts 경유? | 소비처 |
|---|---|---|---|---|
| HF 직결(whole-file) | `data/origin.ts` `hfUrl()` (`HF_RESOLVE`) | `VITE_DARTLAB_HF_RESOLVE` | ✅ | 전 public source(소형 통파일·seed) |
| HF range(byte-range) | `data/origin.ts` `hfRangeUrl()` (`HF_RANGE_RESOLVE`) | `VITE_DARTLAB_HF_RANGE_RESOLVE` | ✅ | hyparquet 범위읽기(panel·finance·price) |
| CF hf-proxy | `VITE_DARTLAB_HF_RESOLVE` 를 워커 URL 로 지정(env) | 위와 동일 | ✅(env 치환) | HF 직결과 동일 경로(콜드 403 흡수) |
| news 워커 | `newsSource.ts` 자체 구성(`/news`·`/__news`) | `VITE_DARTLAB_NEWS_PROXY` | ❌ 독립 | `news.forCompany` |
| naver 워커 | `naverPriceSource.ts` 자체(`/naver`·`/__naver`) | `VITE_DARTLAB_NAVER_PROXY` | ❌ 독립 | gov 미발행 fresh tail |
| 로컬 `/api`(:8400) | `local/fetchJson.ts` `getJson(apiBase, path)` | apiBase 주입 | ❌ 독립 | aiSource·filingSource(panel)·priceSource(events)·exportSource |
| duckdb-wasm CDN | `landing/src/lib/data/duckdb.ts` jsdelivr 하드코딩 + HF parquet(httpfs) | 없음(HF 부분만 origin.ts) | 부분 | `shared.reportFacts`·`shared.changes`(셸 주입) |
| landing JSON | `data/dartlabData.ts` `${HF_RESOLVE}/landing/` + 로컬 폴백 | 없음 | ✅(HF 부분) | dashboards·map·meta |

> dev 전용 미들웨어(`landing/vite.config.ts`): `/__gov`·`/__naver`·`/__news` — 프로덕션엔 CF 워커/빈값. 이것도 URL 하드코딩.

**결론**: HF 계열만 origin.ts SSOT 경유. 워커·로컬·duckdb CDN 은 제각각 URL 구성.

## 2. fetch wrapper 7+종 (진입점 분산)

| wrapper | 위치 | backoff | in-flight dedup | 캐시 |
|---|---|---|---|---|
| `getJson` | `local/fetchJson.ts` | ✗ | ✗ | ✗ |
| `fetchResilient` | `data/hfRange.ts` | ✅ 3retry(403/429/5xx) | ✗ | 브라우저 |
| `readParquetRows`/`WholeFile`/`headHfObject` | `data/hfRange.ts` | ✅(fetchResilient) | HEAD 만 refCache | ✗ |
| `loadJson`/`loadHfJson` | `data/dartlabData.ts` | ✗ | ✗ | ✅ cacheStore(IndexedDB/Cache API, 6h) |
| inline `fetch`(news) | `newsSource.ts` | ✗ | ✗(동기 Map) | in-memory Map |
| inline `fetch`(naver) | `naverPriceSource.ts` | ✗ | ✗ | in-memory Map |
| `streamAgentRun`(SSE) | `local/sources/aiSource.ts` | ✗ | ✗ | ✗ |

**결론**: backoff·dedup·캐시가 wrapper 마다 제각각. news/naver 는 backoff·in-flight dedup 둘 다 없음.

## 3. 죽은 작업대 2종 (만들었으나 미배선)

- `cache/runtimeCache.ts` `RuntimeCache<V>` — `{maxEntries, ttlMs}` 생성자, `get`(LRU touch)/`set`(FIFO evict)/`clear`. **`new RuntimeCache` 호출 0건**(grep: `index.ts` 재export 뿐).
- `cache/requestDedup.ts` `RequestDedup` — `run<T>(key, fn)` in-flight 공유 후 finally 삭제. **인스턴스화 0건.**

→ 이 둘이 본 리팩토링의 *재료*다. 새로 안 만든다.

## 4. 산재 캐시 20+곳 (재발명)

| source | 캐시 | bounded | TTL | in-flight dedup |
|---|---|---|---|---|
| `reportSource.ts` | 11개(wf/inv/sr/own/shp/eb/dp/cc/at/tp/af) | ✗ unbounded | ✗ | Promise 저장으로만 |
| `financeSource.ts` | rowsCache·bundleCache | ✗ | ✗ | Promise 저장 |
| `macroSource.ts` | srcCache(fred/ecos 2) | ✅(2) | ✗ | Promise |
| `priceSource.ts`(public) | cache(CACHE_CAP=16 LRU)+inflight | ✅16 | ✗ | ✅ |
| `govPriceSource.ts`·`govIndexSource.ts` | cache+inflight(+nameScanCache unbounded) | 부분 | ✗ | ✅ |
| `nonRegularFilingsSource.ts` | cache·batchCache | ✗ | ✗ | ✗ |
| `newsSource.ts`·`naverPriceSource.ts` | cache | ✗ | ✗ | ✗ |
| `relationsSource.ts`·`industryPoolSource.ts` | cache | ✗ | ✗ | ✗ |
| `productIndexSource.ts` | 싱글턴 Promise(??=) | ✅1 | ✗ | ✅(암묵) |
| local: `companySource`(productIndex 싱글턴), `filingSource`/`priceSource`(LocalCaches 주입) | — | — | ✗ | 부분 |

**갭 요약**: unbounded(세션 누수 위험) 다수 · in-flight dedup 없는 곳(news/naver/nonReg/relations/industryPool) · TTL 전무(세션 내 영구 stale, naver fresh tail 조차 갱신 안 됨).

## 5. 이미 옳은 패턴 (재사용·확장할 것)

- `data/origin.ts` — HF URL SSOT(env 전환·range 분리 정책 주석까지). **확장 기반**.
- `data/hfRange.ts` `fetchResilient` — backoff/`no-store` range 정책. **fetch 코어의 backoff 층으로 승격**.
- `data/cacheStore.ts` — 브라우저 Cache API(`x-dartlab-cache-ts` TTL·allow-stale). **영속 층으로 합성**.
- `local/localTypes.ts` `LocalCaches` + `createLocalRuntime` 주입 — "어댑터가 캐시 인스턴스를 만들어 source 에 주입". **공개 어댑터로 일반화할 패턴**.
- contracts 17 포트 + "포트 전 메서드 required·silent fallback 금지" 계약 — **불변, 경계 뒤에서만 이관**.

## 6. 정량

| 지표 | 수 |
|---|---|
| 오리진 | 7+ (HF직결·range·CF·news·naver·/api·duckdb + landing JSON) |
| fetch wrapper | 7+ |
| 산재 캐시 구현 | 20+ (reportSource 11 포함) |
| 죽은 작업대 export | 2 (RuntimeCache·RequestDedup) |
| 로컬 `/api` 호출 분산 | 4 source(ai·filing·price·export) |
| TS import 가드 | 0 (Python `tests/architecture/*` 만 존재) |
| operation 문서 데이터층 섹션 | 0 (`operation/ui.md` 빌드/SPA 만) |
