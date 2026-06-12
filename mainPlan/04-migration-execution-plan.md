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
5. 커밋 메시지는 한국어 + `<카테고리>: 플랫폼(단계-N) <내용>` 규약으로 작성한다. 카테고리는 repo 커밋 정책의 허용 접두를 따른다(`.claude/hooks/check_no_ai_markers.py` COMMIT_TYPES — 임의 접두는 hook이 차단한다).
6. 다른 세션이 남긴 변경은 되돌리지 않는다.
7. 다른 세션이 같은 파일을 만진 흔적이 있으면 해당 작업 단위는 시작하지 않는다 (§2.5 공존 규칙으로 운영).
8. 완료 전까지 `landing`의 기존 공개 route·GitHub Pages build **그리고 `ui/web` 로컬 터미널**은 무중단이어야 한다.
9. 모든 작업 단위는 시작 전 07 원장에 entry를 만들고, 1세션 완결 크기로 설계한다. 초과 예상 시 착수 전 sub-unit 분해를 원장에 선언한다. 중단 시 중단 지점 + 다음 행동 1줄을 기록하고, WIP 미커밋 상태로 세션을 끝내지 않는다.

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
- `ui/web` 로컬 터미널 깨짐 (deep import/alias 파손 포함)
- 공개 AI(결정론 Q&A + WebGPU 온디바이스) 회귀

---

## 2.5 활성 제품 작업 공존 규칙

이 리팩토링은 11단계 전체 freeze가 아니다. landing 제품 코드를 실제로 이동하는 작업 단위만 격리한다.

1. **병행 허용**: 단계-0, 1, 2, 3, 4a, 5, 7은 `landing/src/lib/terminal/**` 등 제품 코드를 이동하지 않으므로 활성 제품 PRD(백테스팅, 공시 이벤트 레일 등)와 병행 가능하다. 단 같은 파일을 동시에 만지는 것은 여전히 금지(§1-7).
2. **이동 원자 윈도우**: 단계-4b, 6, 8, 9처럼 landing 제품 파일을 이동/재배선하는 작업 단위는 07 원장에 사전 예약하고, 진행 중인 제품 작업 단위가 landed된 직후 틈에만 연다. 윈도우 동안 해당 경로의 다른 작업을 금지하고, 1세션 내 완결하지 못하면 즉시 롤백한다.
3. **충돌 시 기본 우선순위 = 제품 PRD 우선.** 이동 윈도우가 양보한다.
4. 리팩토링 기간 중 제품 릴리스가 발생하면 freeze 기준 commit/tag를 07 원장에 재기록한다(06 §1).

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
12. `ui/web` 로컬 터미널이 깨지지 않았다는 검증이 있다 (영향 단계 한정 — landing styles/terminal/viewer 경로를 만진 경우 필수).
13. 배포 파이프라인 하드코딩 3종 점검 — `deploy-landing.yml` paths 필터, `publish.yml` UI build/copy 경로, `dependabot.yml` npm directory — 이 작업 단위의 파일 이동이 이들을 깨뜨리지 않는지 확인했다.
14. 07 원장에 완료 entry를 기록했다.

---

## 4. 단계별 실행

### 단계-0: Inventory and Boundary Map

목표:

