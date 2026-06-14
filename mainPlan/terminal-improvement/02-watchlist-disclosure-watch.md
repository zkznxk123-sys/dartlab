# 02. ★워치리스트 = 공시 워치 (핵심 새 원시요소)

상태: 비전 PRD v0.2
범위: 본 PRD 가 신설하는 단 하나의 원시요소. 사용자 큐레이션 종목 집합 + 기기독립 신선도 + 정직 라벨 재방문 델타. storage 계약·거처·비목표.

> 이것만이 본 PRD 가 *신설*한다. 다른 모든 후보(워크스페이스·함수 디스패처·reverseDCF·egress·instrument)는 KILL/DEFER 거나 기존 PRD 소유다(03·04). **강함은 7 을 1 로 깎아서 온다.**

---

## 1. 왜 이것만 정당한가

블룸버그의 묶는 층(수평 개념) 후보 중 우리 제약(퍼블릭 정적 호스팅·서버 0·계정 0·EOD·컨센서스 0)을 *온전히* 견디는 유일 원시요소:

- **정적 데이터로 충분** — EOD 가격·기존 공시 parquet 이 이미 라이브. 신규 데이터 파이프라인 0.
- **서버 불필요** — localStorage 로 충분(터미널은 이미 raw localStorage 4 키 패밀리 `dlTerm.lastSym`·`dlTerm.chart`·`dlTerm.tmpl`·`dlTerm.draw.{code}` 로 같은 패턴 가동 중 — 신규 인프라·데이터셋 0, 신규 포트 메서드 1[§5]).
- **불가침 구역규칙 무위반** — `LeftRail` 은 이미 종목 목록 표면(스크리너·히트맵). 워치리스트가 자연 안착.
- **루프를 닫음** — 00 §3 의 비어 있는 ①WATCH·②SURFACE 를 직접 해소. 사용자에게 *재방문 이유*를 만드는 유일한 레버.
- **우리 강점에 베팅** — 가격 실시간(우리 0)이 아니라 공시 델타(우리 압도적)에. 약점을 피하고 강점에 건다.

---

## 2. 3 층 구조 (정직성 등급순으로 쌓는다)

워치리스트를 정직성 위험이 *낮은 층부터* 쌓는다. 각 층은 독립 출시 가능하며, 위 층 없이도 아래 층이 완결된다.

### Tier 0 — 큐레이션 종목 집합 (SAFE · 즉시)
- 사용자가 "내 회사들"(목표 10~30, 상한 없음)을 추가/제거. `LeftRail` 에 워치리스트 패널(스크리너·히트맵과 동급 표면). 각 행 = 회사명 + 30 거래일 스파크 + 전일대비/1Y(이미 `recent.parquet`·`priceOf` 라이브, 추가 다운로드 0) + 재무유형 칩(`finType`).
- 추가 진입점: GO 검색 결과·스크리너 행·헤더에 ☆ 토글.
- 정직성 위험 0 — 순수 사용자 큐레이션 상태. 완결성 주장 없음.

### Tier 1 — 기기독립 *절대시간* 신선도 배지 (SAFE · 위험 0)
- 각 워치 행에 **공시 발생일 기준 *절대시간*** 신선도 배지: "최근 7 일 신규", "30 일 N 건". 기준점은 *현재 시각(절대 캘린더)* 이지 "마지막 방문"이 아니다 — 데이터는 `RegularFiling`·`NonRegularFiling`·`report` parquet 의 접수일/발생일, **"마지막 방문" 상태가 전혀 필요 없다.** 100% 기기독립·정직.
- 이게 killer 가치의 *위험 0 부분*을 전달한다: 워치리스트를 열면 최근 공시가 있는 회사가 자연 강조된다. **단 이것은 ②SURFACE("마지막 본 시점 이후 신규")의 *근사*지 *완성*이 아니다** — "내가 마지막으로 본 이후"라는 진짜 재방문 델타는 정직성 위험이 있는 Tier 2 에만 있다(§아래). Tier 1 은 "절대시간 신선도", Tier 2 는 "재방문 델타" — 서로 다른 능력이다.
- 정렬: "최근 신규 공시" 우선(monitor 답게) — 단 사용자 토글로 1Y/이름 정렬 전환 가능.

