# 02. 타깃 아키텍처 — 단일 작업대 설계

상태: 설계 PRD v0.1. 모든 신규 코드는 기존 자산(origin.ts·hfRange·cacheStore·RuntimeCache·RequestDedup·LocalCaches) 위에 합성.

---

## 1. 계층 (한 장)

```
contracts/ports (불변)
        │
adapters/{public,local,test}  ← 포트 구현. createXRuntime 이 fetch 코어·캐시 인스턴스를 1개 만들어 source 에 주입
        │  (source 는 더 이상 fetch·URL·Map 을 직접 갖지 않는다)
data/fetch  ── request(spec) ─┬─ origins(spec.origin → URL)
        │                     ├─ RequestDedup(in-flight 공유, key=spec.cacheKey)
        │                     ├─ RuntimeCache(메모리 TTL/LRU)  ┐ 둘 다 spec.cache 정책으로 합성
        │                     ├─ cacheStore(브라우저 영속, opt-in)┘
        │                     └─ fetchResilient(backoff·range no-store)
        └─ adapters/local/api  ← 로컬 전용 provider 게이트(/api). request() 의 'localApi' 오리진으로 합성
```

원칙: **source 는 "무엇을(path) 어느 오리진에서(origin) 어떻게 캐시(cache)" 만 선언**하고, *어떻게 가져오는지*는 전부 코어가 한다.

## 2. fetch 코어 — `data/fetch/request.ts`

단일 진입점. 모든 데이터 호출이 통과.

```ts
export interface RequestSpec<T> {
  origin: OriginId;              // 오리진 레지스트리 키 ('hfRange'|'hf'|'localApi'|'newsWorker'|...)
  path: string;                  // 오리진 상대 경로 또는 엔드포인트
  parse: (res: Response) => Promise<T>;  // json/parquet rows/text — 호출부가 파싱 책임만 명시
  cache?: CachePolicy;           // { scope:'memory'|'persist'|'none', ttlMs, maxEntries, key }
  dedup?: boolean;               // 기본 true (동일 key in-flight 공유)
  range?: { start: number; end: number };  // parquet 범위읽기
  signal?: AbortSignal;
}

export function request<T>(spec: RequestSpec<T>): Promise<T>;
```

합성 순서(코어 내부): `cacheKey = key ?? `${origin}:${path}`` → ① 메모리 캐시 hit 면 반환 → ② RequestDedup.run(cacheKey, …) 로 in-flight 공유 → ③ origins.resolve(origin, path) 로 URL → ④ fetchResilient(backoff) → ⑤ parse → ⑥ cache.scope 에 따라 RuntimeCache.set / cacheStore.write. 에러는 캐시에 넣지 않는다(현재 reportSource 가 실패 Promise 를 캐시하는 버그 해소).

- **RuntimeCache·RequestDedup 를 여기서 처음 인스턴스화**한다(어댑터당 1). 죽은 작업대 실배선 = 본 PRD 의 1순위.
- parquet 전용 헬퍼는 `request()` 위에 얇게: `requestParquetRows(origin,path,{columns,filter,range})` 가 내부에서 hfRange 의 hyparquet 파싱을 parse 로 넘긴다(hfRange 로직 재사용, 캐시/dedup 만 코어로 승격).

## 3. 오리진 레지스트리 — `data/origins/`

8 오리진을 *명명 항목*으로. 각 항목 = `{ id, resolve(path)→url, defaultCache, rangeDirect?, env }`.

```ts
export type OriginId =
  | 'hf' | 'hfRange' | 'landingJson'      // HF 계열(origin.ts 흡수)
  | 'newsWorker' | 'naverWorker'          // CF 워커(env 게이트)
  | 'localApi'                            // 로컬 전용(:8400) — adapters/local/api 게이트가 등록
  | 'duckdbHf';                           // duckdb httpfs 가 읽는 HF parquet URL(landing 셸이 동일 레지스트리 사용)

export const ORIGINS: Record<OriginId, OriginDef>;
export function originUrl(id: OriginId, path: string): string;
```

