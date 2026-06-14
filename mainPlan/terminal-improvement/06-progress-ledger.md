# 06. 진행 원장 — 결정 · 토론 기록 · NEXT

상태: 비전 PRD v0.2 (2026-06-14)
범위: 결정 SSOT, 전문에이전트 토론 기록, 문서 상태, NEXT, 착수 게이트.

> v0.2 정정(운영자 피드백): ① "터미널 OS 레이어" 프레이밍 폐기 → **기존 터미널 개선**("OS"는 *새 걸 짓는다*처럼 과장, 폴더 `terminal-os`→`terminal-improvement`). ② 로컬/퍼블릭 2 배포 타깃 정정 — "서버리스" 제약은 *퍼블릭 전용*(로컬은 :8400 백엔드·포트 배선됨), 같은 공유 surface 라 퍼블릭 floor 에 설계·로컬 bonus(03 §7).

---

## 1. 핵심 결정 (확정)

1. **"블룸버그식" = 분석들을 묶는 수평 층, 수직 분석 아님.** dartlab 은 비싼 절반(분석)을 이미 초과 수준으로 끝냈고 싼 절반(수평 직조)을 비웠다 — 이 묶는 층 개선 ROI 가 높다. (이건 *기존 터미널 개선*이지 새 제품·새 추상 아님.)
2. **이 PRD 의 고유 신설 = 워치리스트(공시 워치) 1 개.** 어떤 기존 PRD 도 미claim(코드·PRD grep 0). 가격 워치가 아니라 *공시 델타*가 우리 사용자·우리 데이터·우리 제약에 맞는 유일한 monitor.
3. **함수문법은 *약화*(섹션 점프)로만.** 풀 mnemonic 백과사전 KILL.
4. **알림 = 정직 한정 생존.** 푸시 KILL(서버 0). 기기독립 신선도(Tier 1)가 핵심, 재방문 델타(Tier 2)는 완결성 주장 금지·기기/시점 명시로만.
5. **멀티패널 Launchpad·멀티심볼·reverseDCF 함수승격·크로스에셋 instrument = KILL/DEFER.** 구역규칙·cargo-cult·기존 PRD 소유권·재발명 위험.
6. **본 PRD 는 *연결* 레이어** — JUDGE(fin-stmt-lab)·시뮬(scenario-simulator)·egress(table-export)·포트(ui-platform-refactor)를 claim 하지 않고 monitor 루프로 묶는다.

---

## 2. 전문에이전트 토론 기록 (방향을 박은 근거)

4 렌즈 토론(2 웨이브, OOM 가드로 병렬 ≤ 2) + 운영자(메인) 코드 실측 검증:

- **Wave 1-A (블룸버그 개념지도)**: 블룸버그 = *분석들을 묶는 수평 층* 가설 강하게 지지. dartlab 은 분석 초과·묶는 층 빈약. Top 7 빠진 원시요소 + 포기선(실시간·컨센서스·풀 런치패드). 절제선 = Koyfin/TIKR.
- **Wave 1-B (자산·아키텍처 감사)**: ★`services`/`storage`/`navigation` 포트 계약 실재 but 미배선. 터미널은 단일 `sym`·raw localStorage. 멀티패널만 진짜 신규, 크로스에셋 DEFER 권고. 기존 PRD 커버리지 맵.
- **Wave 2-C (적대검증/덕지덕지 사냥)**: 무자비 KILL. "포트 배선만=싸다"는 *터미널 트리엔 포트 소비 0* 이라 반박. 알림 KILL(확신오정렬), 멀티패널 KILL(구역규칙), 함수문법 DE-SCOPE, reverseDCF KILL(라벨갈이). **최소집합 = 워치리스트 1 개.**
- **Wave 2-D (사용자 워크플로·차별화)**: monitor 루프 5 단계(WATCH→SURFACE→DIG→JUDGE→RECORD), ③DIG 만 완성·①②비어 루프 안 닫힘. ★"공시 워치 ≠ 가격 워치"가 우리만의 monitor. reverseDCF 엔진 실재·미배선 발견(단 fin-stmt-lab 소유).
- **운영자 코드 실측 판정**: (a) landing = adapter-static·백엔드 0·인증 0 → 푸시·동기화 불가 확정. (b) 포트 계약 실재(B 맞음) but public 어댑터 `notWiredYet` throw + 터미널 미소비(C 맞음) → "신설 아님 but 공짜도 아님". (c) `reverseImpliedGrowth` 엔진 실재(D 맞음). (d) 워치리스트 미claim·reverseDCF/compare = fin-stmt-lab killer #1/#2 소유 확정 → non-encroachment map.

