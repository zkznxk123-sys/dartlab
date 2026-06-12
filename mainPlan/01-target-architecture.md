# 01. Target Architecture

상태: v1 확정 기준 문서  
범위: 앱, 패키지, 폴더 구조, 의존성, export, alias, naming 규칙

---

## 1. 최종 구조 원칙

1. `landing`은 공개 콘텐츠 앱이면서 영구 public shell이다 — 제품 route의 얇은 wrapper와 public adapter 배선을 소유한다.
2. `ui/apps/public`은 신설하지 않는다(비채택, §3.2). 별도 도메인/배포 분리 필요가 실제 발생할 때만 재개한다.
3. `ui/apps/local`은 로컬 SvelteKit 앱이다.
4. `ui/web`은 legacy fallback이다 — 물리 이동 없이 제자리 동결.
5. 공용 제품 UI 원본은 `ui/packages` 아래에만 둔다.
6. public/local 차이는 adapter로 해결한다.
7. 앱 내부 구현을 다른 앱이 직접 import하지 않는다.
8. npm 워크스페이스는 repo 루트에 둔다(§2.1). `ui/web`은 워크스페이스 밖이다.

---

## 2. 최상위 폴더 구조

```text
dartlab/
  package.json            # npm 워크스페이스 루트 (workspaces: landing, ui/packages/*, ui/apps/local)
  package-lock.json       # 단일 lockfile (landing/package-lock.json 은 워크스페이스 전환 시 삭제)

  landing/                # 공개 콘텐츠 앱 + 영구 public shell (GitHub Pages)
    src/
      routes/             # blog/docs/legal/static + 제품 route wrapper (terminal/viewer/company)
      lib/                # content, seo, publicShell — 제품 UI 원본은 단계적으로 ui/packages 로 승격
    static/
    package.json

  ui/
    tsconfig.base.json
    apps/
      local/              # 로컬 SvelteKit 앱 (wheel 포함 build)
        src/
          routes/
            chat/
            terminal/[code]/
            ask/
            analysis/[code]/
            analysis/[code]/viewer/
            settings/providers/
            settings/workspace/
          lib/
            runtime/
            shell/
        package.json
    web/                  # React legacy — 물리 이동 금지, 제거 시까지 제자리 (워크스페이스 밖, 자체 lockfile)

    packages/
      contracts/
      runtime/
      design/
      surfaces/
      testing/            # 첫 conformance test 가 생길 때 생성 (빈 스캐폴딩 금지)

  mainPlan/
```

---

## 2.1 npm 워크스페이스 토폴로지

결정:

1. repo 루트 `package.json`에 `workspaces = ["landing", "ui/packages/*", "ui/apps/local"]`.
2. `ui/web`은 워크스페이스에서 제외한다 — frozen legacy, 자체 lockfile, Vite 6 잔존. 루트 node_modules 호이스팅으로 ui/web의 누락 의존성이 "우연히" 해석되는 오염을 막기 위해, `ui/web` 단독 `npm ci` 후 빌드 재현을 freeze 검증에 포함한다.
3. svelte는 워크스페이스에서 정확 버전(caret 금지)으로 단일 고정한다 — 두 앱이 같은 surface 소스를 다른 컴파일러로 빌드하는 fork를 봉인한다.
4. lockfile은 루트 단일이다. `landing/package-lock.json`은 전환 작업 단위에서 삭제한다.

전환 시 동반 변경 (누락 = silent 사고):

- `.github/workflows/deploy-landing.yml` — `working-directory: landing` + `npm ci`를 루트 `npm ci` + `npm run build -w landing`으로 개정, 캐시 경로 갱신.
- `.github/dependabot.yml` — npm directory `/landing` → 루트. 안 바꾸면 npm 의존성 감시가 조용히 죽는다.
- `landing/vite.config.ts`의 d3 모듈해석 alias 핵 제거 — 워크스페이스 호이스팅이 원인을 해소한다.
- `ui/node_modules`, `ui/build` 스트레이 디렉토리(package.json 없는 잔재) 선청소.

Windows/OneDrive 검증 항목 (repo가 OneDrive 경로 아래):

