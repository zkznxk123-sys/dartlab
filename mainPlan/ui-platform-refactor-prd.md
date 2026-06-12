# DartLab UI Platform Refactor PRD

상태: v2 확정 기준 문서 (개정 이력은 07 원장)  
위치: `mainPlan/ui-platform-refactor-prd.md`  
목적: GitHub Pages 공개 UI와 로컬 AI UI를 하나의 UI 플랫폼 자산 체계로 관리하기 위한 리팩토링 기준  
운영 전제: 로컬 `master`에서 순차 작업 단위로 진행한다. 별도 분기 작업, 작업 복제본, 병합 절차, 원격 코드리뷰 절차를 이 계획의 기본 전제로 두지 않는다.  
무중단 전제: 리팩토링 완료 전까지 `landing`의 공개 URL, GitHub Pages build, blog/docs/SEO/static route는 무중단이다.

---

## 1. 문서 세트

이 계획은 `mainPlan` 아래 문서 세트 하나로 관리한다. 기준 문서는 이 인덱스이며, 세부 내용은 역할별 문서로 나뉜다.

| 문서 | 책임 |
|---|---|
| [ui-platform-refactor-prd.md](ui-platform-refactor-prd.md) | 이 파일. 최상위 결정, 문서 지도, 실행 규칙 |
| [00-product-prd.md](00-product-prd.md) | 목표, 범위, 사용자 흐름, 성공 기준 |
| [01-target-architecture.md](01-target-architecture.md) | 앱/패키지/폴더 구조, 의존성, export, alias 규칙 |
| [02-runtime-ai-services.md](02-runtime-ai-services.md) | runtime contract, adapter, AI provider, Ask 엔진, 서비스 registry |
| [03-ui-design-system.md](03-ui-design-system.md) | surface API, terminal/viewer UX, 디자인 토큰, 접근성, 시각 회귀 |
| [04-migration-execution-plan.md](04-migration-execution-plan.md) | 단계별 실행 계획, landing 무중단, local master 작업 운영 |
| [05-validation-release-rollback.md](05-validation-release-rollback.md) | 테스트, 릴리스, PyPI, GitHub Pages, rollback/fix-forward |
| [06-inventory-and-freeze-template.md](06-inventory-and-freeze-template.md) | 착수 전 작성할 표와 검증 템플릿 |
| [07-progress-ledger.md](07-progress-ledger.md) | 진행 원장 — NEXT 포인터, 작업 단위 완료·중단·재개 기록 (유일한 가변 문서) |

문서 난립을 막기 위해 새 계획 문서는 추가하지 않는다. 필요한 내용은 위 파일 중 하나에 통합한다. 진행 상태는 07 원장에만 기록한다 — 00~06은 기준 문서이며, 개정 시 07에 개정 entry를 남긴다.

---

## 2. 핵심 결정