### Tier 2 — 재방문 델타 다이제스트 (정직 한정 · 선택)
- localStorage 에 워치별(또는 회사별) "이 기기에서 마지막 렌더 시점" 타임스탬프를 저장. 재방문 시 *그 시점 이후* 신규 공시·재무 panel 갱신을 델타로 표시: "이 기기 · 마지막 방문 06-12 14:30 이후 신규 3 건".
- **반드시 다음 정직 가드를 단다(아래 §3):** 완결성 주장 금지, 기기·시점 명시, "알림"이라는 단어 금지.
- 가격 델타도 같은 메커니즘으로 *공짜로* 끼운다 — 단 공시가 헤드라인, 가격은 *보조 컬럼*("마지막 본 가격 → 현재 EOD"). 가격을 *버리는* 게 아니라 *종속*시킨다. **이 가격 보조컬럼은 행 안의 *텍스트 수치*(전일대비/1Y/델타)지 차트 위 오버레이가 아니다** — 주가차트 위 "가격↔기초체력 지수 오버레이"는 financial-statement-lab 소유(03 §4 경계), 워치는 그 영역을 침범하지 않는다.

---

## 3. ★정직 가드 (Tier 2 의 생존 조건 — 적대검증 합의)

적대 에이전트(C)는 "푸시 못 하는 알림은 알림이 아니고, localStorage 단일이라 '지난 방문'조차 신뢰 불가 → 틀린 알림 > 알림 없음(확신오정렬 > 정렬실패)"이라 Tier 2 를 통째로 KILL 주장했다. 사용자 렌즈(D)는 "정직 라벨을 달면 *측정값*이지 거짓 약속이 아니다"라 반박했다. **합의: Tier 1(기기독립)이 가치의 대부분을 위험 0 으로 전달하므로 핵심이고, Tier 2 는 *아래 가드를 전부 만족할 때만* 산다.**

- **완결성 주장 금지.** "다 봤음"·"신규 없음"·"모두 확인" 같은 *완결* 진술 절대 금지. 상태가 기기로컬이라 다른 기기에서 봤으면 거짓. "이 기기에서 마지막 렌더 06-12 이후 *이 fetch 에서* 신규 N 건"처럼 *측정 범위*만 진술.
- **기기·시점 명시.** "이 기기 기준 · 마지막 방문 {timestamp}" 를 배지 옆에 *항상* 노출. 크로스기기 동기화 불가를 숨기지 않는다.
- **"알림" 단어 금지.** UI 문구는 "재방문 델타"·"마지막 방문 이후"·"신선도"만. "알림"·"notification"·"푸시"는 못 지킬 약속이라 금지.
- **공시 = 정본, 워치는 카운트 참조만.** 신규 공시 *목록/원문*은 공시 레일·뷰어가 정본(disclosure-event-rail). 워치리스트는 *카운트와 점프 링크*만 — 공시 데이터를 두 군데서 관리하지 않는다(이중관리 차단).
- **localStorage 1 키.** 워치리스트는 `terminal.watchlist`(또는 `dlTerm.watch`) *한 키*에 못박는다. 타임스탬프는 그 안의 필드로(별도 키·읽음표시·diff 엔진 신설 금지). SSOT 분열 원천차단.

---

## 4. storage 계약 (코드 실측 기반)

- contracts 에 `storage.ts` 실재: `RuntimeStorageKey = `${DartLabSurfaceId}.${string}` | GlobalStorageKey`, `DartLabSurfaceId` 에 `'terminal'` 포함 → **`'terminal.watchlist'` 키가 계약상 합법**(주석에 `terminal.chartState`·`terminal.backtestConfig`·`viewer.layout` 예시 명시).
- **로컬 어댑터(`createLocalRuntime.ts`)는 `storage: localStoragePort()` 로 이미 배선** — 로컬에선 StoragePort 가 오늘 동작. 단 퍼블릭 어댑터(`createPublicRuntime.ts`)는 `storage` getter 가 `notWiredYet('storage','단계-4a-3')` throw, 그리고 **공유 터미널 surface 는 현재 StoragePort 를 소비하지 않는다**(raw localStorage 직접 — 4 키 패밀리). → 03 §2·§7. **localStorage 포트 *구현체*(`localStoragePort()`)는 퍼블릭에서도 이미 export 포트에 배선됨**(`createPublicRuntime.ts:161`) — 퍼블릭 `storage` getter 만 게이트라 "거의 다 된" 중간 비용이지 신규 구축이 아니다.
- **정공법 = StoragePort 배선에 정합**(ui-platform-refactor 단계-4a-3 이 이미 storage 주입 예정). 터미널은 *이미* raw localStorage 4 키 패밀리(`dlTerm.lastSym`·`dlTerm.chart`·`dlTerm.tmpl`·`dlTerm.draw.{code}`)로 분열돼 있고, 워치리스트가 *다섯 번째* raw 키를 더하면 분열이 깊어진다 → StoragePort 경유가 옳다(기존 4 키의 StoragePort 이관도 ui-platform-refactor 단계-4a-3 의 미해결 부채임을 함께 기록).
- **단 워치리스트 *가치*는 StoragePort 에 의존하지 않는다** — Tier 0/1 은 raw localStorage(현 패턴)로 선출시 *가능*하다. ⚠그러나 raw 선출시는 *다섯 번째 키를 늘리는 부채*라, ui-platform-refactor 가 raw localStorage 청산·port required 를 결정한 방향과 역행한다. **단계-4a-3 이 임박했다면 raw 선출시를 건너뛰고 StoragePort 를 기다리는 게 정합** — 선출시 여부는 단계-4a-3 진척과 1 회 정합 확인 후 결정(06 NEXT). "의존 순서 강제 안 함"을 *무조건 raw 허용*으로 읽지 말 것.