- `landing` 전 route를 제품/콘텐츠로 분류한다 — 경계 원칙(00 §2-11): 콘텐츠 자산 빼고 전부 제품. 01 §4.1 전수 지도의 "단계-0 분류" 행(changes·insights·embed·lab·playground·site-signals)을 확정한다. site-signals 등 타 세션 작업 중 route는 소유자 확인 후 분류.
- 옮길 파일 목록과 유지할 파일 목록을 확정한다.
- **terminal 의존 폐쇄(closure)를 실측으로 확정한다.** 알려진 최소 폐쇄(사전 실측): `$lib/data/hfRange`(govPrice·macroSeries·priceSeries·reportSeries·terminalFinance 5파일), `$lib/data/dartlabData`(2), `$lib/data/{productIndexRuntime,companyFilingsRuntime,companyNonRegularFilings}`, `$lib/browser/companyLive`, `$lib/scan/duckSql`, `$lib/components/viewer/{ViewerStudio,FinanceDialog}`, `$lib/brand`(2), `$lib/components/GithubIcon.svelte`, `$app/paths`(3) + `$app/environment`(10), `lib/styles/{v2-tokens,tokens}.css`(ui/web 직접 import).
- **포트 설계 초안 = `terminal/data/workbench.ts` export 표면 + `localAdapter.ts` 25메서드의 합집합**으로 잡는다. ui/web vite shim 목록은 보조 증거일 뿐 — shim은 5모듈뿐이고 hfRange/dartlabData는 블랭킷 `$lib` alias로 landing 원본이 로컬에서 그대로 실행되는 비가시 경로다.
- **`ui/shared` 사용처 census + 처분 결정(운영자).** 실측(2026-06-13): landing·ui/web 모두 실제 import 0 — alias 배선(3곳)과 주석만 잔존. 무사용분은 흡수가 아니라 별도 처분(폐기/보존) 결정. 단 ChartRenderer는 Skill OS viz 계약·메모리 정본이 참조하므로 즉시 삭제 금지 — 처분 시 참조 문서 동시 갱신.
- `ui/node_modules`, `ui/build` 스트레이 디렉토리 처분을 결정한다.
- `ui/web`, `landing`, Python server SPA, PyPI wheel 포함 경로를 표로 고정한다.
- 공개 route, legacy shim, adapter 후보, feature flag 후보를 기록한다.

산출:

- `06-inventory-and-freeze-template.md` 작성 완료
- migration inventory table (의존 폐쇄 포함)
- import graph report
- landing + ui/web 무중단 영향표

검증:

- 코드 변경 최소
- build 영향 없음
- `landing` 공개 route 목록 보존

### 단계-1a: npm 워크스페이스 기반 (독립 작업 단위)

목표:

- repo 루트 `package.json` + `workspaces = ["landing", "ui/packages/*", "ui/apps/local"]` 신설 (01 §2.1).
- lockfile 루트 단일화 — `landing/package-lock.json` 삭제.
- `.github/workflows/deploy-landing.yml` 설치/캐시 경로 개정 (루트 `npm ci` + `npm run build -w landing`).
- `.github/dependabot.yml` npm directory `/landing` → 루트.
- `landing/vite.config.ts` d3 모듈해석 alias 핵 제거 (호이스팅이 원인 해소).
- `ui/node_modules`, `ui/build` 스트레이 선청소.

검증:

- landing build green + GitHub Pages artifact smoke
- `ui/web` 단독 `npm ci` 후 빌드 재현 (워크스페이스 오염 차단)
- Windows/OneDrive: junction 생성 + `npm ci` 2회 연속 재현성 + node_modules 동기화 제외 확인
- svelte 정확 버전 단일 고정 확인

### 단계-1b: `ui/packages/contracts`

목표:

- Company, Filing, Price, Finance, Viewer, AI, Runtime 타입 계약 생성
- public/local이 공유할 최소 타입 정의 — Port 메서드는 required (optional 메서드 금지, 02 §3)
- AiCapabilities 3-티어 계약 (02 §4)
- adapter 반환 metadata 기준 추가
- AG-UI allowlist 이벤트와 Evidence 표시 계약 분리

범위:

```text
ui/packages/contracts/**
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
- **ui/web 로컬 터미널 smoke** — ui/web이 `landing/src/lib/styles/{v2-tokens,tokens}.css`를 상대경로 deep import 중이라 토큰 이동 시 즉사 경로. 이동 시 ui/web import 재배선 동반.

### 단계-4a: Terminal 데이터 계층 포트화 (제자리 — 제품 작업과 병행 가능)

목표:

- 파일 이동 없이, `landing/src/lib/terminal` 내부의 데이터 접근을 port 계약 뒤로 모은다.
- `localTerminalAdapter()?.x() ?? HF로드()` silent fallback 패턴과 `window.__DARTLAB_LOCAL_TERMINAL__` 전역 locator(13개 파일 참조)를 철거하고 runtime context 주입으로 대체한다.
- **terminal → viewer 역방향 의존을 주입 계약으로 역전한다** — RightStack→FinanceDialog, ViewerOverlay→ViewerStudio dynamic import가 현존하며, 단계-4b(이동)가 단계-6(viewer 추출)보다 앞이므로 역전 없이 이동하면 즉시 surfaces→landing/src 금지 의존이 생긴다. ViewerHost port 또는 snippet 주입으로 해소.
- HF/static fetch와 `$app/*` 의존(13개 파일)을 어댑터 구현으로 내린다.

범위:

```text
landing/src/lib/terminal/** 제자리 수정
ui/packages/runtime public/local adapter 구현
```

검증:

- landing terminal route 동작 + ui/web 로컬 터미널 smoke (양쪽 무중단)
- 전역 locator 참조 0
- silent fallback 패턴 0 (port required 검사)
- console error 0

### 단계-4b: Terminal Surface 이동 (이동 원자 윈도우 — §2.5)

목표:

- `landing/src/lib/terminal/**`을 `ui/packages/surfaces/src/terminal/**`로 이동한다 — 기능 변경 없는 기계적 이동만.
- landing terminal route는 wrapper로 전환한다.
- **ui/web의 `$lib`/deep import alias를 `ui/packages` 파일경로 alias로 재배선한다** (ui/web은 워크스페이스 밖 — 패키지명 해석 불가).
- **`.github/workflows/deploy-landing.yml`의 `on.push.paths`에 `ui/packages/**`를 추가한다** — 누락 시 이후 터미널 수정이 공개 사이트에 영영 반영되지 않는 silent 동결이 기본값이 된다.
- 좌측 탐색/검색/필터, 중앙 chart/시각화/fullscreen, 우측 공시/service panel 구조를 계약으로 고정한다.
- 우측 stack에는 graph를 배치하지 않는다.

순서 결정 기록: "단계-5(로컬 scaffold)를 migration alias로 선행해 가치를 먼저 내고 이동을 미루는" 대안은 기각 — `ui/web`이 이미 로컬 터미널을 제공 중이라 가치 공백이 없고, landing 내부의 세 번째 소비자(접착 코드)를 신설하게 되기 때문. 추출 우선이 정공법.

검증:

- public terminal route 동작 + **ui/web 로컬 터미널 동작** (양쪽 무중단)
- local fake runtime terminal render
- console error 0
- screenshot diff 허용 범위 내
- terminal ready/loading/empty/error 상태 screenshot
- chart canvas nonblank pixel 검사
- deploy-landing paths 필터 갱신 확인

### 단계-5: Local SvelteKit App Scaffold — 가치 도달점 V1 (로컬 SvelteKit 터미널 첫 구동)

목표:

- `ui/apps/local` 생성 — landing과 동일 툴체인(Vite 8 계열, svelte 정확 고정)
- local runtime adapter 연결 (AI는 `/api/agent/*` 경유)
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

### 단계-6: Viewer Surface Extraction (이동 원자 윈도우 — §2.5)

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

### 단계-7: AI Surface Integration — 가치 도달점 V2 (로컬 고급 Ask 챗+터미널)

목표:

- Viewer Ask drawer와 Terminal AI command layer를 `AiPort` 뒤에 연결
- public = deterministic(항상) + onDevice(WebGPU 가용 시) — 02 §4 3-티어
- local = advanced (src/dartlab/ai Ask 엔진, provider 직접 연결)
- Ask 엔진 기반 chat/terminal mode 공통화
- raw trace, raw tool args/result, 내부 tool id는 Evidence panel로 분리

검증:

- provider 없음: graceful — deterministic tier 로 동작 + upgradeHint
- provider 있음: stream response
- **공개 온디바이스(WebGPU)·결정론 경로 무회귀 — 출시된 공개 AskDrawer 기준**
- selected evidence context 전달
- tool call 실패 표시
- AG-UI allowlist 외 이벤트 렌더 금지
- 챗모드와 터미널모드가 같은 Ask engine contract 사용

### 단계-8: Services + 잔여 제품 Surface 추출 (이동 원자 윈도우 — §2.5)

목표:

- 회사 화면, charting, evidence UI 공용화
- **scan(탐색기·SQL 노트북·ScreenBuilder)·screener·map/industry·search + 단계-0 분류 확정분(changes·insights 등) surface 추출** — 01 §4.1 전수 지도의 잔여 제품 작업면 전부. 터미널·뷰어만 옮기고 끝나지 않는다.
- terminal/chart/viewer 간 상태 규칙 정리
- `ServicesPort` command registry 구현 (localOnly descriptor + upgradeHint 포함)
- ChartSpec -> ChartRenderer 단일 경로
- `ui/shared` 처분 집행 — 단계-0 census의 운영자 결정에 따라 흡수 또는 폐기. 폐기 시 `$chart` alias 배선(landing svelte.config·vite.config, ui/web vite.config) 제거 + ChartRenderer 정본 참조 문서(메모리·Skill OS) 동시 갱신
- 가격 상승/하락, good/bad, brand 색 의미를 token에서 분리

검증:

- company page public/local
- price chart controls
- chart state persistence
- no duplicated chart CSS
- service command palette
- chart toolbar, tooltip, axis 표시
- tabular-nums와 단위 표시 일관성

### 단계-9: Landing Public Shell 전환 완료 (이동 원자 윈도우 — §2.5)

> `ui/apps/public`은 비채택(01 §3.2) — landing이 영구 public shell이다. 이 단계는 새 앱 신설이 아니라 landing 제품 route를 packages 기반 wrapper로 전환 완료하는 단계다.

목표:

- landing의 모든 제품 route(terminal/viewer/company)가 `ui/packages/surfaces` + public adapter wrapper로 동작
- `landing/src/lib`에 제품 UI 원본 잔재 0 (content/seo/publicShell만 잔존)
- `landing` content route는 그대로 유지
- 공개 URL 안정성을 확인한 뒤에만 기본 route 변경

검증:

- GitHub Pages build artifact 구조
- base path
- deep link refresh
- static asset path
- 기존 content route smoke
- 기존 product URL redirect 또는 compatibility wrapper 확인
- viewer/company prerender entry 보존 (svelte.config viewerEntries)

### 단계-10: Local App Default Switch

목표:

- Python server 기본 UI를 `ui/apps/local`로 전환
- 기존 `ui/web` fallback flag 유지
- `resolveUiBuildDir`, `serveSpa`, asset 404/cache 동작 검증
- PyPI wheel에 local SvelteKit build 산출물 포함

명시 범위 (하드코딩 4파일 — 누락 시 wheel 사고):

```text
.github/workflows/publish.yml      # 현행: cd ui/web && npm ci && vite build → src/dartlab/ui/build 복사 하드코딩
src/dartlab/server/_ui_path.py     # dev 우선순위에 ui/apps/local/build 추가 + 죽은 경로(ui/web/client/dist) 제거
pyproject.toml hatch artifacts     # src/dartlab/ui/build/** 포함 패턴 확인
tests/ wheel smoke 스크립트         # testWheelSmoke/verifyWheel 류 — local app 기준으로 갱신
```

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
단계-0   Inventory and Boundary Map          (병행 가능)
단계-1a  npm workspace 기반                   (병행 가능)
단계-1b  contracts package                    (병행 가능)
단계-2   runtime ports, fake runtime, services skeleton  (병행 가능)
단계-3   design tokens and primitives         (병행 가능 — 단 styles 이동 시 ui/web smoke)
단계-4a  terminal 데이터 계층 포트화 (제자리)   (병행 가능)
단계-4b  terminal surface 이동                 [이동 원자 윈도우]
단계-5   local SvelteKit scaffold             (병행 가능) ← 가치 V1: 로컬 SvelteKit 터미널
단계-6   viewer surface extraction            [이동 원자 윈도우]
단계-7   AI runtime integration               (병행 가능) ← 가치 V2: 로컬 고급 Ask
단계-8   services + 잔여 제품 surface 전부      [이동 원자 윈도우]
         (company·chart·evidence·scan·screener·map·search·changes·insights)
단계-9   landing public shell 전환 완료        [이동 원자 윈도우]
단계-10  local app default switch
단계-11  ui/web legacy removal
```

가치 도달점 주석: `ui/web`이 전 기간 로컬 터미널을 제공하므로(무중단 대상) 가치 공백은 없다. V1(단계-5)=로컬 SvelteKit 터미널 첫 구동, V2(단계-7)=로컬 고급 Ask 챗+터미널 — funnel의 flagship 가치가 프로그램 중반에 전달된다.
