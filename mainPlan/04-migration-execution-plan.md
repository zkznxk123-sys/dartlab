# 04. Migration Execution Plan

상태: v1 확정 기준 문서  
범위: 로컬 `master` 순차 작업, landing 무중단, 단계별 실행 계획

---

## 1. 운영 모델

이 리팩토링은 로컬 저장소의 `master`에서 순차 작업 단위로 진행한다.

절대 전제:

1. 별도 분기 작업, 작업 복제본, 병합 workflow, 원격 코드리뷰 workflow를 기본 운영 방식으로 두지 않는다.
2. 한 번에 하나의 작업 단위만 진행한다.
3. 각 작업 단위는 독립적으로 빌드 가능해야 한다.
4. 각 작업 단위는 실패 시 되돌릴 수 있는 커밋 경계를 가져야 한다.
5. 커밋 메시지는 한국어로 작성한다.
6. 다른 세션이 남긴 변경은 되돌리지 않는다.
7. 다른 세션이 같은 파일을 만진 흔적이 있으면 해당 작업 단위는 시작하지 않는다.
8. 완료 전까지 `landing`의 기존 공개 route와 GitHub Pages build는 무중단이어야 한다.

착수 전 금지:

- PyPI 릴리스 전 폴더 대이동 금지
- 다른 기능 작업과 같은 파일 병행 수정 금지
- 대량 rename과 기능 변경 혼합 금지
- `landing` 공개 route를 새 구조로 즉시 대체 금지
- `ui/web` 삭제 또는 기본 UI 전환 선행 금지

---

## 2. Landing 무중단 원칙

이 리팩토링이 완성될 때까지 `landing`은 무중단이다.

무중단의 의미:

1. 기존 GitHub Pages 공개 URL은 유지하거나 검증된 redirect를 제공한다.
2. blog, docs, SEO, sitemap, static asset, llms/static content route는 초기 리팩토링 대상에서 제외한다.
3. 제품 route 전환은 additive 방식으로만 시작한다.
4. 먼저 wrapper, feature flag, hidden route, compatibility route로 검증한다.
5. `landing`에서 제품 UI 원본을 제거하는 작업은 public/local surface parity와 fallback 검증 이후에만 허용한다.
6. `landing` build 또는 공개 route smoke가 실패하면 해당 작업 단위는 완료될 수 없다.
7. GitHub Pages 산출물의 base path, asset path, deep link refresh는 매 전환 단계에서 검증한다.
8. 공개 사이트에 half-wired route를 남기지 않는다.
9. `landing` content route와 product route를 동시에 옮기지 않는다.

즉시 중단 조건:

- `landing` build 실패
- 기존 공개 URL 404
- 공개 route에서 local-only API 호출 발생
- 공개 route에서 secret/provider 설정 노출
- product route 전환 중 blank 화면 또는 hydration error 발생

---

## 3. 작업 단위 완료 공통 기준

각 작업 단위는 아래 기준을 만족해야 완료다.

1. 변경 목적이 이 문서의 작업 단위 번호와 연결되어 있다.
2. app boundary 또는 package boundary를 새로 흐리지 않는다.
3. public/local/landing 중 어느 runtime에 영향을 주는지 명시한다.
4. 새 deep import가 없다.
5. 새 임시 alias가 있다면 제거 작업 단위 번호가 있다.
6. console error 0 smoke 또는 해당 작업 단위에서 불필요한 이유가 있다.
7. visual screenshot이 필요한 작업 단위는 screenshot 결과를 남긴다.
8. `ui/web` legacy에 새 기능을 추가하지 않는다.
9. build output 또는 lockfile 변경 이유가 명확하다.
10. rollback 방법이 한 문장으로 설명 가능하다.
11. `landing` 기존 공개 route가 깨지지 않았다는 검증이 있다.

---

## 4. 단계별 실행

### 단계-0: Inventory and Boundary Map

목표:

- `landing` 제품 UI와 content UI를 분류한다.
- 옮길 파일 목록과 유지할 파일 목록을 확정한다.
- dependency graph를 뽑는다.
- `ui/web`, `landing`, Python server SPA, PyPI wheel 포함 경로를 표로 고정한다.
- 공개 route, legacy shim, adapter 후보, feature flag 후보를 기록한다.

산출:

- `06-inventory-and-freeze-template.md` 작성 완료
- migration inventory table
- import graph report
- landing 무중단 영향표

검증:

- 코드 변경 최소
- build 영향 없음
- `landing` 공개 route 목록 보존

### 단계-1: `ui/packages/contracts`

목표:

- Company, Filing, Price, Finance, Viewer, AI, Runtime 타입 계약 생성
- public/local이 공유할 최소 타입 정의
- adapter 반환 metadata 기준 추가
- AG-UI allowlist 이벤트와 Evidence 표시 계약 분리

범위:

```text
ui/packages/contracts/**
ui/package.json workspace 설정
ui/tsconfig.base.json
```

금지:

- UI 컴포넌트 이동
- app route 변경
- runtime 구현 추가

검증:

- TypeScript build
- contracts package no dependency check
- public/local fixture type conformance

### 단계-2: `ui/packages/runtime`

목표:

- Runtime port 인터페이스와 fake runtime 구현
- public/local adapter skeleton
- surface가 의존할 runtime context 생성
- `basePath`, `navigate`, `storage`, `fetch`, `openExternal`, `featureFlags`, `telemetry` 표준화
- `ServicesPort` skeleton 추가

범위:

```text
ui/packages/runtime/**
```

검증:

- fake runtime unit tests
- public/local adapter type tests
- route/server/global 직접 참조 금지 검사

### 단계-3: `ui/packages/design`

목표:

- landing token을 공용 design package로 이동
- terminal/viewer token을 semantic token으로 정리
- primitive component 최소 세트 작성
- `--dl-*` 원천 token과 alias map 정의

검증:

- landing build
- visual smoke screenshot
- inline hex/rgb 신규 사용 0
- public/local 기본 surface screenshot tone 일치

### 단계-4: Terminal Surface Extraction

목표:

- `landing/src/lib/terminal/**`을 `ui/packages/surfaces/src/terminal/**`로 승격
- HF/static fetch와 route path 의존 제거
- `TerminalSurface`가 runtime만 보게 만든다.
- 좌측 탐색/검색/필터, 중앙 chart/시각화/fullscreen, 우측 공시/service panel 구조를 계약으로 고정한다.
- 우측 stack에는 graph를 배치하지 않는다.

범위:

```text
ui/packages/surfaces/src/terminal/**
landing terminal route wrapper
ui/packages/runtime public adapter terminal support
```

검증:

- public terminal route 동작
- local fake runtime terminal render
- console error 0
- screenshot diff 허용 범위 내
- terminal ready/loading/empty/error 상태 screenshot
- chart canvas nonblank pixel 검사

### 단계-5: Local SvelteKit App Scaffold

목표:

- `ui/apps/local` 생성
- local runtime adapter 연결
- `/chat`, `/terminal/[code]`, `/ask`, `/analysis/[code]`, `/analysis/[code]/viewer` skeleton
- `TerminalSurface` full screen mount
- 챗모드에서 터미널모드로 별도 탭 없이 진입
- 정기공시 리스트와 viewer를 terminal 우측 패널/fullscreen 흐름에 연결

범위:

```text
ui/apps/local/**
python server static frontend 선택 flag
```

검증:

- `ui/apps/local` dev server
- local API 연결
- chat -> terminal
- Ask -> recent company terminal
- terminal regular filing viewer overlay
- 기존 `ui/web` fallback flag 유지
- landing build 영향 없음

### 단계-6: Viewer Surface Extraction

목표:

- 공시뷰어를 `ui/packages/surfaces/src/viewer`로 승격
- terminal overlay와 standalone viewer가 같은 `ViewerSurface` 사용
- local/public viewer adapter 분리
- TOC, period timeline, panel matrix, compare matrix, ask drawer를 한 surface로 통합

검증:

- viewer standalone
- viewer embedded component mode
- panel toc/grid
- search/evidence
- console error 0
- fullscreen viewer viewport 95% 이상
- focus trap, focus restore, Escape close

### 단계-7: AI Surface Integration

목표:

- Viewer Ask drawer와 Terminal AI command layer를 `AiPort` 뒤에 연결
- public disabled mode
- local enabled mode
- local AI provider 직접 연결
- Ask 엔진 기반 chat/terminal mode 공통화
- raw trace, raw tool args/result, 내부 tool id는 Evidence panel로 분리

검증:

- provider 없음: graceful disabled
- provider 있음: stream response
- selected evidence context 전달
- tool call 실패 표시
- AG-UI allowlist 외 이벤트 렌더 금지
- 챗모드와 터미널모드가 같은 Ask engine contract 사용

### 단계-8: Services and Company/Chart Surface Extraction

목표:

- 회사 화면, charting, evidence UI 공용화
- terminal/chart/viewer 간 상태 규칙 정리
- `ServicesPort` command registry 구현
- ChartSpec -> ChartRenderer 단일 경로
- 가격 상승/하락, good/bad, brand 색 의미를 token에서 분리

검증:

- company page public/local
- price chart controls
- chart state persistence
- no duplicated chart CSS
- service command palette
- chart toolbar, tooltip, axis 표시
- tabular-nums와 단위 표시 일관성

### 단계-9: Public Product App Wiring

목표:

- `ui/apps/public`에서 product routes 담당
- GitHub Pages publish composition 구현
- landing content + public product routes 결합
- `landing` content route는 그대로 두고 product route만 wrapper 기반으로 전환
- 공개 URL 안정성을 확인한 뒤에만 기본 route 변경

검증:

- GitHub Pages build artifact 구조
- base path
- deep link refresh
- static asset path
- 기존 content route smoke
- 기존 product URL redirect 또는 compatibility wrapper 확인

### 단계-10: Local App Default Switch

목표:

- Python server 기본 UI를 `ui/apps/local`로 전환
- 기존 `ui/web` fallback flag 유지
- `resolveUiBuildDir`, `serveSpa`, asset 404/cache 동작 검증
- PyPI wheel에 local SvelteKit build 산출물 포함

검증:

- wheel install 후 local UI serve
- `/chat`
- `/terminal/:code`
- `/ask`
- `/analysis/:code`
- `/analysis/:code/viewer`
- provider settings
- `DARTLAB_UI_DIR`로 이전 build 지정 가능
- 신규 venv `pip install` smoke

### 단계-11: `ui/web` Legacy Removal

조건:

- local SvelteKit이 2회 릴리스에서 안정
- user-facing regression 없음
- fallback 요구 없음
- `ui/web` legacy 호출 경로 0
- `landing` 공개 route 무중단 검증 완료

목표:

- `ui/web` 제거 또는 archive
- React deps 제거
- reference 정리

검증:

- package lock 정리
- wheel size
- all UI routes pass
- landing build
- public/local screenshot parity

---

## 5. 작업 단위 요약

```text
단계-0  Inventory and Boundary Map
단계-1  contracts package
단계-2  runtime ports, fake runtime, services skeleton
단계-3  design tokens and primitives
단계-4  terminal surface extraction
단계-5  local SvelteKit scaffold
단계-6  viewer surface extraction
단계-7  AI runtime integration
단계-8  services, company, chart, evidence surfaces
단계-9  public product app wiring
단계-10 local app default switch
단계-11 ui/web legacy removal
```