- `hf`/`hfRange`/`landingJson` 은 현 `origin.ts` 로직(HF_RESOLVE·HF_RANGE_RESOLVE·range 직결 정책)을 **그대로 흡수**(origin.ts 는 레지스트리의 한 항목으로 재배치, 하위호환 re-export 유지).
- `newsWorker`/`naverWorker` 의 env 게이트(`VITE_DARTLAB_NEWS_PROXY`·`VITE_DARTLAB_NAVER_PROXY`)·dev `/__news`·`/__naver` 분기를 레지스트리 정의로 이관(source 에서 제거).
- `localApi` 는 로컬 어댑터만 등록(공개 어댑터엔 미등록 → 공개에서 `localApi` 호출 시 명시적 throw = 배선순서 가드 유지).
- `duckdbHf` 는 landing duckdb 가 HF parquet URL 을 만들 때 origin.ts 대신 레지스트리를 쓰게(이미 HF_RESOLVE 재사용 중이라 저비용).
- **정책 표 한곳**: env 전환(CF 프록시↔직결), range 직결 여부, 기본 TTL 을 레지스트리에서 한눈에.

## 4. 캐시/dedup 정책 — 오리진별 차등 TTL

`CachePolicy` 기본값을 오리진 정의가 제공, 호출부가 override:

| 오리진/데이터 | scope | TTL | 근거 |
|---|---|---|---|
| 회사 panel·finance·report parquet | memory | 세션(긴 maxEntries LRU) | 분기 단위 갱신, 같은 회사 재조회 빈번 |
| `recent.parquet`(가격/공시 신선도) | memory | 짧게(예 5–10분) | 신선도가 생명 — 길면 stale |
| naver fresh tail | memory | 짧게/무 | T+1 갭 채움, 매번 최신 필요 |
| landing JSON(dashboards·map) | persist(cacheStore) | 6h(현행) | 일배치 |
| news/naver 워커 | memory | 짧게 + **in-flight dedup 신설** | 현재 dedup 없음 |
| local `/api` | memory | 호출별(이벤트=짧게, panel=세션) | 로컬 전용 |

- **unbounded Map → RuntimeCache(maxEntries) 로 일괄 교체** → 세션 누수 차단.
- **dedup 없던 source(news/naver/nonReg/relations/industryPool) → 코어 RequestDedup 자동 적용** → 동시 중복 fetch 제거.

## 5. 공개/로컬 공통배선 + 로컬 provider 게이트

- **공통**: `createPublicRuntime`·`createLocalRuntime` 둘 다 코어 인스턴스(fetch+캐시+dedup) 1개를 만들어 source 에 주입. 로컬은 현재처럼 공개 HF source(price·finance·macro·index·report·company·filing 목록)를 *그대로 재사용* — 같은 코어를 공유하므로 캐시도 공유.
- **로컬 전용 게이트 `adapters/local/api/`**: 흩어진 `/api` 호출을 단일 모듈로 집결.
  - `localApi.ts` — `request({origin:'localApi', …})` 래퍼 + 엔드포인트 카탈로그(panel init/toc/grid, price-events, agent SSE, export). 로컬 전용 source(filing panel·ai·export)는 이 게이트만 호출.
  - 로컬 전용 레인의 *유일* 진입점 → "특별 기능"이 어디서 서버를 부르는지 한 파일에서 자명.
  - SSE(agent) 는 캐시 부적합 → 게이트가 stream 전용 경로 노출(코어 request 와 분리하되 오리진/URL 은 레지스트리 공유).
- **test 어댑터**: fake 코어(네트워크 0, 메모리 stub) — `createFakeRuntime` 가 동일 인터페이스 구현(계약 conformance tsc 검사 유지).

## 6. source 가 바뀌는 모습 (before/after)

before (nonRegularFilingsSource): 자체 `cache`·`batchCache` Map + 직접 `readParquetRows` + 직접 dedup 없음.
after:
```ts
export const loadCompanyNonRegularFilings = (code: string) =>
  requestParquetRows<RecentRow>({
    origin: 'hfRange', path: 'dart/allFilings/recent.parquet',
    cache: { scope: 'memory', ttlMs: MIN_10, key: `nonReg:${code}` },
    filter: { stock_code: { $in: [code] } }
  }).then(mapToNonRegular);
```
→ Map·dedup·backoff 전부 코어. source 는 "무엇을·어디서·캐시키" 만.

## 7. 무중단 보장

- 포트 인터페이스 불변 → surface·landing 무수정.
- source 한 개 이관 = 그 source 내부만 교체, 반환 타입 동일 → 회귀면 = 골든 픽스처(아래 05 테스트)로 검출.
- 코어는 기존 hfRange/cacheStore 로직을 *감싸는* 것이라 동작 동일(캐시 적중·dedup 추가가 순개선).