---

## 5. ★데이터 계약 (코드 실측 — 공시 델타를 *어느 포트로* 재나)

> 완전성 비평이 잡은 차단 결함: "데이터는 전부 기존 포트"라는 초안 주장은 *작동하지 않는 조합*이었다. 공시 델타의 실제 계산 경로를 못박고, "신규 포트 0"을 **정직하게 철회**한다.

**왜 기존 *포트*로 안 되나 — 단 능력은 이미 *소스*에 있다 (코드 실측):**
- 공개 `FilingPort.regular(code, limit?)`·`nonRegular(code, limit?)`(`contracts/src/filing.ts:79·81`)는 **per-company**(code 인자 필수). 즉 포트엔 *다중코드* 메서드가 없다 → 워치 N 사를 회사당 호출 = N 회.
- **그러나 그 아래 소스는 이미 cross-company 파일을 읽는다**: `nonRegularFilingsSource.ts:35-37` 가 `dart/allFilings/recent.parquet`(전종목 통합 1 파일)를 `readParquetRows({ filter: { stock_code: { $in: [code] } } })` 로 읽는다 — **배열 `$in` 필터 + stock_code 정렬 row-group pushdown**(파일 sorted, 회사 row-group 만 읽음·per-code 캐시). 컬럼 = `stock_code`·**`rcept_dt`**·`report_nm`·`rcept_no`·`flr_nm`.
- 정정: 따라서 "회사당 풀다운로드"가 아니라 *회사당 필터 read*(N 회). 진짜 결손은 **포트에 다중코드 변형이 없다**는 것 — `$in: [code]` 를 `$in: [watchCodes]` 로 한 read 에 묶는 메서드가 공개 포트에 없다.
- `syncStatus.fetchLastSync(dir, file?)`(`lib/syncStatus.ts:17`)는 **데이터셋 경로 단위**(HF dir/file 의 마지막 push)지 *회사별*이 아니다 → "이 회사에 최근 공시"를 못 잰다(워치 신선도에 부적합).
- `report.*`는 **연 단위 시계열**(`WorkforceYear[]` 등)이지 *날짜 찍힌 공시 이벤트*가 아니다 → "최근 7 일 신규"를 못 만든다.

**진짜 데이터 경로:**
| 워치 행 요소 | 소스 | 포트 | 신규? |
|---|---|---|---|
| 가격(전일대비/1Y·30 거래일 스파크) | `gov/prices/recent.parquet`(전종목 1 파일) | `priceOf`·`govRecent`(기존) | 0 |
| 재무유형 칩 | finance bundle(기존 캐시) | `finType`(기존) | 0 |
| **Tier 1 신선도("최근 N 일 신규 N 건")** | **`dart/allFilings/recent.parquet`**(전종목 최근 공시 1 파일·EOD, `SourcesModal.svelte:46`·`nonRegularFilingsSource.ts` 실재) | **★신규 FilingPort *다중코드* 메서드**(예: `recentForCodes(codes[])` — 기존 `readParquetRows({filter:{stock_code:{$in:[…]}}})` 재사용) | **1 메서드(얇은 래퍼)** |
| **Tier 2 재방문 델타** | 위 allFilings + localStorage 방문 timestamp | 위 메서드 + 클라 필터(`rcept_dt` > lastVisit) | 0(메서드 재사용) |

