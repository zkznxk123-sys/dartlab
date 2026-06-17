# 03. 폴더 구조 — 현재 → 향후(슬롯 확장)

상태: 설계 PRD v0.1. CLAUDE.md 폴더 규칙 준수(루트 `scripts/` 금지·도메인 폴더, master only). 새 루트 폴더 신설 없음 — 전부 `ui/packages/runtime/src/` 내부.

---

## 1. 현재 트리

```
ui/packages/runtime/src/
├─ createRuntime.ts            진입(kind dispatch)
├─ runtimeContext.svelte.ts
├─ index.ts                    public exports (RuntimeCache·RequestDedup 죽은 export 포함)
├─ adapters/
│  ├─ public/createPublicRuntime.ts
│  │  └─ sources/   16개 (price·gov·finance·macro·report·news·company·relations·filings·industryPool·productIndex·export…)
│  ├─ local/createLocalRuntime.ts
│  │  ├─ fetchJson.ts          getJson(+notWiredYet)
│  │  ├─ localTypes.ts         LocalCaches·ClientPanel*·CompanyMeta
│  │  └─ sources/   ai·company·filing·price·scan·viewer·storage·export
│  └─ test/createFakeRuntime.ts
├─ cache/   runtimeCache.ts · requestDedup.ts        ← 죽어있음
├─ data/    origin.ts · hfRange.ts · dartlabData.ts · cacheStore.ts · financeRows.ts
└─ services/  serviceRegistry.ts · exportCommand.ts
```

문제: `data/` 가 origin+range+loader+cacheStore 가 평면으로 섞임. `cache/` 는 분리돼 있으나 미배선. 로컬 `/api` 가 source 들에 분산.

## 2. 향후 트리 (목표)

```
ui/packages/runtime/src/
├─ data/                       ★ 데이터 작업대 SSOT (단일 자원 허브)
│  ├─ fetch/
│  │  ├─ request.ts            request<T>() 단일 진입점 + requestParquetRows
│  │  ├─ resilient.ts          fetchResilient (hfRange 에서 이전)
│  │  └─ index.ts
│  ├─ origins/
│  │  ├─ registry.ts           ORIGINS 표 + originUrl() (8 오리진)
│  │  ├─ hf.ts                 HF_RESOLVE·HF_RANGE_RESOLVE (옛 origin.ts 흡수, re-export 하위호환)
│  │  └─ workers.ts            news·naver env 게이트 + dev 분기
│  ├─ cache/                   ← 기존 ../cache 를 data 하위로 이동(자원 허브 일원화)
│  │  ├─ runtimeCache.ts       (이동) — 코어가 인스턴스화
│  │  ├─ requestDedup.ts       (이동)
│  │  └─ cacheStore.ts         (이동, 브라우저 영속)
│  ├─ parquet/
│  │  └─ hfRange.ts            hyparquet 세션·refCache (fetch 코어가 호출)
│  └─ landingJson.ts           (옛 dartlabData.ts) loadJson/loadHfJson → request 위로 재구현
├─ adapters/
│  ├─ public/createPublicRuntime.ts   (코어 1 인스턴스 생성·주입)
│  │  └─ sources/   (16 — fetch/Map 제거, request() 호출로 축소)
│  ├─ local/
│  │  ├─ createLocalRuntime.ts
│  │  ├─ api/                  ★ 로컬 전용 provider 게이트 (단일)
│  │  │  ├─ localApi.ts        request({origin:'localApi'}) 래퍼 + 엔드포인트 카탈로그
│  │  │  └─ stream.ts          SSE(agent) 전용 경로
│  │  ├─ localTypes.ts
│  │  └─ sources/   (panel·ai·export·scan·viewer — api/ 게이트만 호출)
│  └─ test/createFakeRuntime.ts
├─ services/
├─ createRuntime.ts · runtimeContext.svelte.ts · index.ts
```

## 3. 이동 원칙

- **`cache/` → `data/cache/`**: 캐시는 데이터 작업대의 일부 — 자원 허브를 `data/` 하나로. (index.ts re-export 경로만 갱신, 외부 import 불변)
- **`origin.ts` → `data/origins/hf.ts`** + 하위호환 `data/origin.ts` re-export 유지(점진 이관 중 깨지지 않게).
- **`hfRange.ts` → `data/parquet/hfRange.ts`**: fetch 코어가 호출하는 parquet 엔진. fetchResilient 만 `data/fetch/resilient.ts` 로 분리.
- **로컬 `/api` → `adapters/local/api/`**: 분산된 호출을 게이트 한 폴더로. 향후 새 로컬 엔드포인트는 카탈로그에 한 줄 추가.

## 4. 향후 확장이 슬롯에 꽂히는 법 (ad-hoc 패치 제거)

| 새로 추가할 것 | 어디에 (한 곳) | 다른 곳 수정? |
|---|---|---|
| 새 데이터 소스(HF parquet) | public `sources/` 에 `request()` 호출 한 함수 | ✗ (캐시·dedup·backoff 자동) |
| 새 오리진(예: 새 워커) | `data/origins/registry.ts` 항목 1개 | ✗ |
| 새 로컬 `/api` 엔드포인트 | `adapters/local/api/localApi.ts` 카탈로그 1줄 | ✗ |
| 캐시 정책 변경 | 오리진 정의 `defaultCache` | ✗ (전 소비처 일괄) |
| env 프록시 전환 | 오리진 정의 env 필드 | ✗ |

→ "새 능력 = source 에 request 한 줄". Map·fetch·URL 재발명 금지(가드가 강제, 06).

## 5. 제약 준수

- 새 루트 폴더 0(전부 `ui/packages/runtime/src/` 내부) — CLAUDE.md `scripts/` 금지·도메인 폴더 규칙 무위반.
- master only — 브랜치/worktree 없음.
- 이동은 점진(05 페이즈). 한 번에 전 폴더 이동 금지 — re-export 다리 두고 source 단위로.
