# 03. 커맨드바 섹션 점프 + 아키텍처 · 경계

상태: 비전 PRD v0.2
범위: 약화 함수문법(커맨드바 섹션 점프), 아키텍처 거처, 포트 실태(코드 실측), 재사용, ★non-encroachment map(이 PRD 가 *하지 않는* 것), instrument DEFER.

---

## 1. 커맨드바 섹션 점프 (약화 함수문법)

블룸버그식 `005930 FA` mnemonic 백과사전은 리테일 cargo-cult다(01 §3 절제선). 적대검증(C)과 사용자 렌즈(D)가 수렴한 정공법:

- **현재**: `‹GO›` = `eng.search(cmd)` → 종목 점프 *전용*. `eng.suggest()` 자동완성. 검색 후 항상 *기본 뷰*로 떨군다.
- **순증분의 실체** = "검색 후 *어느 섹션으로 점프*". 현 ⌘K 는 회사만 고르고 기본 뷰로 떨굼. **"회사 + 섹션 토큰"** 점프가 진짜 가치(공시뷰어 align 과 동형):
  - 자연어 토큰(한국 리테일 우선): `삼성전자 공급망`, `삼성전자 거버넌스`, `삼성전자 손익`, `삼성전자 자사주` → 회사 `pick` 후 해당 forensic 패널/탭 활성·스크롤.
  - 선택적 짧은 별칭(파워유저): `sc`(공급망)·`g`(거버넌스)·`fin`(재무) 등 한 줌만. **풀 mnemonic 사전 금지**([[feedback_always_check_clutter]] — 키워드규칙 더미 누적은 신호).
- **차별 직조**: 섹션 점프 목적지가 우리 *forensic 자산*(공급망·거버넌스·임원보수·타법인출자 — 블룸버그가 데이터 자체를 안 파는 영역)이라, 흉내가 아니라 *우리 강점의 빠른 주소창*이 된다(00 §3 ③DIG 진입비용 해소).

### ★토큰 → 타깃 매핑 (코드 실측 — "검색 한 겹"이 아니라 선결 식별자 부여)

> 완전성 비평이 잡은 차단 결함: forensic 타깃들이 *서로 다른 3 메커니즘*에 흩어져 있고 **scroll anchor·tab-id 가 0**(RightStack 패널 grep id 0). 즉 점프는 "검색 한 겹"(과소평가)이 아니라 — (1) 타깃마다 안정 식별자 부여 + (2) 액션 결정 + (3) 모호성 규칙이 *선결*이다.

| 토큰(예) | 거처(코드) | 액션 | 안정 식별자 | 모호성 |
|---|---|---|---|---|
| `공급망` | `RightStack.svelte:346` Panel | scroll-to | **신설 필요**(현재 id 0) | 단일 |
| `거버넌스` | `RightStack.svelte:471` Panel **+** `:177` 등급 칩 *2 곳* | scroll-to(Panel) | 신설 필요 | **모호 → Panel 우선** |
| `손익` | `RightStack.svelte:119` 재무탭 `key:'IS'` **+** `FinFullscreen` `FS_TABS key:'profitability'` | activate-tab(RightStack 기본)/openFullscreen(수식어) | 기존 tab key | **모호 → 기본=RightStack IS, ⇧=전체화면** |
| `자사주` | `FinFullscreen` `FS_TABS key:'shareholder'`(`finTabs.ts`) | openFullscreen+activate | 기존 FS_TAB key | 단일 |

- **3 액션 종류**: `scroll-to`(RightStack Panel) · `activate-tab`(RightStack 재무탭/FinFullscreen FS_TAB) · `openFullscreen`(FinFullscreen). 토큰별로 *어느 액션*인지 표가 SSOT.
- **선결 작업 = Phase 2 의 절반**: RightStack 의 forensic Panel 들에 안정 `data-section` id 부여(현재 0) + 토큰 사전(자연어→식별자) + 모호 규칙. "기능은 다 있고 점프 문법만 없음"은 *과소평가* — 식별자 인프라가 없다.
- **정공법 = 기존 `go`/`suggest` 에 "섹션 토큰 → pick 후 위 표의 액션 실행" 인식 한 겹.** 별도 함수 디스패처/문법은 덕지덕지. 풀 mnemonic 사전 금지.

