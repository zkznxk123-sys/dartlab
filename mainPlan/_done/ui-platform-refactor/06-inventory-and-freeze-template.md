# 06. Inventory and Freeze Template

상태: v2 확정 기준 문서 (개정 이력은 07 원장)  
범위: 착수 전 작성할 inventory, freeze, 단계 완료 기록 템플릿

---

## 1. Freeze 체크리스트

리팩토링 첫 작업 단위를 시작하기 전에 아래 표를 채운다.

```text
작업 기준 기준선: v0.10.7 (2026-06-13 단계-0에서 실측 기입)
작업 기준 commit: e3e296bd5 (tag v0.10.7 — publish 수정 커밋. 이후 master에는 mainPlan 문서 커밋만 얹힘)
PyPI version: 0.10.7 (pyproject = tag = CHANGELOG 최상단 3자 일치)
PyPI 업로드 시간: 2026-06-12 18:09Z (publish run 27432180934 success — 1차 27427531012 failure 후 재발행)
릴리스 tag: v0.10.7
릴리스 검증 담당: 운영자 (publish 워크플로 success 기반 판정 — PyPI 페이지 직접 조회는 미수행)
열린 작업 세션: site-signals 세션 1 (landing/src/{lib,routes} site-signals 4 dirs untracked)
세션별 종료 확인: 미완 — 단계-1a 착수 전 종료 또는 lockfile·landing 설정 파일 비충돌 확인 필요
남은 dirty file: landing/static/{llms.txt,sitemap.xml} (M) + site-signals 4 dirs (??)
dirty file 소유자: llms/sitemap = postbuild.js 재생성 부산물(타 세션 로컬 빌드) / site-signals = 타 세션
dirty file 처리 방식: 보존 (리팩토링 파일과 무겹침 — 단계-1a의 landing/package-lock.json·vite.config.ts와는 site-signals 세션 종료 후 재확인)
landing 현재 build 상태: green 추정 (최근 Pages 배포·로컬 postbuild 부산물 존재) — 단계-1a 직전 재검증
local UI 현재 build 상태 (ui/web 단독 npm ci + build 재현): green (publish run 27432180934에서 npm ci + vite build 성공)
Python package 현재 상태: 0.10.7 발행 완료·wheel smoke green
rollback 기준 commit: tag v0.10.7 (e3e296bd5)
ui/node_modules·ui/build 스트레이 처분: 삭제 결정 (둘 다 gitignored 고아 — node_modules=2026-04-04 stale 169폴더, build=옛 "DartLab AI" 웹챗 SPA 2026-04-03. 집행=단계-1a)
node_modules OneDrive 동기화 제외 확인: 미확인 — 단계-1a 검증 항목
```

기간 중 재기록 규칙: 리팩토링 기간 중 제품 릴리스가 발생하면 freeze 기준 commit/tag를 07 원장에 재기록하는 entry를 남긴다. 단계 진행 중이면 해당 작업 단위 완료 후에만 재기록한다.

통과 조건:

1. `master` 기준으로 PyPI에 배포된 commit이 명확하다.
2. `git status`의 모든 변경이 분류되어 있다.
3. 다른 세션이 건드리는 파일과 UI 리팩토링 파일이 겹치지 않는다.
4. user-facing release note가 작성되어 있다.
5. `landing` build가 현재 기준으로 green이다.
6. 로컬 UI와 Python package의 현재 정상 상태가 기록되어 있다.

---

## 2. Dirty File 감사표

| 파일 | 현재 상태 | 소유자/세션 | 리팩토링 영향 | 처리 방식 | 완료 확인 |
|---|---|---|---|---|---|
| landing/static/llms.txt · sitemap.xml | modified | postbuild.js 부산물(타 세션 로컬 빌드) | 무관 | 보류(해당 세션 커밋 대기) | 2026-06-13 단계-0 |
| landing/src/lib/components/siteSignals · lib/siteSignals · routes/site-signals · static/site-signals | untracked | site-signals 타 세션 | 무관(단 단계-1a lockfile과 시점 협의) | 보류 | 2026-06-13 단계-0 |

규칙:

- 소유자가 불명확한 변경은 건드리지 않는다.
- 리팩토링 파일과 겹치면 작업 단위를 시작하지 않는다.
- 기존 변경을 되돌리지 않는다.

---

## 3. Current App Inventory

