# 데이터 워크벤치 SSOT — 공통배선 + 호출 캐시 작업대

상태: 비전/실행 PRD v0.1 (2026-06-17, 전문에이전트 3 렌즈 심층조사 + 코드 실측 검증)
범위: UI 런타임(`ui/packages/runtime`)의 **모든 데이터 호출(오리진·fetch·캐시·dedup)을 한 작업대 SSOT로 수렴** + 공개/로컬 공통배선 정착 + 로컬 전용(provider 서버 호출) 레인 단일화 + 폴더 구조화 + 운영문서 박제(향후 별도 패치 금지). 백엔드(Python) 데이터 파이프라인은 범위 밖(별도 SSOT = `feedback_terminal_hf_ssot_local_compute`).

> ⚠ 이 PRD 의 핵심은 *새 인프라를 만드는 게 아니다*. 운영자가 이미 만들어둔 작업대(`data/origin.ts` "Phase 0", `cache/runtimeCache.ts`, `cache/requestDedup.ts`)가 **export 만 되고 한 번도 배선되지 않은 채** 각 source 가 제각각 `new Map()` 을 재발명한 상태를 — *이미 만든 작업대에 전부 꽂는* 리팩토링이다.

---

## 한 줄 결론

데이터 호출 SSOT 작업대는 **이미 절반 존재한다**(origin.ts=HF URL SSOT 살아있음, RuntimeCache/RequestDedup=만들었으나 죽어있음). 남은 일은 ① fetch 코어 하나에 캐시·dedup·backoff 를 모아 죽은 작업대를 실배선하고 ② 오리진 7종을 origin 레지스트리 하나로 모으고 ③ 로컬 provider(/api) 호출을 단일 게이트로 모으고 ④ 폴더를 구조화한 뒤 ⑤ 운영문서 + 기계 가드로 박아 *앞으로 source 가 다시 제멋대로 fetch/Map 을 쓰지 못하게* 하는 것이다.

---

## 무엇을 만드나 (Section A)

1. **fetch 코어 SSOT (`data/fetch/`)** — 오리진 해소 + `fetchResilient`(backoff) + `RequestDedup`(in-flight) + `RuntimeCache`(TTL/LRU) + `cacheStore`(브라우저 영속, opt-in)를 한 `request()` 진입점으로 합성. 이미 만든 `RuntimeCache`·`RequestDedup` 를 *여기서 처음으로 인스턴스화*한다.
2. **오리진 레지스트리 (`data/origins/`)** — HF직결·HF range·CF hf-proxy·news워커·naver워커·local /api·duckdb-wasm CDN·landing JSON 8종을 *명명된 항목*으로 모은다. 각 항목 = URL 빌더 + 정책(캐시 TTL·range 직결 여부·env 게이트). env 전환면 단일화.
3. **로컬 provider 게이트 (`adapters/local/api/`)** — 흩어진 `/api` 호출(aiSource·filingSource panel·priceSource events·exportSource)을 단일 게이트 모듈로 모은다. 로컬 전용 레인의 유일 진입점.
4. **공통배선 정착** — 공개/로컬이 같은 fetch 코어·같은 캐시 인스턴스를 공유. 로컬은 "특별 명시"가 없으면 공개 HF source 재사용([[feedback_terminal_hf_ssot_local_compute]] 규칙5 코드화).

## 무엇을 잠그나 (Section B)

5. **운영문서 박제 + 기계 가드** — `operation/ui.md` 에 데이터층 SSOT 규칙 신설 + `tests/audit/` 에 TS 가드(source 가 raw `fetch`·직접 URL·자체 `new Map` 캐시 금지, 반드시 fetch 코어 경유) → 향후 별도 패치 없이 강제.
6. **폴더 구조화** — `data/{origins,cache,fetch}` + `adapters/local/api/` 로 향후 확장이 ad-hoc 패치 없이 슬롯에 꽂히게.

---

## 문서 지도

1. [00-vision-and-problem.md](00-vision-and-problem.md) — 왜·문제 정의·원칙(공통배선 default·dev=퍼블릭·로컬 전용 명시).
2. [01-current-state-audit.md](01-current-state-audit.md) — 실측 인벤토리(오리진 7·fetch wrapper 15·캐시 20+·죽은 작업대 2) + file 근거.
3. [02-target-architecture.md](02-target-architecture.md) — fetch 코어·오리진 레지스트리·캐시/dedup·공개/로컬 공통+로컬 provider 게이트 설계.
4. [03-folder-structure.md](03-folder-structure.md) — 현재 트리 + 향후 폴더 구조(슬롯 확장).
5. [04-killlist-and-non-goals.md](04-killlist-and-non-goals.md) — 안 건드리는 것(계약/포트·duckdb 엔진 병합·서버 도입·전면 재작성) + 정직 TTL 정책.
6. [05-migration-phasing-and-rollback.md](05-migration-phasing-and-rollback.md) — 4 페이즈·source 단위 이관 순서·롤백·테스트 매트릭스·이중 평가(개발자+PM).
7. [06-operation-codification-and-guard.md](06-operation-codification-and-guard.md) — operation 문서 박제 본문 + TS 가드 테스트 명세.
8. [07-progress-ledger.md](07-progress-ledger.md) — 세션 간 재개 원장(다른 세션 동시작업 충돌 회피 + NEXT 포인터).

---

## 정직 척추 (전 문서 관통)

- **새 발명 아님** — 죽은 작업대를 실배선. "만들어놓고 안 쓴" 모순 해소가 1순위.
- **공통배선 default** — 로컬은 명시적 로컬 전용이 아니면 공개와 같은 배선. dev 는 :8400 없이 퍼블릭 기준으로 떠야 정상.
- **정직 캐시** — 모든 캐시가 같은 TTL 이 아니다. `recent.parquet`·naver fresh tail 은 짧은/무 TTL(신선도 생명), 회사 panel·finance 는 길게. 오리진별 정책 명시(04 §정직 TTL).
- **계약 불변** — `DartLabRuntime` 17 포트 인터페이스는 안 바꾼다. 포트 경계 *뒤에서만* 이관(무중단).
- **점진 이관** — 전면 재작성 금지. source 한 개씩 fetch 코어로 옮기고, 옮긴 것만 가드 적용. 다른 세션의 surface 작업과 충돌 최소(런타임/data 계층만 건드림).
- **앞으로 못 어기게** — 운영문서(사상) + 기계 가드(강제) 둘 다. 문서만으론 회귀한다.