**C vs D 핵심 충돌 해소**: 알림은 *기기독립 신선도(Tier 1) 핵심 + 정직 라벨 재방문 델타(Tier 2) 선택*으로 분리 — D 의 killer 가치를 C 의 확신오정렬 위험 없이 흡수. reverseDCF 는 *표시(연결)하되 함수승격 안 함* — D 의 surfacing 가치 + C 의 라벨갈이 KILL 양립.

**Wave 3 — 완전성 비평(v0.2 "완벽 완성" 라운드, 운영자 코드 실측 동반)**: ★차단 결함 3 + 누락 개념 1 + 사실 정밀화 2 를 정정.
- **C1(완성 차단·정확성 정정 — "치명" 아님)**: 워치리스트 데이터 계약이 비어 있었고 "신규 포트 0" 주장이 *틀림*. 단 *방향 오류가 아니라* 내 비용 주장의 정확성 결함 — 방향(공시 워치)은 무관하게 섬. `FilingPort.regular/nonRegular` = per-code, `syncStatus` = 데이터셋 경로 단위 → 회사별 공시 델타를 *포트로* 못 잼. → 02 §5 데이터 계약 신설·"신규 포트 0" 철회.
- **C2(차단, 정정)**: 섹션 점프 타깃이 *주소 불가능*(RightStack 패널 id 0) + 3 메커니즘 분산 + 모호(손익=RightStack IS vs FinFullscreen). → 03 §1 토큰→타깃 매핑표 + 식별자 부여 = Phase 2 절반.
- **C3(차단, 정정)**: Phase AC 가 추상적 → 05 §1 정량 AC(워치 30 사 fetch ≤ 1·DOM "알림" 문자열 0 등).
- **누락 개념(정정)**: `recentCompanies`(전역 계약 키 기존재·ui/web 사용) 미언급 → 02 §7 경계(자동 이력 ≠ 수동 큐레이션, 흡수 안 함).
- **사실 정밀화**: W1 `priceEvents` = 터미널 CenterStack 실재(비평 과오류) → PriceChart `events` prop 정밀화. W2 `localStoragePort()` = export 포트 소비지 storage 배선 아님 → 명확화.

**Wave 4 — 최종 결함 확인 + 완성도(운영자 직접 코드 적대 검증, 전문에이전트 rate-limit 로 인라인 수행)**:
- **C1 재검증으로 갭이 *더 작아짐***: `nonRegularFilingsSource.ts:35-37` 가 이미 `dart/allFilings/recent.parquet` 를 `readParquetRows({filter:{stock_code:{$in:[code]}}})`(배열 `$in`·row-group pushdown·컬럼 `rcept_dt`) 로 읽는다 → cross-company 읽기 *능력은 소스에 이미 존재*, 결손은 *공개 포트의 다중코드 메서드 표면*뿐(얇은 래퍼). 02 §5 정밀화. "치명" 아님 재확인.
- **C2 토큰표 라인 전수 검증 통과**: RightStack `:177`(거버넌스 칩)·`:346`(공급망 Panel)·`:471`(거버넌스 Panel — 모호성 실재)·finTabs FS_TABS `profitability`/`shareholder` 모두 실측 일치.
- **완성도 자평(5 축 ×20)**: 방향 건전성 19 / 주장 정확성 18(C1 정밀화로 상향) / 경계 명확성 19 / 정직성 20 / 착수 가능성 17(신규 포트 메서드 시그니처는 구현 시 확정) = **93/100**. 착수 임계(≥85) 충족 — *재조사 없이 Phase 0 착수 가능*. 잔여 −7 = 포트 메서드 정확 시그니처·toc별 식별자 부여(Phase 2 선결)는 *의도적으로 구현 단계 결정*으로 남김(vision PRD 적정 깊이).