| 앱 | 현재 역할 | build 명령 | 산출물 | 배포/패키징 경로 | 유지/이동/제거 |
|---|---|---|---|---|---|
| landing | public content + product UI | pre(checkDevIsolation·syncBrand·syncBlogAssets) → `node --max-old-space-size=8192 vite build` → post(postbuild.js: docs/blog 미러·llms.txt·sitemap) | landing/build/ | GitHub Pages (deploy-landing.yml: HF seed → `BASE_PATH=/dartlab npm run build`) | 유지 — 영구 public shell (원본은 packages로 승격) |
| ui/web | local React legacy | `tsc -b && vite build` (CI는 `npx vite build`만 — landing `npm ci` 선행 필수: cross-package import가 svelte-kit sync tsconfig 요구) | ui/web/build/ | publish.yml: `cp -r ui/web/build/* src/dartlab/ui/build/` → wheel → PyPI | 제자리 동결 → fallback 후 제거 (물리 이동 금지) |
| ui/apps/local | new local SvelteKit | (단계-5 신설 — landing과 동일 vite 8 계열) | ui/apps/local/build/ | wheel UI build (단계-10에서 publish.yml 전환) | 신규 |
| ui/shared | 무소속 공유 코드 (실측: chart 15 + api 3 + markdown 2 = 20파일) | — | — | 없음 — 실 import 0 실측(2026-06-13). 단 Skill OS viz 계약(`specs/engines/viz/SKILL.md:198`)이 ChartRenderer 경로를 정본으로 참조 + 산출물 JSON 5종 복제 | 처분 권고: api·markdown 폐기, chart는 viz SKILL.md·산출물 JSON·alias 3곳 동시 갱신 조건부 — 운영자 결정, 집행=단계-8 |

> `ui/apps/public`은 비채택(01 §3.2) — 표에서 제외.

---

## 4. Public Route Inventory

