# 06. Inventory and Freeze Template

상태: v1 확정 기준 문서  
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
local UI 현재 build 상태:
Python package 현재 상태:
rollback 기준 commit:
```

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
| landing | public content + product UI |  |  | GitHub Pages | 유지 + product 분리 |
| ui/web | local React legacy |  |  | Python server SPA | fallback 후 제거 |
| ui/apps/local | new local SvelteKit |  |  | wheel UI build | 신규 |
| ui/apps/public | public product shell |  |  | GitHub Pages composition | 필요 시 신규 |

---

## 4. Public Route Inventory

| route | 현재 owner | 사용자 영향 | 새 owner | 전환 방식 | smoke 필요 | 무중단 기준 |
|---|---|---|---|---|---|---|
| / | landing | 높음 | landing | 유지 | yes | 200 + metadata |
| /blog/* | landing | 높음 | landing | 유지 | yes | 200 |
| /docs/* | landing | 높음 | landing | 유지 | yes | 200 |
| /terminal/* | landing/product | 높음 | public wrapper/surface | wrapper 후 전환 | yes | no 404 |
| /viewer/* | landing/product | 높음 | public wrapper/surface | wrapper 후 전환 | yes | no blank |

---

## 5. Product UI Source Inventory

| 현재 경로 | 책임 | 목표 경로 | 단계 | 임시 alias 필요 | 제거 조건 |
|---|---|---|---|---|---|
| landing/src/lib/terminal/** | TerminalSurface | ui/packages/surfaces/src/terminal/** | 단계-4 | 필요 시 | public/local render green |
| landing/src/lib/viewer/** | ViewerSurface | ui/packages/surfaces/src/viewer/** | 단계-6 | 필요 시 | overlay/standalone green |
| landing/src/lib/chart/** | charting | ui/packages/surfaces/src/charting/** | 단계-8 | 필요 시 | chart visual green |
| landing/src/lib/styles/** | design token | ui/packages/design/src/styles/** | 단계-3 | 최소 | landing build green |
| ui/web/src/** | local legacy | ui/apps/web-legacy 또는 제거 | 단계-11 | 없음 | fallback call 0 |

---

## 6. Adapter Inventory

| 기능 | public adapter | local adapter | test adapter | metadata 필요 | 비고 |
|---|---|---|---|---|---|
| company search | static/HF | local API | fixture | provenance/asOf |  |
| price | static/HF | local API/cache | fixture | stale/coverage |  |
| filing | static metadata | local cache/API | fixture | source/asOf |  |
| viewer | public route | component/local route | fixture | source |  |
| AI | disabled/demo | provider via Ask engine | fake stream | evidence |  |
| services | public-safe | full local registry | fake registry | availability |  |

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
| filing.regularList | filing | terminal | available/limited | available | filing.openRegularList | code |
| viewer.open | viewer | terminal | available | available | viewer.openFiling | filing |
| finance.export | export | terminal | disabled/limited | available | finance.exportCsv | code/period |
| ai.explain | ai | both | disabled/demo | available | ai.explainEvidence | evidence |
| cache.refresh | system | terminal | disabled | available | cache.refreshCompany | code |

---

## 9. 단계 완료 로그

각 작업 단위 완료 시 아래 양식으로 기록한다.

```text
단계:
완료 commit:
변경 파일:
영향 범위:
landing 영향:
local 영향:
public 영향:
새 alias:
제거 예정 alias:
실행 테스트:
실행하지 못한 테스트:
스크린샷 위치:
rollback 방법:
남은 위험:
```

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