1. 장기 기준점은 `landing`도 `ui/web`도 아니다. 기준점은 새 `ui/packages` 계층이다.
2. `landing`은 공개 콘텐츠 앱이면서 **영구 public shell**이다. blog, docs, SEO, sitemap, static asset, GitHub Pages 책임에 더해 제품 route의 얇은 wrapper(+public adapter 배선)를 소유한다. `ui/apps/public`은 신설하지 않는다(비채택) — 두 SvelteKit 정적 빌드를 한 Pages artifact로 합성하는 복잡성을 회피한다. 별도 도메인/배포 분리 필요가 실제 발생할 때만 재개한다.
3. 제품 작업면 전부를 `ui/packages/surfaces`의 공용 Svelte surface로 승격한다 — terminal·viewer·company·scan·screener·map·search·ask + 공용 부품 charting·evidence. 전수는 01 §4.1 지도가 단일 참조다.
4. public/local 차이는 컴포넌트 fork가 아니라 adapter 차이로만 만든다. Port 메서드는 required로 선언하고 미지원은 명시적 unavailable 상태로 드러낸다 — optional 메서드 + 조용한 public fallback(현행 `localTerminalAdapter()?.x() ?? HF로드()` 패턴)을 금지한다.
5. AI는 3-티어다 — local = server-engine(`/api/agent/*`, `src/dartlab/ai` Ask 엔진, 고급 분석) / public = onDevice(WebGPU, `webgpuUsable` 실측 게이트) + deterministic(결정론 Q&A, 항상) / test = fake. "public AI = disabled"는 폐기한다 — 이미 출시된 공개 AskDrawer(Tier0 결정론 + WebGPU)의 회귀를 금지한다.
6. 로컬 앱은 AI provider를 직접 붙인다. 단 provider SDK, API key, model 선택, tool execution은 `localAiAdapter`와 Ask 엔진 뒤에 둔다.
7. 로컬에는 챗모드와 터미널모드가 있다. 터미널모드는 가격, 재무, 공시, viewer, screener, export, evidence, cache, AI tool 같은 로컬 서비스 대부분이 붙는 운영 화면이다.
8. 기존 React `ui/web`은 legacy fallback이다. 물리 이동하지 않고 제자리에서 동결한다(새 기능 금지, 보안·치명 bug만 수정). local SvelteKit이 안정화된 뒤 별도 작업 단위로 제거한다.
9. 무중단 대상은 둘이다 — `landing` 공개 route **그리고 `ui/web` 로컬 터미널**(현행 pip 사용자). 제품 route 전환은 hidden route, compatibility wrapper, feature flag, smoke 검증 이후에만 기본 경로로 승격한다.
10. npm 워크스페이스를 repo 루트에 둔다 — `workspaces = [landing, ui/packages/*, ui/apps/local]`. `ui/web`은 제외한다(frozen legacy, 자체 lockfile, Vite 6 잔존). svelte 버전은 워크스페이스에서 정확 버전(caret 금지)으로 단일 고정한다.
11. 기능은 로컬에서 먼저 개발하고, 승격 게이트(02 §10)를 통과한 것만 공개로 승격한다. 공개에서는 승격 가능(또는 로컬 전용 상위) 기능을 숨기지 않는다 — tier 표시 + 로컬 업그레이드 hint로 funnel을 만든다.
12. 작업은 로컬 `master`에서 한 번에 하나의 작업 단위로 진행한다. 각 작업 단위는 독립 build, 검증, rollback 경계를 가지며 `07-progress-ledger.md`에 기록한다. 커밋 규약은 `<카테고리>: 플랫폼(단계-N) <내용>` — 카테고리는 repo 커밋 정책의 허용 접두(추가/수정/문서/정리/리팩토링 등, `.claude/hooks/check_no_ai_markers.py` COMMIT_TYPES)를 따른다.
13. 활성 제품 작업(백테스팅·공시 이벤트 레일 등)과의 공존은 04 §2.5를 따른다 — landing 제품 코드를 실제로 이동하는 단계만 "이동 원자 윈도우"로 격리하고, 그 외 단계는 병행을 허용하며, 충돌 시 제품 작업이 우선한다.

---

## 3. 문서별 책임

`00-product-prd.md`:

- 왜 이 리팩토링이 필요한지
- 공개 UI와 로컬 AI UI가 어떤 사용자 경험을 공유해야 하는지
- 하지 않을 것과 성공 기준

`01-target-architecture.md`:

- 최종 폴더 구조
- `landing`, `ui/apps/local`, `ui/web legacy` 역할 + `ui/apps/public` 비채택 결정
- `contracts`, `runtime`, `design`, `surfaces`, `testing` 패키지 경계
- import 방향, package export, alias, naming 규칙

`02-runtime-ai-services.md`:

- `DartLabRuntime` 최상위 계약
- public/local/test adapter
- AI provider 직접 연결 방식
- Ask 엔진, 챗모드, 터미널모드
- `ServicesPort`와 service command registry

`03-ui-design-system.md`:

- 공용 surface API 규칙
- TerminalSurface, ViewerSurface, CompanySurface, Charting 책임
- 디자인 토큰, CSS 경계, primitive component
- 접근성, 키보드, focus, screenshot 기준

`04-migration-execution-plan.md`:

- 착수 전 freeze
- landing 무중단 원칙
- 단계-0부터 단계-11까지 실행 순서
- 각 단계의 목표, 범위, 금지, 검증

`05-validation-release-rollback.md`:

- 단위, 통합, 브라우저, 시각, 릴리스 테스트
- PyPI 릴리스 전후 검증
- GitHub Pages 검증
- rollback/fix-forward 기준
- legacy 제거 조건

`06-inventory-and-freeze-template.md`:

- 착수 전 채워야 하는 inventory 표
- route, file, adapter, service, AI, dirty file, 세션 종료 확인표

`07-progress-ledger.md`:

- NEXT 단일 포인터 (끊긴 세션의 재개 지점)
- 작업 단위 entry — 완료·중단·예약 기록, 04 §3 완료 기준 체크박스 인스턴스
- 단계 완료 로그의 SSOT (06 §9 템플릿을 대체)

---

## 4. 작업 운영 규칙

1. 시작 전 `06-inventory-and-freeze-template.md`의 Freeze 체크리스트를 채운다.
2. 현재 진행 중인 다른 작업 세션이 종료되기 전에는 리팩토링을 시작하지 않는다. 단 04 §2.5 공존 규칙에 따라 landing 제품 코드를 이동하지 않는 단계는 병행할 수 있다.
3. PyPI 릴리스 1회와 릴리스 기준 commit/tag 기록 이후 시작한다. 단 코드 무변경인 단계-0(인벤토리)은 릴리스 전에도 착수 가능하다(07 NEXT 기준).
4. 매 작업 단위 시작 전 `git status`를 확인하고 기존 dirty file 소유자를 분류한다.
5. 다른 세션이 만진 파일과 겹치면 해당 작업 단위는 시작하지 않는다.
6. 대량 이동과 기능 변경을 같은 작업 단위에 섞지 않는다.
7. `landing` build 또는 공개 route smoke가 실패하면 작업 단위는 완료될 수 없다. `ui/web` 로컬 터미널 smoke 실패도 동일하다.
8. `ui/web` fallback을 제거하는 작업은 마지막 안정화 단계에서만 허용한다.
9. 커밋 메시지는 한국어로 작성하고 `<카테고리>: 플랫폼(단계-N) <내용>` 규약을 따른다(카테고리 = repo 허용 접두) — `git log --grep "플랫폼(단계"` 로 전체 이력을 추적한다.
10. 모든 작업 단위는 시작 전 07 원장에 entry를 만들고 완료/중단 시 갱신한다. 작업 단위는 1세션 완결 크기로 설계하며, 초과가 예상되면 착수 전 sub-unit 분해를 원장에 선언한다.
11. 중단 시 의무 기록: 중단 지점 + 다음 행동 1줄. WIP 미커밋 상태로 세션을 끝내지 않는다(완결 커밋 또는 되돌림).

---

## 5. 완료 정의

이 리팩토링은 다음 상태가 되었을 때 완료다.

1. public terminal과 local terminal이 같은 `TerminalSurface`를 사용한다.
2. public viewer와 local viewer가 같은 `ViewerSurface`를 사용한다.
3. local AI는 `AiPort`와 Ask 엔진으로만 연결된다.
4. terminal mode는 `ServicesPort`를 통해 로컬 서비스 command를 실행한다.
5. `landing/src/lib/terminal` 같은 제품 UI 원본이 `landing`에 남지 않는다.
6. public/local 차이는 adapter에만 존재한다.
7. 디자인 토큰은 `ui/packages/design`에서 관리된다.
8. `ui/web`은 legacy fallback 기간 이후 제거된다.
9. GitHub Pages(landing shell)와 local PyPI UI가 같은 surface release를 사용한다.
10. 주요 route의 console error가 0이다.
11. public/local screenshot baseline이 같은 디자인 언어를 유지한다.
12. `landing`의 공개 콘텐츠와 기존 URL, 그리고 `ui/web` 로컬 터미널은 전체 전환 기간 동안 중단되지 않는다.
13. 공개 AI(결정론 Q&A + WebGPU 온디바이스)는 전환 전후 회귀가 없다.

---

## 6. 최종 원칙

> DartLab의 제품 UI는 한 벌이어야 하고, 공개/로컬 차이는 runtime adapter와 service adapter로만 존재해야 한다.

이 원칙에 어긋나는 구조는 단기적으로 편해 보여도 장기 유지보수 실패로 본다.
