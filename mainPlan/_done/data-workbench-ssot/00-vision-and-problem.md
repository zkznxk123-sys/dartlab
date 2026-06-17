# 00. 비전과 문제 정의

상태: 비전 PRD v0.1

---

## 1. 문제 — "작업대는 있는데 아무도 안 꽂혀 있다"

운영자는 데이터 호출을 한곳에서 관리하려고 작업대를 *이미* 만들기 시작했다:
- `ui/packages/runtime/src/data/origin.ts` — 주석에 직접 *"데이터 호출 경로를 한곳에서 관리(SSOT) — 데이터 워크벤치 Phase 0"*.
- `ui/packages/runtime/src/cache/runtimeCache.ts` — `RuntimeCache<V>`(maxEntries·ttlMs·LRU).
- `ui/packages/runtime/src/cache/requestDedup.ts` — `RequestDedup.run(key, fn)`(in-flight 공유).

그런데 실측 결과:
- **origin.ts 는 HF resolve URL *하나만* 덮는다.** 나머지 오리진(CF hf-proxy·news/naver 워커·local `/api`·duckdb-wasm CDN)은 각 source 가 제 URL 을 직접 만든다.
- **`RuntimeCache`·`RequestDedup` 는 `index.ts` 에서 export 만 되고 코드 전체에서 단 한 번도 `new` 되지 않는다**(grep 확정). 죽은 작업대다.
- 대신 **~20+ source 가 각자 `new Map()` 캐시·dedup 을 재발명**한다. `reportSource.ts` 한 파일에만 11개(wf/inv/sr/own/shp/eb/dp/cc/at/tp/af). 다수가 unbounded(세션 누수)·in-flight dedup 없음(동시 중복 fetch)·TTL 없음(세션 내 영구 stale).

요약: **URL 은 (HF 만) 한 곳, 캐시·dedup·그 외 오리진·fetch 는 16+ 곳.** 새 데이터 능력을 추가할 때마다 "또 Map 만들고 또 fetch 짜는" ad-hoc 패치가 반복된다 — 이게 "뒤죽박죽"의 정체다.

## 2. 왜 지금 — 회귀의 누적

이번 세션의 공시워치/포렌식 작업에서 정확히 이 함정에 빠졌다(`feedback_terminal_hf_ssot_local_compute` 위반사례2): 신선도를 공통배선이 아니라 로컬 `/api` 에 물렸고, `localReportPort` 가 죽은 스텁이라 로컬 report 가 통째로 비어있었다. **작업대가 없어서가 아니라, 작업대에 꽂는 단일 규칙·강제가 없어서** 매번 새로 틀린다. 문서(사상)와 기계 가드(강제)로 박지 않으면 영구히 반복된다.

## 3. 비전 — 모든 자원을 한 작업대 SSOT 로

데이터를 요구하는 모든 표면(terminal·viewer·scan·map·ask·landing)이 *어디서 오든*(HF·CF·워커·로컬·duckdb) **하나의 작업대를 통해** 가져온다:

```
surface → runtime port → data/fetch.request({ origin, path, cache, dedup }) → 오리진 레지스트리 → 네트워크
                                         └ RuntimeCache(TTL/LRU) · RequestDedup(in-flight) · cacheStore(영속) 공통 적용
```

- **단일 진입점**: source 는 `fetch`/URL/`new Map` 을 직접 쓰지 않는다. 전부 `request()` 한 곳으로.
- **오리진 레지스트리**: 8 오리진이 명명 항목으로 모여 env 전환·정책(TTL·range·프록시)을 한 표에서 관리.
- **공통 캐시/dedup**: 죽어있던 `RuntimeCache`·`RequestDedup` 를 여기서 실배선. 20+ 산재 Map 을 어댑터당 단일 인스턴스로 수렴.
- **로컬 provider 게이트**: 로컬 전용 `/api` 호출을 한 게이트로. 로컬 전용 레인이 *명시적으로* 한곳에만 존재.

## 4. 원칙 (전 설계 관통)

1. **공통배선 default** — 로컬은 *명시적 로컬 전용*이 아니면 공개와 같은 배선·같은 캐시. (`feedback_terminal_hf_ssot_local_compute` 규칙5)
2. **dev = 퍼블릭 기준** — 로컬 앱은 `:8400` 없이 정적 HF 로 떠야 정상. `/api` 는 진짜 로컬 전용(라이브 provider·AI·뷰어 격자)만.
3. **로컬 전용은 한 곳에 모은다** — 흩어진 `/api` 호출을 단일 게이트로. "특별 기능"의 위치가 명시적·단일.
4. **계약 불변·점진 이관** — 포트 인터페이스 뒤에서만 바꾼다. source 한 개씩. 무중단.
5. **정직 캐시** — 오리진별 TTL 차등(신선도 데이터는 짧게/무). 일괄 캐시로 stale 을 만들지 않는다.
6. **문서 + 기계 둘 다** — 사상은 operation 문서, 강제는 가드 테스트. 문서만으론 회귀한다.

## 5. 성공 기준 (측정 가능)

- source 파일에서 raw `fetch(`·직접 URL 문자열·자체 `new Map()` 캐시 **0건**(가드 테스트 green).
- `RuntimeCache`·`RequestDedup` **인스턴스화 ≥1**(죽은 코드 해소), 산재 캐시 Map 20+ → 어댑터당 1 코어로 수렴.
- 8 오리진 전부 오리진 레지스트리 경유(직접 URL 구성 0).
- 로컬 `/api` 호출이 단일 게이트 모듈 1곳에만 존재.
- dev(`:8400` off)에서 터미널 전 패널(차트·재무·공시목록·워치·포렌식·공급망) 동작.
- `operation/ui.md` 데이터층 섹션 + 가드 테스트 CI 등록.
