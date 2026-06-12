# 01. Target Architecture

상태: v1 확정 기준 문서  
범위: 앱, 패키지, 폴더 구조, 의존성, export, alias, naming 규칙

---

## 1. 최종 구조 원칙

1. `landing`은 공개 콘텐츠 앱이다.
2. `ui/apps/public`은 필요 시 공개 제품 route shell이 된다.
3. `ui/apps/local`은 로컬 SvelteKit 앱이다.
4. `ui/web`은 legacy fallback이다.
5. 공용 제품 UI 원본은 `ui/packages` 아래에만 둔다.
6. public/local 차이는 adapter로 해결한다.
7. 앱 내부 구현을 다른 앱이 직접 import하지 않는다.

---

## 2. 최상위 폴더 구조

```text
dartlab/
  landing/
    src/
      routes/
        blog/
        docs/
        health/
        legal/
        static-content-only/
      lib/
        content/
        seo/
        publicShell/
    static/
    package.json

  ui/
    package.json
    tsconfig.base.json
    apps/
      public/
        src/
          routes/
            terminal/[code]/
            company/[code]/
            viewer/[code]/
          app.html
        package.json
      local/
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
      web-legacy/
        README.md

    packages/
      contracts/
      runtime/
      design/
      surfaces/
      testing/

  mainPlan/
```

---

## 3. 앱 역할

### 3.1 `landing`

책임:

- public content
- blog/docs/legal/static route
- SEO, sitemap, metadata
- GitHub Pages build compatibility
- 리팩토링 중 기존 공개 route 유지

허용:

- 과도기 동안 `ui/packages/*` public export import
- 제품 route wrapper 유지
- 기존 공개 URL compatibility route

금지:

- `ui/apps/local` import
- local API 직접 호출
- AI provider secret 접근
- local file/workspace permission UI 노출
- 제품 UI 원본을 장기적으로 소유

### 3.2 `ui/apps/public`

책임:

- 공개 제품 route shell
- public adapter 연결
- GitHub Pages base path 처리
- static/HF/public-safe 데이터 연결

금지:

- local adapter import
- provider settings 노출
- workspace/session 권한 UI 노출
- local-only service command 노출

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

### 3.4 `ui/apps/web-legacy`

현재 `ui/web`의 장기 위치 또는 역할이다.

운영 규칙:

- 기존 사용자 fallback으로 유지한다.
- 새 제품 기능을 추가하지 않는다.
- 보안, build, 치명 bug만 수정한다.
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

---

## 5. 의존성 규칙

허용:

```text
contracts -> none
design -> contracts optional only
runtime -> contracts
surfaces -> contracts, runtime, design
ui/apps/local -> ui/packages/*
ui/apps/public -> ui/packages/*
landing -> ui/packages/* during migration
```

금지:

```text
contracts -> runtime/design/surfaces/apps
design -> runtime/surfaces/apps
runtime -> surfaces/apps
surfaces -> apps/*
surfaces -> landing/src/*
surfaces -> ui/web/*
apps/public -> apps/local
apps/local -> apps/public
landing -> ui/apps/local
landing -> ui/apps/public internals
ui/web -> landing/src
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
