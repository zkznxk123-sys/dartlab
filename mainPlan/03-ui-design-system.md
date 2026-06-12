# 03. UI Design System

상태: v1 확정 기준 문서  
범위: 공용 Svelte surface, terminal/viewer UX, 디자인 토큰, CSS 경계, 접근성, 시각 회귀

---

## 1. Surface 원칙

Surface는 사용자에게 하나의 독립 화면 경험을 제공하는 UI 단위다.

예:

- `TerminalSurface`
- `ViewerSurface`
- `CompanySurface`
- `ScreenerSurface`
- `AskSurface`

규칙:

1. Surface는 app shell이 아니다.
2. Surface는 route를 소유하지 않는다.
3. Surface는 runtime과 props만 받아 동작한다.
4. 모든 surface는 host 앱 없이 fake runtime fixture로 렌더 가능해야 한다.
5. public/local 차이로 surface를 fork하지 않는다.
6. route, server, static host, local API, provider, workspace 권한을 직접 알지 않는다.
7. **열화 티어 표시 원칙** — 승격 가능(또는 로컬 전용 상위) 기능은 public에서 숨기지 않는다. tier badge + `upgradeHint`("로컬에서 더 강력함") + 설치 CTA로 표시한다. 완전 숨김은 cache refresh 같은 시스템 명령에만 허용한다. funnel은 공개 사용자가 로컬의 우위를 "봐야" 작동한다.

---

## 2. Surface API 규칙

1. Svelte 5 typed `$props`를 표준으로 한다.
2. URL에 반영되는 상태는 controlled props로 받는다.
3. `code`, `period`, `vs`, `mode`, `fullscreen` 같은 route state는 surface 내부 전역 상태로 숨기지 않는다.
4. hover, popover open, temporary flash 같은 순수 UI 상태만 surface 내부에서 소유한다.
5. boolean prop 증식을 금지한다.
6. `variant`, `density`, `tone`, `provenance`, `status` 같은 enum 또는 discriminated union을 사용한다.
7. slot/snippet은 `header`, `right`, `footer`, `emptyState`처럼 구조가 명확한 확장에만 허용한다.
8. 빈 데이터는 `empty`, `unavailable`, `stale`, `error` 상태로 드러낸다.
9. 가짜 fallback 데이터를 정상 화면처럼 렌더하지 않는다.

---

## 3. TerminalSurface

입력:

```ts
export interface TerminalSurfaceProps {
  initialCode?: string;
  runtime: DartLabRuntime;
  mode?: 'full' | 'embedded';
  locale?: 'ko' | 'en';
}
```

책임:

- landing terminal UX의 원본 역할
- company selection
- price chart
- financial panels
- right disclosure/service panels
- regular filing fullscreen viewer overlay
- source/provenance badge
- local/public runtime에 따른 링크 생성
- 좌측 탐색/검색/필터
- 중앙 chart/시각화/fullscreen
- 우측 정기공시/정성 정보/service panel
- Ask 모드에서 terminal mode 클릭 시 별도 탭 없이 full terminal 화면 진입

금지:

- 직접 HF fetch
- 직접 local API fetch
- 직접 SvelteKit route import
- local-only AI UI hardcode
- 우측 stack에 graph 배치
- service 구현 import

레이아웃:

```text
TerminalSurface
  LeftRail
    company search
    recent companies
    filters
    command entry

  CenterStack
    chart frame
    financial summary
    fullscreen analysis
    selected service work area

  RightStack
    regular filings
    non-regular filings
    evidence/source
    service status
    viewer quick panel
```

---

## 4. ViewerSurface

입력:

```ts
export interface ViewerSurfaceProps {
  code: string;
  runtime: DartLabRuntime;
  embedded?: boolean;
  initialPeriod?: string;
  initialSectionKey?: string;
}
```

책임:

- DART panel TOC/grid 표시
- period timeline
- section navigation
- text/table rendering
- evidence selection
- compare matrix
- optional Ask drawer
- route 이동은 `runtime.navigation` 또는 `onNavigate`로 위임

AI 동작:

- `runtime.ai.capabilities().tier`에 따라 단계적으로 렌더한다 — `deterministic`: 결정론 Q&A(항상, public 포함) / `onDevice`: + WebGPU 온디바이스 대화 / `advanced`: + 로컬 엔진 스트리밍·tool calling.
- `advanced` 미만 tier에서는 `upgradeHint`로 로컬 업그레이드를 안내한다 — Ask drawer 를 숨기지 않는다.
- 이미 출시된 공개 AskDrawer(Tier0 + WebGPU) 동작의 회귀 금지.
- selected paragraph/table/period를 evidence로 전달

---

## 5. CompanySurface와 Charting

CompanySurface 책임:

- 공개 회사 페이지와 로컬 회사 summary가 같은 구조를 공유
- terminal과 viewer로 자연스럽게 이동
- SEO는 public app wrapper가 처리

Charting 책임:

- price chart
- mini financial chart
- chart toolbar
- compare overlay
- economic overlay
- drawing state

Charting 원칙:

- chart state는 runtime storage key로 저장
- chart library는 surface 내부 구현 detail
- data는 `PricePort`/`FinancePort`를 통해 공급
- ChartSpec -> ChartRenderer 단일 경로를 유지
- canvas chart는 nonblank pixel 검사 대상

---

## 6. 디자인 토큰

원칙:

1. public/local 디자인 토큰은 동일해야 한다.
2. surface별 CSS는 `ui/packages/design` 토큰을 사용한다.
3. app별 override는 layout shell 수준으로 제한한다.
4. terminal, viewer, company, ask는 같은 제품 계열이어야 한다.
5. 색, typography, spacing, radius, panel border, z-index를 임의 재정의하지 않는다.

토큰 파일:

```text
ui/packages/design/src/styles/
  reset.css
  tokens.css
  semantic.css
  aliases.css
  terminal.css
  viewer.css
  app-shell.css
```

토큰 계층:

```text
primitive token
  --color-gray-950
  --color-red-500
  --space-1
  --font-mono

semantic token
  --dl-surface-bg
  --dl-surface-panel
  --dl-text-primary
  --dl-line-subtle
  --dl-focus-ring
  --surface-bg
  --panel-bg
  --panel-border
  --text-primary
  --text-muted
  --accent-danger
  --accent-positive

surface token
  --terminal-bg
  --terminal-panel-bg
  --viewer-document-bg
  --chart-grid
```

규칙:

1. `--dl-*`를 원천 토큰으로 삼는다.
2. Tailwind, shadcn, legacy 변수는 `aliases.css`에서만 매핑한다.
3. 브랜드 빨강, 가격 상승/하락, good/bad 의미 색은 분리한다.
4. 한국 시장 가격 convention은 `price.up`, `price.down` 계열에서만 처리한다.
5. radius는 4px, 8px, 12px 중심으로 제한한다.
6. 숫자는 `tabular-nums`를 기본으로 한다.
7. motion은 180ms, 240ms, 320ms 토큰만 사용한다.
8. `prefers-reduced-motion`을 지원한다.
9. 토큰 정의 파일 외 inline hex/rgb 색상 추가를 금지한다.

---

## 7. Primitive Component

공용 primitive:

- `Button`
- `IconButton`
- `Panel`
- `Toolbar`
- `SplitPane`
- `SegmentedControl`
- `Tabs`
- `Tooltip`
- `Drawer`
- `Dialog`
- `CommandPalette`
- `DataTable`
- `ChartFrame`
- `ProvenanceTag`
- `MetricCell`

규칙:

1. surface 내부에서 유사 버튼을 새로 만들지 않는다.
2. Svelte surface icon은 `lucide-svelte` 기준이다.
3. 도구 버튼은 `IconButton` + tooltip을 사용한다.
4. local app shell이 React/shadcn 스타일을 surface에 주입하지 않는다.
5. 카드 안에 카드 중첩을 금지한다.
6. terminal panel radius, border, padding은 design token으로 고정한다.
7. 반복 data card 외에는 페이지 섹션을 card처럼 감싸지 않는다.
8. 공용 primitive 이름과 API는 public/local에서 동일해야 한다.

---

## 8. CSS 경계

1. 공용 surface 스타일은 `.dlSurface` 또는 surface별 root scope 아래에서만 적용한다.
2. global CSS는 reset, font, token alias, scrollbar, raw HTML table 렌더에만 둔다.
3. Tailwind utility는 layout과 spacing 보조로만 사용한다.
4. 색, typography, 상태 표현은 token 기반 class로 고정한다.
5. shell CSS가 surface 내부 grid, panel width, chart frame, viewer fullscreen sizing을 override하지 않는다.
6. public/local 화면 차이는 shell wrapper에서 해결하고 surface CSS를 fork하지 않는다.

---

## 9. 접근성 기준

필수:

1. 모든 클릭 가능한 요소는 실제 `button` 또는 `a`를 우선 사용한다.
2. 불가피한 `role="button"`은 Enter와 Space를 모두 지원한다.
3. `Cmd/Ctrl+K`, `/`, `Escape`, 방향키, Tab 이동 경로를 e2e로 검증한다.
4. dialog, drawer, fullscreen viewer는 focus trap, focus restore, inert background, Escape close를 지원한다.
5. loading, stale, error, soft swap 상태는 `aria-live` 또는 명확한 status 영역으로 노출한다.
6. 상승/하락/위험 상태는 색만으로 표현하지 않는다.
7. 본문 텍스트 contrast는 WCAG 4.5:1 이상이다.
8. UI 경계/상태 contrast는 3:1 이상이다.
9. 모바일 터치 타깃은 최소 44px이다.
10. 데이터 표는 모바일에서 가로 스크롤과 sticky 기준열을 유지한다.
11. command palette는 keyboard-only 사용자가 terminal service command를 모두 실행할 수 있어야 한다.

---

## 10. 시각 회귀 기준

필수 viewport:

- desktop: 1440x900
- desktop compact: 1280x720
- tablet: 1024x768
- mobile: 390x844
- wide: 1920x1080

필수 screenshot:

- public terminal ready/loading/empty/error
- local terminal ready/loading/empty/error
- terminal regular filing fullscreen viewer
- viewer embedded mode
- viewer standalone mode
- viewer compare mode
- viewer ask drawer open
- chat to terminal transition
- provider disabled public mode
- provider enabled local mode
- command palette

합격 기준:

- console error 0
- Svelte warning 0
- 주요 영역 blank 금지
- panel overlap 금지
- button text overflow 금지
- viewer iframe/component height 100% 유지
- public/local terminal의 주요 layout 차이 없음
- chart canvas nonblank
- tooltip, axis, toolbar 표시