1. 워크스페이스 링크(junction) 생성 확인 — OneDrive 동기화와 `npm ci` rename 단계의 EPERM/EBUSY 충돌 여부.
2. `npm ci` 2회 연속 재현성.
3. node_modules의 OneDrive 동기화 제외 확인 (Files On-Demand dehydrate 가 vite cold start ENOENT 를 유발할 수 있다).

---

## 3. 앱 역할

### 3.1 `landing`

책임:

- public content
- blog/docs/legal/static route
- SEO, sitemap, metadata
- GitHub Pages build compatibility
- 리팩토링 중 기존 공개 route 유지
- **영구 public shell** — 제품 route의 얇은 wrapper + public adapter 배선 + GitHub Pages base path 처리

허용:

- `ui/packages/*` public export import (영구 — 과도기 한정 아님)
- 제품 route wrapper 유지
- 기존 공개 URL compatibility route

금지:

- `ui/apps/local` import
- local API 직접 호출
- AI provider secret 접근
- local file/workspace permission UI 노출
- 제품 UI **원본**을 장기적으로 소유 (wrapper 는 소유하되 원본은 packages)

수용 부채 (명시적 기록):

- landing build 비용 누적 — prerender 수천 entry + heap 8GB(`--max-old-space-size=8192`). 제품 wrapper가 더해져도 이 구조를 유지한다. build 시간이 운영 한계를 넘으면 그때 분리를 재검토한다.

### 3.2 `ui/apps/public` — 비채택 결정

신설하지 않는다.

근거:

- GitHub Pages 는 단일 artifact 배포다. 두 SvelteKit 정적 빌드 합성은 base path, 404.html fallback, prerender, asset 경로 충돌만 추가한다.
- landing 이 이미 viewer/company prerender, SEO, 무중단 기계를 검증된 상태로 갖고 있다.
- 원본이 `ui/packages`에 있는 한 "제품 UI 한 벌" 원칙은 landing wrapper 로도 충족된다.

재개 조건 (이때만 재논의):

- 제품 route를 별도 도메인 또는 별도 배포 주기로 분리할 실제 필요가 발생.
- landing build 비용이 운영 한계 초과.

### 3.3 `ui/apps/local`

책임:

- 로컬 SvelteKit 앱
- 챗모드와 터미널모드 shell
- Ask 엔진 진입점
- local runtime adapter 연결
- local API, local DB/cache, workspace context 연결
- AI provider 직접 연결
- service registry와 tool registry 연결
- Python package/wheel에 포함될 build 산출물 생성

대표 route:

```text
ui/apps/local/src/routes/
  +layout.svelte
  +page.svelte
  chat/+page.svelte
  terminal/[code]/+page.svelte
  ask/+page.svelte
  analysis/[code]/+page.svelte
  analysis/[code]/viewer/+page.svelte
  settings/providers/+page.svelte
  settings/workspace/+page.svelte
```

금지:

- `landing/src` import
- React `ui/web` import
- public/HF 전용 URL hardcode
- provider SDK를 surface로 전달
- surface CSS override로 구조를 억지로 맞추기

### 3.4 `ui/web` (legacy)

현재 위치 그대로 동결한다 — **물리 이동 금지**. 이동하면 `src/dartlab/server/_ui_path.py`의 dev 경로와 publish.yml 빌드 경로가 깨진다. 제거 시까지 제자리.

운영 규칙:

- 기존 사용자 fallback으로 유지한다. `ui/web` 로컬 터미널은 무중단 대상이다.
- 새 제품 기능을 추가하지 않는다.
- 보안, build, 치명 bug만 수정한다.
- 워크스페이스 밖 — `ui/packages` 소비는 패키지명 해석이 불가하므로 파일경로 alias로만 한다(과도기 재배선 한정).
- local SvelteKit이 feature parity에 도달하면 별도 제거 작업 단위로 처리한다.

제거 조건:

1. local app에서 chat, terminal, viewer, provider settings가 동작한다.
2. local app이 Python server packaging에 포함된다.
3. 기존 `/ask`, `/analysis/:code`, `/analysis/:code/viewer` 진입점 compatibility를 제공한다.
4. PyPI test install에서 local app이 정상 구동된다.
5. 2회 이상 릴리스에서 fallback 요청이 없다.

---

## 4. 공용 패키지 구조