- **계산 필드 = `rcept_dt`(접수일, 소스가 `rceptDate` 로 매핑).** "최근 N 일" = `현재시각 − rcept_dt ≤ N`(절대시간, 기기독립). Tier 2 델타 = `rcept_dt > 이 기기 마지막 방문 timestamp`(기기종속, 정직 가드 §3).
- **per-company `nonRegular(code)` N 회 = 기각**(N 필터 read). `$in: [watchCodes]` 한 read 가 정공법(워치 30 사를 한 번에).

**★정직한 포트 회계(초안 "신규 포트 0" 철회 — 단 v0.2 가 본 것보다도 갭이 작다):**
- **신규 데이터셋 0**·**신규 인프라 0**·**신규 데이터 접근 패턴 0**(cross-company `$in` 필터 read 는 `nonRegularFilingsSource` 가 이미 사용 중)·가격/큐레이션/재무칩 신규 0.
- **신규 = 공개 FilingPort 의 *다중코드 메서드* 1 개**(기존 단건 `nonRegular(code)` 를 `$in:[codes]` 로 묶는 얇은 래퍼). 능력은 소스에 이미 있고 *포트 표면*만 없다. ROI 논거("싼 절반")는 유지되되 "공짜"가 아니라 "거의 공짜(포트 표면 1 메서드)"로 정정(00 §5).

---

## 6. 거처 (불가침 구역규칙 준수)

- **`LeftRail`**(좌측 = 네비/목록/이동) — 워치리스트 패널이 스크리너·히트맵과 동급으로 자연 안착. 구역규칙 무위반(그래프 아님·테이블/목록).
- **헤더 ☆ 토글** — 현재 종목을 워치에 추가/제거(`TerminalSurface` 헤더, `pick`/`sym` 인접).
- **데이터** — §5 데이터 계약 참조: 가격·재무칩 = 기존 포트(신규 0), 공시 신선도 = `dart/allFilings/recent.parquet` cross-company 리더(신규 포트 메서드 1). 신규 데이터셋·인프라 0.
- **상태** — `terminal.watchlist` 단일 키(StoragePort 또는 raw localStorage). 추가 상태 0.

---

## 7. 비목표 (이 원시요소가 *되지 않는* 것)

- ❌ **푸시 알림.** 서버·푸시 인프라 0(정적 호스팅 코드 확인). 불가능한 약속.
- ❌ **크로스기기 동기화.** 계정·서버 0. localStorage 는 기기종속·시크릿모드 0·캐시삭제 소실. *정직하게 노출*(§3), 숨기지 않는다.
- ❌ **실시간 가격 워치.** EOD 0. 가격은 *보조 컬럼*으로만 종속, 헤드라인은 공시(00 §4).
- ❌ **포트폴리오/보유·손익 추적.** 매매·보유 개념 없음(우리는 거래소 아님). 워치리스트는 *관심* 집합이지 *보유* 집합이 아니다.
- ❌ **신규 공시 *목록/원문* 재구현.** 공시 레일·뷰어가 정본. 워치는 카운트+점프만.
- ❌ **다조건 저장 스크리너.** 스크리너는 별도(`ScreenerModal`). 워치리스트는 *수동 큐레이션*이지 *조건 저장*이 아니다(혼동 시 덕지덕지).
- ❌ **`recentCompanies`(자동 최근 본 이력) 흡수.** ★중요 경계: contracts 에 **전역 키 `recentCompanies` 가 이미 존재**(`storage.ts:6` `GlobalStorageKey`)하고 `ui/web AppSidebar` 가 사용 중(`useRecentCompanies`). 이건 *자동 최근 이력*이고 워치리스트는 *수동 큐레이션 관심 집합* — **다른 능력이다.** 워치리스트는 최근 본 회사를 *자동 추가하지 않는다*(자동 추가 = 큐레이션 정체성 오염, §6 거처 ☆ 수동 토글만). recentCompanies 는 별 능력(전역 키 기존재)이라 본 PRD 워치리스트가 흡수·재구현 안 한다. 둘을 같은 패널에 섞지 말 것.

---

## 8. 한 줄 종합

워치리스트를 **공시 워치**로 정의하고, 정직성 위험이 낮은 층부터(Tier 0 큐레이션 → Tier 1 기기독립 신선도 → Tier 2 정직 라벨 재방문 델타) 쌓는다. 데이터·상태·거처가 거의 다 기존 자산(신규 인프라·데이터셋 0, 공시 신선도 리더 포트 메서드 1 뿐)이라 싸게 비어 있던 monitor 루프를 닫아 터미널의 재방문 이유를 만든다. "알림"이 아니라 "재방문 델타", 완결성 주장 금지가 생존 조건이다.
