# 04. 킬리스트 · 비목표 · 정직 TTL

상태: 경계 PRD v0.1. "다 SSOT 로 모은다"가 *전면 재작성*으로 번지는 것을 차단.

---

## 1. KILL (하지 않는다)

- ❌ **계약/포트 변경.** `DartLabRuntime` 17 포트 인터페이스·반환 타입 불변. 리팩토링은 *포트 구현 뒤*에서만. 포트를 건드리면 surface·landing 전부 회귀 위험 + 다른 세션 충돌.
- ❌ **전면 재작성.** "한 번에 20 source 갈아엎기" 금지. source 한 개씩 코어로 이관(05). 큰 빅뱅 PR 금지.
- ❌ **duckdb-wasm 엔진을 fetch 코어에 병합.** duckdb 는 SQL 엔진(httpfs 로 HF parquet 직독) — 성격이 다르다. *오리진 레지스트리에서 URL 만 가져오게* 정렬할 뿐, 쿼리 경로를 코어로 흡수하지 않는다.
- ❌ **공개 플로어에 서버 도입.** 퍼블릭은 서버 0 정적 유지. `localApi` 오리진은 로컬 어댑터만 등록(공개 호출 시 throw = 배선순서 가드).
- ❌ **단일 글로벌 캐시 인스턴스(싱글턴 전역).** 어댑터당 인스턴스(런타임 생명주기에 묶음). 전역 싱글턴은 테스트 격리·다중 런타임(soft-swap)에서 오염.
- ❌ **모든 데이터 일괄 동일 TTL.** 신선도 데이터까지 길게 캐시하면 stale 회귀. 오리진별 차등(아래 §정직 TTL).
- ❌ **새 캐시/fetch 라이브러리 도입.** 이미 있는 RuntimeCache·RequestDedup·cacheStore·fetchResilient 로 충분. 외부 의존 추가 금지.
- ❌ **백엔드(Python) 데이터 파이프라인 손대기.** 본 PRD 는 UI 런타임 한정. HF=SSOT·CI consolidation 은 별도(`feedback_terminal_hf_ssot_local_compute`).

## 2. DEFER (이번 범위 밖, 후속)

- ⏸ **scan/map/search/ai 포트의 본격 배선** — 단계-7·8(별도 추출 PRD) 소관. 본 PRD 는 이들이 코어를 *쓸 수 있는* 구조만 마련(throw 게이트 유지).
- ⏸ **landing 의 duckdb OPFS 캐시 전략 고도화** — 오리진 레지스트리 정렬까지만. OPFS 수명/재빌드는 별도.
- ⏸ **캐시 메트릭/관측(hit/miss/evict 카운터)** — 코어에 hook 자리만 두고, 대시보드화는 후속.
- ⏸ **cross-session 영속 캐시(IndexedDB) 확장** — 현 cacheStore(landing JSON) 범위 유지. parquet 메타까지 영속화는 후속.

## 3. 정직 TTL 정책 (오리진별 — 일괄 금지)

| 데이터 | TTL | 왜 |
|---|---|---|
| 회사 panel·finance·report parquet | 세션(LRU maxEntries, 무만료) | 분기 갱신·재조회 빈번 — 길게 OK |
| `recent.parquet`(가격/공시 신선도) | 5–10분 | 신선도가 가치 — 길면 "최근 공시" 거짓 |
| naver fresh tail | 짧게/무캐시 | T+1 갭 채움, 매 조회 최신 필요 |
| landing JSON(dashboards·map·meta) | 6h(현행 cacheStore) | 일배치 |
| news/naver 워커 | 짧게 + in-flight dedup | 현재 dedup 없음(중복 fetch) |
| 로컬 `/api` events | 짧게 | 동적 |

**원칙**: 캐시는 *정확성*을 해치면 안 된다. "신선도 라벨이 붙은 데이터"는 짧은 TTL 이 기본. 길게 캐시할 것과 짧게 할 것을 오리진 정의에 명시하고, 의심스러우면 짧게.

## 4. 정직 한계 (이 PRD 가 *해결하지 않는* 것)

- 뉴스가 dev 에서 안 뜨는 것은 워커 정책(private 저작권)이라 공통배선으로 못 푼다 — 본 PRD 는 *호출 경로 일원화*까지(데이터 가용성 정책은 불변).
- 공시뷰어 격자(panel)는 진짜 로컬 전용(공개도 단계-6 notWiredYet) — `localApi` 게이트로 *모으되* 공개화하지 않는다.
- 캐시 적중률·속도 개선은 *부산물*이지 목표가 아니다. 목표는 **SSOT 단일화 + 회귀 차단(가드)**.