---

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README | v0.2 — "기존 터미널 개선" 틀(추가할 개념 A + 박을 개념 B)·로컬/퍼블릭·문서지도·정직척추 |
| 00-product-vision | v0.2 — 문제(묶는 층 결손)·사용자·monitor 루프·공시워치≠가격워치·ROI |
| 01-bloomberg-concept-gap | v0.2 — 원시요소 카탈로그·"묶는 층 vs 분석" 가설·리테일 절제선 |
| 02-watchlist-disclosure-watch | v0.2 — ★핵심. 3 층·정직 가드·storage 계약·**§5 데이터 계약**·거처·비목표(recentCompanies 경계) |
| 03-command-and-architecture | v0.2 — 섹션점프(**토큰 매핑표**)·포트 실태(로컬/퍼블릭)·non-encroachment·instrument DEFER·§7 2 타깃 |
| 04-killlist-and-non-goals | v0.2 — KILL/DEFER 판정표·정체성 가드·덕지덕지 차단 |
| 05-scope-phasing-guardrails | v0.2 — Phase 0-3·**정량 AC**·정직 가드·성공기준·착수 게이트 |
| 06-progress-ledger | v0.2 — 본 문서 |

---

## 4. NEXT (다음 세션이 닫을 것)

- [ ] **운영자 리뷰** — 방향(공시 워치 = monitor 핵심, 나머지 KILL/DEFER)에 대한 운영자 승인 또는 정정.
- [x] **메모리 포인터 등록** — `MEMORY.md` §6.2 `[[project_terminal_improvement]]`(PRD 경로=`mainPlan/terminal-improvement/`, 옛 `project_terminal_os_layer` 폐기).
- [ ] **(승인 시) Phase 0 선행 가능성 확인** — 워치리스트 Tier 0 가 raw localStorage 로 mainPlan 무관 선행 가능한지 ui-platform-refactor 진척과 1 회 정합 확인.
- [ ] **★로컬 백엔드 모니터 판단(별도)** — 로컬(:8400 백엔드)에서 *진짜 모니터/알림*(서버측 평가·저장)을 켤지. 단 static 프런트라 푸시는 여전히 불가 + local-only 위험. 본 PRD 는 퍼블릭 floor 에 설계하고 이건 *후속 판단*으로 분리(03 §7).
- [ ] **fin-stmt-lab 경계 1 회 동기화** — (a) 워치/섹션점프가 reverseDCF·compare 뷰로 *점프*시키는 접점, (b) ★워치 가격 보조컬럼 ↔ fin-stmt-lab "가격↔기초체력 지수 오버레이·PER/PBR 시계열"(둘 다 `gov/prices × 주가차트` 거처) 충돌 점검 — 워치 가격은 *행 텍스트*지 *차트 오버레이 아님* 경계 재확인. 소유는 fin-stmt-lab.
- [ ] **(StoragePort 정합) 기존 raw 4 키 이관 부채 인지** — 워치리스트는 `terminal.watchlist` 1 키로, 기존 4 raw 키(`dlTerm.*`) StoragePort 이관은 ui-platform-refactor 단계-4a-3 범위로 위임.

---

## 5. 착수 게이트

- **코딩 아님** — 방향 확정 문서. 착수 = mainPlan(ui/packages 정착, 이미 이관) + **운영자 go** 후.
- **충돌 시 기존 4 PRD 가 정본**, 본 PRD 는 연결 레이어로서 양보.
