# 05. 이관 페이즈 · 롤백 · 테스트 · 이중 평가

상태: 실행 PRD v0.1. 점진·무중단·source 단위. 다른 세션이 surface 작업 중 → 충돌면 최소(런타임/data 계층만).

---

## 1. 페이즈 (각 독립 출시·롤백 가능)

### P1 — fetch 코어 신설 + 죽은 작업대 실배선 (기반·최고 ROI)
- `data/fetch/request.ts`(`request`·`requestParquetRows`) 신설. 내부에 `RuntimeCache`·`RequestDedup`·`cacheStore`·`fetchResilient` 합성. **여기서 RuntimeCache/RequestDedup 첫 인스턴스화.**
- `createPublicRuntime`·`createLocalRuntime` 가 코어 인스턴스 1개 생성·주입(공개에 `LocalCaches` 패턴 일반화).
- 아직 source 는 미이관 — 코어만 존재(테스트로 검증). 영향: 신규 파일 + 어댑터 2개 생성자.
- **롤백**: 코어 미사용이면 무영향(추가만). source 미이관이라 동작 동일.

### P2 — 오리진 레지스트리 (`data/origins/`)
- `origin.ts` 흡수(re-export 유지) + news/naver env 게이트·dev 분기 이관 + `localApi`·`duckdbHf` 항목 등록.
- 아직 source URL 구성은 유지(레지스트리가 같은 URL 산출 확인). 영향: data/origins 신설, origin.ts re-export.
- **롤백**: 레지스트리 미참조면 무영향. env 동작 동일성 테스트로 검증.

### P3 — source 이관 (한 개씩, 골든 픽스처 동행)
이관 순서(저위험·고중복 우선):
1. `nonRegularFilingsSource`(이번 세션 신규·dedup 없음 — 즉효) · `relationsSource` · `industryPoolSource`
2. `newsSource` · `naverPriceSource`(dedup·TTL 신설 효과 큼)
3. `reportSource`(11 Map → 코어 1, 최대 정리)
4. `financeSource` · `macroSource` · `productIndexSource`
5. `priceSource`/`govPriceSource`/`govIndexSource`(이미 LRU/dedup 있음 — 정렬만)
6. 로컬 `/api` → `adapters/local/api/` 게이트로 모으기(filing panel·ai·export·price-events)
- 각 source 이관 = 그 파일 내부만 교체, 반환 타입 동일. 이관한 source 에만 가드 적용(P4).
- **롤백**: source 단위라 문제 source 만 직전 커밋 되돌림(나머지 무영향).

### P4 — 폴더 구조화 + 가드 + 운영문서 박제
- 03 의 폴더 이동(`cache/`→`data/cache/`, `hfRange`→`data/parquet/` 등, re-export 다리).
- `tests/audit/` TS 가드 신설(06) + CI 등록.
- `operation/ui.md` 데이터층 섹션 신설(06).
- **롤백**: 가드는 baseline 부채원장으로 시작(신규 위반만 차단), 문서·이동은 독립.

## 2. 영향 파일 (전수)

- **신규**: `data/fetch/{request,resilient,index}.ts`, `data/origins/{registry,hf,workers}.ts`, `adapters/local/api/{localApi,stream}.ts`, `tests/audit/checkUiDataWiring.*`, `src/dartlab/skills/specs/operation/ui.md`(섹션 추가).
- **이동(re-export 다리)**: `cache/*`→`data/cache/*`, `data/hfRange.ts`→`data/parquet/`, `data/origin.ts`→`data/origins/hf.ts`, `data/dartlabData.ts`→`data/landingJson.ts`.
- **수정(이관)**: public sources 16 + local sources 8 (각 fetch/Map 제거→request 호출), `createPublicRuntime.ts`·`createLocalRuntime.ts`(코어 주입), `index.ts`(export 경로).
- **불변**: `ui/packages/contracts/**`(포트), surface(`ui/packages/surfaces/**`), landing surface(duckdb 는 URL 출처만 레지스트리로).

## 3. 테스트 매트릭스

| 층 | 테스트 | 통과 기준 |
|---|---|---|
| 코어 | `request` 단위(캐시 hit/miss·dedup 동시호출 1 fetch·에러 미캐시·TTL 만료) | 신규 vitest |
| 오리진 | `originUrl` 이 옛 URL 과 바이트 동일(HF·range·워커 env 분기) | 동일성 단위 |
| source 동등성 | **골든 픽스처** — 이관 전/후 반환 객체 동일(대표 회사 005930·035720 등 fixture) | deep-equal |
| 어댑터 conformance | `createFakeRuntime` 가 전 포트 구현(tsc) + fake 코어 | 기존 + 확장 |
| 타입 | `npm run check -w @dartlab/ui-{contracts,runtime,surfaces}` 0 errors | 3 패키지 |
| 가드 | `tests/audit/checkUiDataWiring` — source raw fetch·직접 URL·자체 Map 신규 0 | baseline 대비 증가 0 |
| dev 스모크 | `:8400` off 로 터미널 전 패널 동작(차트·재무·공시·워치·포렌식·공급망) | 수동/플레이라이트 |

## 4. 롤백 전략

- 페이즈·source 단위 커밋 → 문제 단위만 revert.
- 오리진 env 전환은 한 줄(CF↔직결) — 성능 회귀 시 즉시 롤백.
- 코어는 기존 로직 *래퍼* → 동작 회귀는 골든 픽스처가 PR 단계에서 검출.
- 가드는 baseline 부채원장(신규 위반만 fail) → 점진 이관 중 기존 미이관 source 가 CI 를 깨지 않음.

## 5. 이중 평가

**전문 개발자 관점**
- 강점: 죽은 코드(RuntimeCache/RequestDedup) 실배선 = 순이득. 포트 경계 뒤 점진 이관이라 무중단·롤백 쉬움. dedup/TTL 신설이 동시 중복 fetch·세션 누수·stale 3 버그를 구조적으로 제거.
- 위험: ① source 20+ 이관은 길다 → 골든 픽스처 없이는 미묘한 회귀(정렬·dedup 키·필드 매핑) 샘. **완화**: P3 각 source 골든 픽스처 동행, 1개씩. ② 폴더 이동이 import 경로 대량 변경 → **완화**: re-export 다리 + P4 로 분리. ③ duckdb/landing 셸이 origin.ts 직접 의존 → **완화**: re-export 유지, 레지스트리는 추가만.
- 판정: 정공법. 단 "한 번에" 금지, "1개씩 + 픽스처" 강제.

**PM 관점**
- 가치: 신규 데이터 기능의 한계비용↓(request 한 줄), 회귀(이번 세션 같은 오배선) 구조 차단, dev=퍼블릭 보장으로 기여자 온보딩↑.
- 비용/리스크: 사용자 가시 기능 0(내부 리팩토링) → 우선순위는 "기능 사이"에. 다른 세션 surface 작업과 병행 가능(계층 분리). P1·P2 는 추가만이라 저위험 선착수, P3 는 여유 있을 때 source 씩.
- 게이트: 각 페이즈 타입체크 0 + 골든 픽스처 green + dev 스모크. UI 변경 아님(런타임 로직)이라 자동 push 대상이지만, **source 이관은 시각 회귀 0 확인 후**. 최종 판단은 운영자 go.
- 판정: 승인 가치 충분. 단계적·저위험. "끝까지" 보장은 07 progress-ledger 가 세션 간 이어줌.
