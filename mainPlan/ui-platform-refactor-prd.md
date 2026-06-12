# DartLab UI Platform Refactor PRD

상태: v1 확정 기준 문서  
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

문서 난립을 막기 위해 새 계획 문서는 추가하지 않는다. 필요한 내용은 위 파일 중 하나에 통합한다.

---

## 2. 핵심 결정

1. 장기 기준점은 `landing`도 `ui/web`도 아니다. 기준점은 새 `ui/packages` 계층이다.
2. `landing`은 공개 콘텐츠 앱으로 남긴다. blog, docs, SEO, sitemap, static asset, GitHub Pages 책임을 가진다.
3. terminal, viewer, company, chart, evidence, ask 작업면은 `ui/packages/surfaces`의 공용 Svelte surface로 승격한다.
4. public/local 차이는 컴포넌트 fork가 아니라 adapter 차이로만 만든다.
5. 로컬 앱은 AI provider를 직접 붙인다. 단 provider SDK, API key, model 선택, tool execution은 `localAiAdapter`와 Ask 엔진 뒤에 둔다.
6. 로컬에는 챗모드와 터미널모드가 있다. 터미널모드는 가격, 재무, 공시, viewer, screener, export, evidence, cache, AI tool 같은 로컬 서비스 대부분이 붙는 운영 화면이다.
7. 기존 React `ui/web`은 legacy fallback이다. 새 제품 기능을 추가하지 않고, local SvelteKit이 안정화된 뒤 제거한다.
8. `landing`은 완성 전까지 무중단이다. 제품 route 전환은 hidden route, compatibility wrapper, feature flag, smoke 검증 이후에만 기본 경로로 승격한다.
9. 작업은 로컬 `master`에서 한 번에 하나의 작업 단위로 진행한다. 각 작업 단위는 독립 build, 검증, rollback 경계를 가진다.

---

## 3. 문서별 책임

`00-product-prd.md`:

- 왜 이 리팩토링이 필요한지
- 공개 UI와 로컬 AI UI가 어떤 사용자 경험을 공유해야 하는지
- 하지 않을 것과 성공 기준

`01-target-architecture.md`:

- 최종 폴더 구조
- `landing`, `ui/apps/public`, `ui/apps/local`, `ui/web legacy` 역할
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
- 단계별 완료 로그 템플릿

---

## 4. 작업 운영 규칙

1. 시작 전 `06-inventory-and-freeze-template.md`의 Freeze 체크리스트를 채운다.
2. 현재 진행 중인 다른 작업 세션이 종료되기 전에는 리팩토링을 시작하지 않는다.
3. PyPI 릴리스 1회와 릴리스 기준 commit/tag 기록 이후 시작한다.
4. 매 작업 단위 시작 전 `git status`를 확인하고 기존 dirty file 소유자를 분류한다.
5. 다른 세션이 만진 파일과 겹치면 해당 작업 단위는 시작하지 않는다.
6. 대량 이동과 기능 변경을 같은 작업 단위에 섞지 않는다.
7. `landing` build 또는 공개 route smoke가 실패하면 작업 단위는 완료될 수 없다.
8. `ui/web` fallback을 제거하는 작업은 마지막 안정화 단계에서만 허용한다.
9. 커밋 메시지는 한국어로 작성하고 변경 category와 내용을 모두 담는다.

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
9. GitHub Pages와 local PyPI UI가 같은 surface release를 사용한다.
10. 주요 route의 console error가 0이다.
11. public/local screenshot baseline이 같은 디자인 언어를 유지한다.
12. `landing`의 공개 콘텐츠와 기존 URL은 전체 전환 기간 동안 중단되지 않는다.

---

## 6. 최종 원칙

> DartLab의 제품 UI는 한 벌이어야 하고, 공개/로컬 차이는 runtime adapter와 service adapter로만 존재해야 한다.

이 원칙에 어긋나는 구조는 단기적으로 편해 보여도 장기 유지보수 실패로 본다.