**우선순위 주의**: 섹션 점프는 워치리스트(02)보다 후순위. 식별자 부여 선결비용이 있으나 목적지 데이터는 라이브. 루프를 닫는 핵심은 워치리스트다.

---

## 2. 포트 실태 (코드 실측 — B vs C 논쟁 판정)

토론 중 "포트 계약이 이미 있으니 배선만 하면 됨(싸다)"(B) vs "그건 viewer/scan 표면 얘기고 terminal 엔 없다(환각)"(C)가 충돌했다. 직접 grep 으로 *양쪽 다 부분적으로 맞음*을 확정:

- **계약은 실재(B 맞음)**: `contracts/src/services.ts`(`ServiceGroup` 에 `'workspace'`·`'export'`, `ServiceCommand.shortcut`·`mode`·`executeCommand`/`listCommands`)·`storage.ts`(`terminal.*` 키 합법)·`navigation.ts` 모두 정의됨. `runtime/src/services/serviceRegistry.ts` 의 `createServiceRegistry` + `exportCommand.ts` 가 패턴을 *이미 증명*.
- **★로컬 어댑터는 셋 다 이미 배선됨**: `createLocalRuntime.ts` — `services: createServiceRegistry([exportServiceRegistration(...)])`, `storage: localStoragePort()`, `navigation: options.navigation`(셸 주입). 즉 *로컬에선* 함수문법·워치리스트-via-포트가 **오늘 당장 가능**.
- **단 퍼블릭 미배선 + 터미널 surface 미소비(C 맞음)**: `createPublicRuntime.ts` 는 `services`/`navigation`/`storage` getter 가 전부 `notWiredYet(...)` throw. 그리고 **공유 터미널 surface 는 셋 중 무엇도 소비하지 않는다**(grep 0 — GO 는 raw `<input>`+search, 저장은 raw `localStorage` 4 키 패밀리 `dlTerm.lastSym`·`dlTerm.chart`·`dlTerm.tmpl`·`dlTerm.draw.{code}`). → 즉 같은 surface 가 로컬에선 포트를 쓸 *수* 있으나 아직 raw localStorage 만 쓴다.
- **localStorage 구현체는 이미 존재(단 storage getter 미배선)**: `localStoragePort()` 구현체가 퍼블릭에서 이미 *export* 포트에 소비됨(`createPublicRuntime.ts:161` `export: publicExportPort(localStoragePort(), ...)`) — 즉 구현체는 있으나 `storage` getter 는 여전히 `notWiredYet` throw(`:178`). "storage 가 배선됐다"는 아니고 "*구현체는 있고 storage getter 배선만 단계-4a-3 미완*".
- **정직한 결론**: 함수문법·워치리스트 지속성은 **로컬에선 거의 무료(포트 배선됨)·퍼블릭에선 중간(getter 배선 + surface 소비)**. "신설 아님(계약·레지스트리·예시 커맨드·localStorage 구현체 존재) but 퍼블릭 공짜도 아님". **"배선만 하면 됨"은 퍼블릭 과소평가, "전부 신규 구축"은 과대평가.**

→ 함의: 섹션 점프(1)는 ServicesPort 를 *쓸 수도* 있으나(로컬 배선됨), 본질은 검색 한 겹 확장이라 ServicesPort 를 *강제 의존*하지 않는다(퍼블릭에서도 동작해야). 워치리스트(02)는 StoragePort 정합하되 가치가 의존하지 않는다(퍼블릭 floor = raw localStorage). 2 타깃 차이는 §7.

---

## 3. 아키텍처 거처

- **모든 신설은 `ui/packages/surfaces/src/terminal/`** (라이브 터미널 SSOT — 2026-06 `landing/src/lib/terminal/` → 이관 완료, scenario-simulator 07 §5).
- **워치리스트**: `LeftRail` 신규 패널 + 헤더 ☆ 토글 + `terminal.watchlist` 상태. 데이터 = 가격·재무칩 기존 포트(신규 0) + **공시 신선도 = `dart/allFilings/recent.parquet` cross-company 리더(신규 FilingPort 메서드 1, 02 §5 데이터 계약)**. 신규 데이터셋·인프라 0.
- **섹션 점프**: `TerminalSurface` 의 `go`/`onInput`/`suggest` 확장 + 각 패널의 탭/스크롤 타깃 식별자. 신규 컴포넌트 최소.
- **포트 원칙 정합**(ui-platform-refactor): 새 포트 남발 금지. required·silent fallback 금지·미지원=정직(null/throw). 워치리스트가 StoragePort 를 쓰면 그 배선은 ui-platform-refactor 단계-4a-3 과 한 묶음.