| route | 현재 owner | 사용자 영향 | 새 owner | 전환 방식 | smoke 필요 | 무중단 기준 |
|---|---|---|---|---|---|---|
| / | landing | 높음 | landing | 유지 | yes | 200 + metadata |
| /blog/* · /docs/* · /about · /skills/* | landing(콘텐츠) | 높음 | landing | 유지 | yes | 200 |
| /terminal/* | landing/product | 높음 | landing wrapper + surface | wrapper 후 전환 | yes | no 404 |
| /viewer/* | landing/product | 높음 | landing wrapper + surface | wrapper 후 전환 | yes | no blank |
| /scan · /screener | landing/product | 높음 | landing wrapper + ScanSurface | 단계-8 | yes | no blank |
| /map · /industry/* | landing/product | 높음 | landing wrapper + MapSurface | 단계-8 | yes | prerender 보존 |
| /compare | landing/product | 중간 | ViewerSurface(compare) | 단계-6 | yes | no 404 |
| /search | landing/product | 중간 | SearchSurface | 단계-8 | yes | no blank |
| /changes · /insights | landing/product | 중간 | 단계-0 분류 | 단계-8 | yes | no 404 |
| /embed · /lab/* · /playground · /site-signals · /cheatsheet · /health | 단계-0 분류 (site-signals=타 세션) | — | 단계-0 결정 | — | — | — |

---

## 5. Product UI Source Inventory

| 현재 경로 | 책임 | 목표 경로 | 단계 | 임시 alias 필요 | 제거 조건 |
|---|---|---|---|---|---|
| landing/src/lib/terminal/** (54파일) | TerminalSurface | ui/packages/surfaces/src/terminal/** | 단계-4a/4b | 필요 시 | public/local render green |
| landing/src/lib/data/hfRange + dartlabData + {productIndex,companyFilings,companyNonRegular}Runtime | terminal 데이터 폐쇄 | ui/packages/runtime adapters | 단계-4a | 필요 시 | silent fallback 0 |
| landing/src/lib/browser/companyLive · lib/scan/duckSql | terminal 데이터 폐쇄 | ui/packages/runtime adapters | 단계-4a | 필요 시 | port 경유만 |
| landing/src/lib/components/viewer/{ViewerStudio,FinanceDialog} | terminal→viewer 역의존 | 주입 계약(ViewerHost)으로 역전 | 단계-4a | 불필요 | surfaces→landing/src 0 |
| landing/src/lib/viewer/** | ViewerSurface | ui/packages/surfaces/src/viewer/** | 단계-6 | 필요 시 | overlay/standalone green |
| landing/src/lib/styles/{v2-tokens,tokens}.css 외 | design token | ui/packages/design/src/styles/** | 단계-3 | 최소 | landing build green + ui/web smoke (deep import 재배선) |
| landing/src/lib/scan/** (36파일 — DataExplorer·SQL노트북·ScreenBuilder·duckSql·presets) | ScanSurface | ui/packages/surfaces/src/scan/** | 단계-8 | 필요 시 | scan/screener route green |
| landing map 자산 (routes/map·industry + static/map 로더) | MapSurface | ui/packages/surfaces/src/map/** | 단계-8 | 필요 시 | industry prerender 보존 |
| landing/src/routes/search + 검색 인덱스 로더 | SearchSurface | ui/packages/surfaces/src/search/** | 단계-8 | 필요 시 | search route green |
| ui/shared/{chart,api,markdown} | 실사용 0 실측 | 단계-0 census 후 운영자 처분 | 단계-0 결정 · 단계-8 집행 | — | ChartRenderer 참조 문서 동시 갱신 |
| ui/web/src/** | local legacy | 제자리 동결 → 제거 | 단계-11 | 없음 | fallback call 0 |

---

## 6. Adapter Inventory

| 기능 | public adapter | local adapter | test adapter | metadata 필요 | 비고 |
|---|---|---|---|---|---|
| company search | static/HF | local API | fixture | provenance/asOf |  |
| price | static/HF | local API/cache | fixture | stale/coverage |  |
| filing | static metadata | local cache/API | fixture | source/asOf |  |
| finance | static/HF | local API/cache | fixture | stale/coverage | FinancePort 표면=단계-0 census |
| scan | static/HF parquet 소스 | 로컬 parquet URL 소스 | fixture | coverage | 엔진=duckdb-wasm(surface 내부) |
| map | static map JSON(HF seed) | local API | fixture | asOf |  |
| search | static 인덱스(R*) | local API/인덱스 | fixture | asOf |  |
| viewer | public route | component/local route | fixture | source |  |
| AI | deterministic(항상) + onDevice(WebGPU 게이트) | advanced — provider via Ask engine | fake stream | evidence, tier | 공개 AskDrawer 무회귀 |
| services | public-safe + localOnly descriptor | full local registry | fake registry | availability, upgradeHint |  |

---

## 7. AI Provider Inventory

| 항목 | 현재 위치 | 목표 위치 | surface 노출 여부 | 검증 |
|---|---|---|---|---|
| provider settings | ui/web/local server | ui/apps/local + local adapter | no raw secret | provider 없음/있음 |
| model selection |  | local adapter/Ask engine | label only | capabilities |
| stream events |  | AiPort | normalized only | stream e2e |
| tool call |  | Ask engine + ServicesPort | command result only | failure UI |
| evidence | viewer/AI | contracts/evidence | source ref only | evidence panel |

---

## 8. Service Registry Inventory

| service id | group | mode | public 상태 | local 상태 | command 예 | 요구 context |
|---|---|---|---|---|---|---|
| company.search | market | both | available | available | company.search | query |
| filing.regularList | filing | terminal | available | available | filing.openRegularList | code |
| viewer.open | viewer | terminal | available | available | viewer.openFiling | filing |
| finance.export | export | terminal | localOnly (+upgradeHint) | available | finance.exportCsv | code/period |
| ai.explain | ai | both | deterministic/onDevice tier | available (advanced) | ai.explainEvidence | evidence |
| cache.refresh | system | terminal | 숨김 (시스템 명령 — 완전 숨김 허용 예외) | available | cache.refreshCompany | code |

---

## 9. 단계 완료 로그

> `07-progress-ledger.md`로 이관됨 — 완료·중단·예약 entry는 07 원장이 SSOT다. 이 문서에는 착수 전 freeze/inventory 템플릿만 남는다.

---

## 10. 단계-0 실측 결과 (2026-06-13 — 의존 폐쇄·포트 초안 원자료)

### 10.1 terminal 폐쇄 표 (55파일 — syncStatus.ts 신규 포함)

| 외부 모듈 | 파일 수 | 처분 분류 |
|---|---|---|
| $lib/data/hfRange (hyparquet HF range-read) | 5 (macroSeries·priceSeries·reportSeries·terminalFinance·govPrice) | [port로 흡수 — HF 기본구현] |
| $lib/data/dartlabData (loadJson HF-first + cacheStore) | 2 (relations·routeLoad) | [port로 흡수] |
| $lib/data/{productIndexRuntime, companyFilingsRuntime, companyNonRegularFilings} | 4·3·3 (workbench·localAdapter·패널 2 — 패널 직import는 workbench 미경유 잔존) | [port로 흡수 — 4a에서 단일화] |
| $lib/browser/companyLive (DuckDB 라이브 팩트) | 3 | [port로 흡수] |
| $lib/scan/duckSql — type CompanyChange만 | 3 (전부 type-only) | [타입을 계약으로 승격 → scan 코드 의존 0] |
| $lib/components/viewer/{ViewerStudio, FinanceDialog} (dynamic import) | 각 1 (ViewerOverlay:17 · RightStack:499) | [주입 역전 — ViewerHost 계약] |
| $lib/brand | 2 | [design token/prop 주입] |
| $lib/components/GithubIcon.svelte | 1 | [terminal과 함께 이동] |
| $app/environment (browser) | 12 | [환경 헬퍼 1줄 치환] |
| $app/paths (base) | 3 | [basePath 설정 주입] |
| import.meta.env.VITE_DARTLAB_QUOTE_WORKER | 1 (livePrice) | [설정 주입] |
| tokens.css `--dl-*` | CSS 변수 DOM 상속 (import 문 0) | [design token 패키지 분리 필수] |
| npm klinecharts(dynamic)·svelte | 1·4 | [npm dep 그대로] |
| HF API 직접 fetch | 1 (syncStatus — 자급 모듈) | [함께 이동] |

나머지 ~40파일(engine·types·finTabs·indicators·backtest·charts 18종 등) = 외부 의존 0 자급.

### 10.2 포트 매핑 (workbench 14 export ∪ localAdapter 25 메서드)

| Port | 합집합 표면 | 단계-0 결정 |
|---|---|---|
| PricePort | price.{initial,older,loaded}·govPrice·loadGovRecent·minYear·fetchLiveQuote(livePrice) | gov parquet+recent tail 기본구현, live quote=옵션 메서드 |
| FinancePort | finance → TerminalFinanceBundle | viewer financeQuery(DuckDB)는 별도 surface 구현 — 계약 공유만 검토 |
| CompanyPort | products·productIndex·relations·reportFacts | 4메서드로 유지 |
| **ReportPort (분리 신설)** | reportSeries 10종(workforce·investments·shareholderReturn·ownership·execBoard·debtProfile·capitalChanges·auditTrail·topExecPay·auditFees) | 현행 패널 직호출(workbench 미경유) → 4a에서 port 경유 단일화. CompanyPort 비대(14) 방지 |
| FilingPort | regularFilings·nonRegularFilings | rceptNo 중심 — 공시 이벤트 레일 PRD와 동일 계약면 |
| ScanPort | changes(CompanyChange) | terminal이 쓰는 scan 표면은 1개뿐 |
| **MacroPort (신설)** | loadMacroSeries·loadMacroLatest·MACRO_SERIES·ATTRIBUTION | 회사 무관 시리즈 — PricePort 오염 방지. 소비 6파일 전부 terminal 내부 |
| ViewerPort | viewerUrl + 컴포넌트 주입 슬롯 2 | port라기보다 주입 슬롯 — ViewerHost 계약으로 |
| (port 아님) | prefetch(워밍업 orchestration)·LAST_SYM_KEY(localStorage)·routeLoad bootstrap 7종 JSON | bootstrap은 god-port 금지 — port별 분해, orchestration은 terminal 내부 유지 |

### 10.3 전역 locator·silent fallback 전수 (4a 치환 대상)

- `window.__DARTLAB_LOCAL_TERMINAL__`: 코드 6파일 — landing localAdapter.ts(정의) + ui/web LandingTerminalSurface.tsx(set/restore/delete)·localTerminalData.ts·landingDataShims.ts
- `localTerminalAdapter()?.x() ?? ...`: 13파일 / ~33개소 — workbench(13)·reportSeries(10)·priceSeries(3)·govPrice(2)·terminalFinance(1)·relations(1)·CenterStack·RightStack·ViewerOverlay(각 1)

### 10.4 viewer/scan/map 폐쇄 요약

- viewer(49+18파일): hfRange·duckdb(CDN jsdelivr 동적 — npm 아님)·dartlabData·brand·web-llm·dompurify + **ViewerStudio→sections/Header.svelte landing 셸 역의존(주입 역전 대상)** + JSON 자산 3종 동반
- scan(41파일): duckdb·hfRange·companyFilingsRuntime·format 2종·Sparkline·@codemirror 6종·웹워커
- map: 로더=lib/browser/dartlabBrowser.marketMap()(map JSON 6종 병렬)+industry/[id] 직접 fetch. 컴포넌트 13종(lib/components/industry — cosmos·d3-force·d3-hierarchy). lib/browser/=map+terminal 공용층
- 회사 검색: search-index.json 로더(routeLoad + dartlabData 화이트리스트) + viewer searchIndex(본문 인메모리) 두 갈래

### 10.5 단계-4a 작업량 추정

port 정의+HF 기본구현 이관(~10파일) + 호출부 치환 13파일/33개소 + viewer 주입 역전 2 + $app/environment 12파일 헬퍼 치환 + MacroPort·ReportPort 신설 = **~25파일 터치, 2~3세션 규모** — 착수 전 sub-unit 분해 선언 의무(07 규칙 3). 가장 섬세한 부분 = ViewerStudio embedded·FinanceDialog 주입 계약.

---

## 11. Session Cleanup 체크

작업 종료 전 확인:

```text
dev server 종료:
watcher 종료:
browser automation 종료:
임시 screenshot 정리:
임시 build 산출물 처리:
git status 확인:
다른 세션 변경 보존 확인:
```

장기 실행 프로세스를 사용자에게 남겨야 하는 경우, 이유와 URL/프로세스 정보를 최종 응답에 명시한다.