```text
ui/packages/
  contracts/
    package.json
    src/
      index.ts
      company.ts
      filing.ts
      price.ts
      finance.ts
      viewer.ts
      ai.ts
      runtime.ts
      services.ts
      navigation.ts
      storage.ts
      source.ts
      errors.ts

  runtime/
    package.json
    src/
      index.ts
      createRuntime.ts
      runtimeContext.svelte.ts
      ports/
        companyPort.ts
        pricePort.ts
        filingPort.ts
        financePort.ts
        viewerPort.ts
        aiPort.ts
        servicesPort.ts
        navigationPort.ts
        storagePort.ts
        telemetryPort.ts
      services/
        serviceRegistry.ts
        toolRegistry.ts
        serviceContracts.ts
      adapters/
        public/
          createPublicRuntime.ts
          hfDataClient.ts
          staticAssetClient.ts
          publicViewerAdapter.ts
          publicAiAdapter.ts
          publicServiceAdapter.ts
        local/
          createLocalRuntime.ts
          localApiClient.ts
          localViewerAdapter.ts
          localAiAdapter.ts
          localServiceAdapter.ts
          localStorageAdapter.ts
        test/
          createFakeRuntime.ts
      cache/
        runtimeCache.ts
        requestDedup.ts

  design/
    package.json
    src/
      index.ts
      styles/
        reset.css
        tokens.css
        semantic.css
        aliases.css
        terminal.css
        viewer.css
        app-shell.css
      tokens/
        color.ts
        spacing.ts
        typography.ts
        zIndex.ts
        chart.ts
        motion.ts
      components/
        Button.svelte
        IconButton.svelte
        Panel.svelte
        Toolbar.svelte
        SplitPane.svelte
        SegmentedControl.svelte
        Tabs.svelte
        Tooltip.svelte
        Drawer.svelte
        Dialog.svelte
        CommandPalette.svelte
        DataTable.svelte
        ChartFrame.svelte
        ProvenanceTag.svelte
        MetricCell.svelte

  surfaces/
    package.json
    src/
      index.ts
      terminal/
      viewer/
      company/
      scan/        # DataExplorer · SQL 노트북 · ScreenBuilder (landing lib/scan 36파일)
      map/         # industry map (/map, /industry/[code])
      charting/
      evidence/
      search/
      ask/

  testing/
    package.json
    src/
      fixtures/
      assertions/
      visual/
```

### 4.1 제품 작업면 전수 지도 (헷갈림 방지 단일 표)

> 경계 원칙(00 §2-11): 콘텐츠 자산(blog/docs/about/skills/legal/SEO/static) 빼고 전부 제품. 이 표가 "무엇이 어디로 가는가"의 단일 참조다. 단계-0 인벤토리에서 빈칸·분류 미정 행을 확정한다.

| 작업면 | 공개 route | surface | 주 port | 추출 단계 |
|---|---|---|---|---|
| 터미널 | /terminal/[code] | TerminalSurface | company·price·filing·finance | 4a/4b |
| 공시뷰어 | /viewer/company/[code] | ViewerSurface | filing·viewer | 6 |
| 뷰어 N사 비교 | /compare, ?vs= | ViewerSurface(compare) | filing | 6 |
| Ask(챗·drawer) | 뷰어/터미널 내 + 로컬 /chat | AskSurface | ai | 7 |
| 회사 | terminal/viewer 연계 | CompanySurface | company | 8 |
| 스캔(탐색기·SQL 노트북) | /scan | ScanSurface | scan | 8 |
| 스크리너 | /screener | ScanSurface(ScreenBuilder) | scan | 8 |
| 맵/산업 | /map, /industry/[code] | MapSurface | map | 8 |
| 통합 검색 | /search | SearchSurface | search | 8 |
| 변경 피드 | /changes | 단계-0 분류 | filing | 8 |
| 인사이트 피드 | /insights | 단계-0 분류 | scan | 8 |
| embed/lab/playground/site-signals | 각 route | 단계-0 분류 (site-signals=타 세션 작업 중, 소유자 확인) | — | 단계-0 결정 |

---

## 5. 의존성 규칙

허용:

```text
contracts -> none
design -> contracts optional only
runtime -> contracts
surfaces -> contracts, runtime, design
ui/apps/local -> ui/packages/*
landing -> ui/packages/* (영구 — public shell)
ui/web -> ui/packages/* (과도기 파일경로 alias 재배선만, 신규 기능 금지)
```