---

## 4. ★Non-encroachment map (이 PRD 가 *하지 않는* 것)

본 PRD 는 우산 *연결* 레이어다. 기존 4 PRD 가 소유한 것을 **재발명·재배선·재명명하지 않는다.** 충돌 시 기존 PRD 가 정본.

| 영역 | 소유 PRD | 본 PRD 의 관계 |
|---|---|---|
| **JUDGE 분석** — reverseDCF(가격함축기대 읽기)·compare(동종 백분위 밴드)·이익품질 forensic·정합성 | **financial-statement-lab** (killer #1/#2, `compare(codes)`·`reverseImpliedGrowth` 엔진) | *연결만.* 워치/섹션점프가 이 뷰로 점프시킬 수 있으나 분석 로직·UI 카드는 그쪽 소유. reverseDCF 를 "함수(`IMP`)"로 승격 = 라벨갈이 KILL(04). |
| **가격↔기초체력 지수 오버레이 · PER/PBR 시계열** — 주가차트 위 매출/영업이익/CFO 리베이스 지수 오버레이, 밸류에이션 멀티플 시계열 | **financial-statement-lab** (00 §5.2, 03 §2 — `gov/prices × panel` NEW 어댑터) | *비범위·경계 명시.* 둘 다 `gov/prices × 터미널 주가차트` 거처라 충돌 소지. 워치 가격은 *행 안 텍스트 수치*(전일대비/1Y)지 *차트 오버레이가 아님*(02 §2 못박음). 차트 위 가격-펀더멘털 오버레이는 그쪽 소유. |
| **시뮬레이션·Play·지수·백테스팅·미래 공시마커** | **scenario-simulator** (11 문서) | *비범위.* Play 미래 리플레이·지수 instrument 시퀀싱·DSR/PBO·ReportDock 은 전부 그쪽. 본 PRD 는 *현재/과거* monitor 만. |
| **공시 이벤트레일** (x 축 공시 위치·marker→우측행 스크롤) | **scenario-simulator 11 / disclosure-event-rail** | *비범위.* 터미널 `CenterStack` 의 `priceEvents`(→ `PriceChart.svelte:33` `events` prop, `report.capitalChanges` 등 공급) 차트 마커 이미 라이브. 재구현 금지. 워치는 카운트만 참조. |
| **테이블 egress** (공시 테이블 → .xlsx) | **table-export** (8 문서, `ExportPort` 배선됨) | *비범위.* ⑤RECORD 끊김은 그쪽이 해소. 워치리스트가 흡수하는 최소 핵심(종목집합 저장)만 본 PRD. |
| **포트 원칙·UI 패키지 경계·작업면 대칭** | **ui-platform-refactor** | *준수.* services/storage 배선은 그쪽 단계와 정합. 신 포트·신 route 남발 금지. |
| **N 사 비교** | **financial-statement-lab** (`compare` verb) | *재발명 금지.* 멀티심볼 보드를 만들면 비교가 두 군데 생겨 SSOT 분열 → 단일 sym 보드 유지가 정합(04). |

---

## 5. instrument / 크로스에셋 — DEFER

- **현황(코드 실측)**: 모든 포트가 `code: string`(종목코드) 키잉. instrument/assetClass 추상 0(grep 확인). 지수·매크로·신용(파생 dCR)·원자재(customs HS)는 *데이터로* 존재하나 navigable instrument 타입 체계 없음.
- **판정**: 풀 instrument 타입 체계 신설은 contracts 전반 개정 = **최대 재발명 위험**. 본 PRD 범위에서 **의도적 보류**. 지수는 scenario-simulator(지수 시퀀싱) 소유. 매크로/지수는 equity 보드에 *오버레이/뷰*로 얹는 선까지만(이미 라이브). instrument 추상화는 *별도 깊은 PRD* 감.

---

## 6. 재발명·덕지덕지 위험 경고 (적대검증 종합)

1. **`services`/`storage` 포트를 "없다"고 신설** — 계약·레지스트리·예시(`exportCommand`)가 실재. 새 커맨드 시스템 클래스 만들면 덕지덕지. 배선 + 소비가 정공법.
2. **StoragePort 우회해 또 raw localStorage 키 증식** — 터미널은 *이미* raw 4 키 패밀리(`dlTerm.lastSym`·`dlTerm.chart`·`dlTerm.tmpl`·`dlTerm.draw.{code}`)로 분열돼 있고, 워치리스트가 *다섯 번째* 키를 더하면 더 깊어진다. `terminal.watchlist` 1 키로 못박고 StoragePort 정합(기존 4 키 이관도 ui-platform-refactor 단계-4a-3 부채).
3. **`seriesBus`/`compareOverlay` 를 링크그룹으로 착각 확장** — 둘 다 *단일 차트 내부* 모듈(오버레이용). 멀티패널 링크그룹이 아니다. 차트 내 멀티심볼 VS 는 이미 있으니 재구현 금지.
4. **공시 이벤트레일 재구현** — 터미널 `CenterStack priceEvents`(→ `PriceChart events` prop) 가 이미 마커화. 재구현 말고(scenario-simulator 소유) 워치 카운트만 참조.
5. **`compare` 엔진 재발명** — fin-stmt-lab 소유. N 사 비교 새로 만들면 충돌.
6. **크로스에셋 instrument 타입 풀 신설** — contracts 전반 개정 = 최대 재발명. DEFER(§5).
7. **reverseDCF→`IMP` 함수 승격** — fin-stmt-lab 소유 로직을 터미널 "함수"로 재명명 = SSOT 분열 + 라벨갈이. 표시만(연결), 소유 이전 금지.

---

## 7. ★로컬 ↔ 퍼블릭 — 2 배포 타깃, 같은 surface (코드 실측)

개선 대상 터미널은 *하나의 공유 컴포넌트* `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` 가 `runtime: DartLabRuntime` prop 으로 주입받아 두 배포에 마운트된다. 즉 워치리스트·섹션점프는 *한 번 만들면 둘 다*에 뜬다 — 단 런타임이 달라 *능력 천장*이 다르다.

| | **퍼블릭** (landing `+page.svelte` → `createPublicRuntime`) | **로컬** (ui/apps/local `+page.svelte` → `createLocalRuntime`) |
|---|---|---|
| 배포 | `adapter-static`(GitHub Pages 전체 prerender) | `adapter-static` + vite dev/preview |
| 데이터 | HF 정적 parquet(CF 워커 프록시) | **`apiBase` `/api` → 로컬 dartlab 서버 :8400**(live 엔진) |
| services/storage/navigation | `notWiredYet()` throw(미배선) | **배선됨**(`createServiceRegistry`·`localStoragePort()`·셸 주입) |
| 지속성 | localStorage(기기종속·시크릿 0) | localStorage(현재) — 백엔드 쓰기 엔드포인트 추가 시 서버측 가능(별도) |
| 알림 푸시·동기화 | **불가**(서버 0) | 백엔드 있으나 *static 프런트*라 푸시·백그라운드 잡은 여전히 없음 |

**★설계 원칙 — 퍼블릭 floor 에 설계, 로컬은 같은 포트로 bonus:**
- 워치리스트·섹션점프는 **퍼블릭 floor**(raw localStorage·HF·포트 미배선)에서 *완전히 동작*하게 설계한다. 퍼블릭이 대다수 사용자(landing = 영구 공개 shell).
- 로컬의 *배선된 포트* + *live 백엔드*는 **같은 코드가 켜는 bonus headroom**이다(예: StoragePort 가 로컬에선 풍부한 store, 퍼블릭에선 localStorage — surface 는 `runtime.storage` 만 호출). **local-only 기능 금지**(ui-platform-refactor "열화 UX 숨김 금지·port required·silent fallback 금지").
- 따라서 "퍼블릭 서버 0 → 푸시 불가"(02 §6)는 **floor 의 정직 한계**지 로컬을 부정하는 게 아니다. 로컬 백엔드로 *진짜 모니터/알림*을 켤지는 — static 프런트라 여전히 푸시 불가 + local-only 위험 — **별도 판단 항목**(06 NEXT)이고 본 PRD 는 floor 에 설계한다.
- 데이터 천장도 다름: 로컬은 live dartlab(custom compute) vs 퍼블릭 precomputed HF. 단 이는 *분석 tier*(fin-stmt-lab·simulate 소유)이지 본 PRD(워치/모니터)의 범위 아님 — 워치리스트는 *양쪽 다 있는* price·filing·report 포트만 쓴다.
