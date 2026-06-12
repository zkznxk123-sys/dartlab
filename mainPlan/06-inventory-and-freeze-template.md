# 06. Inventory and Freeze Template

상태: v2 확정 기준 문서 (개정 이력은 07 원장)  
범위: 착수 전 작성할 inventory, freeze, 단계 완료 기록 템플릿

---

## 1. Freeze 체크리스트

리팩토링 첫 작업 단위를 시작하기 전에 아래 표를 채운다.

```text
작업 기준 기준선:
작업 기준 commit:
PyPI version:
PyPI 업로드 시간:
릴리스 tag:
릴리스 검증 담당:
열린 작업 세션:
세션별 종료 확인:
남은 dirty file:
dirty file 소유자:
dirty file 처리 방식:
landing 현재 build 상태:
local UI 현재 build 상태 (ui/web 단독 npm ci + build 재현):
Python package 현재 상태:
rollback 기준 commit:
ui/node_modules·ui/build 스트레이 처분:
node_modules OneDrive 동기화 제외 확인:
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
|  | modified/untracked |  | 겹침/무관/차단 | 유지/분리/보류 |  |

규칙:

- 소유자가 불명확한 변경은 건드리지 않는다.
- 리팩토링 파일과 겹치면 작업 단위를 시작하지 않는다.
- 기존 변경을 되돌리지 않는다.

---

## 3. Current App Inventory

| 앱 | 현재 역할 | build 명령 | 산출물 | 배포/패키징 경로 | 유지/이동/제거 |
|---|---|---|---|---|---|
| landing | public content + product UI |  |  | GitHub Pages | 유지 — 영구 public shell (원본은 packages로 승격) |
| ui/web | local React legacy |  |  | Python server SPA | 제자리 동결 → fallback 후 제거 (물리 이동 금지) |
| ui/apps/local | new local SvelteKit |  |  | wheel UI build | 신규 |
| ui/shared | 무소속 공유 코드 (chart 16·api 3·markdown 2) |  |  | 없음 — 실사용 0 실측(2026-06-13) | 단계-0 census 후 운영자 처분 결정 |

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

## 10. Session Cleanup 체크

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