금지:

```text
contracts -> runtime/design/surfaces/apps
design -> runtime/surfaces/apps
runtime -> surfaces/apps
surfaces -> apps/*
surfaces -> landing/src/*
surfaces -> ui/web/*
apps/local -> landing/src
landing -> ui/apps/local
ui/web -> landing/src (단계-4b 재배선 후 금지 — 그 전까지는 현행 bridge 유지)
```

---

## 6. Package Public Export 규칙

모든 공용 패키지는 `src/index.ts`와 명시적 subpath export만 공개 API로 인정한다.

허용:

```ts
import { TerminalSurface } from '@dartlab/ui-surfaces/terminal';
import type { DartLabRuntime } from '@dartlab/ui-contracts';
import { createLocalRuntime } from '@dartlab/ui-runtime/local';
```

금지:

```ts
import TerminalSurface from '../../packages/surfaces/src/terminal/TerminalSurface.svelte';
import { localApiClient } from '@dartlab/ui-runtime/src/adapters/local/localApiClient';
```

각 패키지는 `package.json`에서 export boundary를 명확히 선언한다.

### 6.1 Raw Svelte Source Export 규칙

surfaces/design 패키지는 빌드 산출물이 아니라 `.svelte` 원소스를 export 한다 — 각 앱이 자기 툴체인으로 컴파일한다.

1. exports map 은 subpath 마다 `svelte` + `types` condition 을 선언한다.

```json
{
  "exports": {
    "./terminal": {
      "types": "./src/terminal/index.d.ts",
      "svelte": "./src/terminal/index.ts",
      "default": "./src/terminal/index.ts"
    }
  }
}
```

2. 소비 앱 tsconfig 는 `moduleResolution: "bundler"` — 아니면 svelte-check 가 exports 를 못 푼다.
3. `.svelte.ts` rune 모듈(예: chartState.svelte.ts)도 export 표면에 포함된다.
4. surfaces 내부에 `$lib/*`, `$app/*` import 가 남아 있으면 export 불가 — 이동 전 전수 치환이 전제다(단계-4a 작업량의 본체).
5. 패키지는 자체 tsconfig + 고정 TypeScript 버전으로 svelte-check 한다 (앱별 TS 버전 분기와 무관하게).
6. svelte 컴파일러 버전은 워크스페이스 정확 고정으로 단일화한다 — landing(Vite 8 + vite-plugin-svelte 7)과 ui/apps/local 은 같은 메이저를 쓴다. ui/web(Vite 6 + vite-plugin-svelte 5)은 워크스페이스 밖이라 이 메커니즘이 적용되지 않으므로 파일경로 alias 소비만 허용한다.

---

## 7. 임시 Alias 정책

마이그레이션 중 기존 import를 한 번에 모두 바꾸기 어려울 수 있다. 임시 alias는 허용하되 조건을 둔다.

허용 조건:

1. alias 이름에 `legacy` 또는 `migration`을 포함한다.
2. 제거 목표 작업 단위 번호를 주석으로 남긴다.
3. alias는 app wrapper에서만 사용한다.
4. package 내부에서는 alias를 쓰지 않는다.
5. alias 추가 작업 단위와 제거 작업 단위를 `04-migration-execution-plan.md`에 기록한다.

허용 예:

```ts
// 단계-4 동안만 허용, 단계-6 전에 제거
'@dartlab/migration-landing-terminal': '../../landing/src/lib/terminal'
```

금지:

```ts
'$lib': '../../landing/src/lib'
'@shared': '../../somewhere'
```

제거 조건:

- 해당 surface가 `ui/packages/surfaces`로 이동 완료
- public/local adapter가 모두 해당 surface를 사용
- visual smoke 통과
- alias에 의존하는 import 0개

---

## 8. Naming 규칙

폴더명:

- `contracts`: 타입과 계약만
- `runtime`: port, adapter, context, cache
- `design`: token, primitive, CSS boundary
- `surfaces`: product UI surface
- `testing`: fixture, assertion, visual harness
- `apps`: deployable shell

금지 이름:

```text
common
shared2
utils2
new
old
temp
misc
bridge-final
```

허용 helper 예:

```text
viewerSearchIndex.ts
terminalSelectors.ts
priceMath.ts
filingNormalize.ts
```
