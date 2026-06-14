# 01 — 공유 투어 엔진 아키텍처 (★핵심)

> 이 문서가 "혁신적·유지보수 편리·공통배선" 요구의 본체다. 결론: map의 606줄 `TutorialTour.svelte`는 *엔진(로직) + 콘텐츠(STEPS) + map전용 prop 8개*가 한 파일에 융합돼 재사용 불가다. **엔진/콘텐츠/배선을 3분리**하고 콘텐츠를 surface별 데이터로 외부화하는 게 유일한 정공법.

## 0. 적대 해소 — "지금 추출" vs "복제 후 추출"

| 렌즈 | 주장 |
|---|---|
| 아키텍처 | 지금 공유 엔진으로 추출. 600줄 컴포넌트 2벌 복제 = 버그픽스 2번·드리프트. |
| 레드팀 | 복제 먼저, 패턴 안정 후 추출. 섣부른 추상화 = no-graph-regression 위험. |

**해소 = 추출하되, 레드팀 가드를 전부 박는다.** 근거:
- 사용자가 **명시적으로 "혁신적·유지보수 편리·공통배선"**을 요구했다 — 600줄 2벌 복제는 그 요구의 *정반대*다.
- 추상화 경계가 이미 *보인다*: 정확히 2 surface(map+terminal) + 명백한 3번째 후보(viewer·company). "rule of three"의 불확실성이 없다.
- 레드팀의 진짜 우려는 *과(過)추상화*(StepGraph/OnboardingKernel/디스패처)지 단순 데이터-주도 엔진이 아니다. 그 우려를 **하드 가드**로 흡수한다(§5·§6):
  - 엔진은 `Step[] 데이터 + spotlight 1컴포넌트`에서 못 벗어난다. 그래프/커널/노드/디스패처 신설 = reject.
  - map은 *얇은 어댑터 뒤*로 축소 → landing 계약 무변경 = **회귀 표면 0**(레드팀의 "복제 안정성" 요구를 마이그레이션 순서로 충족).
  - localStorage 키 상한·CHANGELOG 파싱 금지·실재 기능만·정직 프레이밍 전부 강제.

→ 두 렌즈를 모두 만족. 이하 설계.

## 1. 거처 + 3분리

### 1.1 거처 — 새 패키지 ❌ / `_shared/tour/` ✅

신규 패키지(`@dartlab/ui-tour`)는 **과잉**이다 — `package.json`/`tsconfig`/`exports`/workspace 의존선언 4곳 증식. 투어는 surface가 *내부적으로* 쓰는 공유 부품이지 독립 도메인이 아니다.

**정공법**: `ui/packages/surfaces/src/_shared/tour/` 신설(현재 `_shared/` 부재). `package.json:exports`에 `_shared` subpath를 **추가하지 않는다**(terminal/index.ts의 "내부 부품은 비공개 — 트리 내부 상대 import로만" 규율과 동일).

```
ui/packages/surfaces/src/_shared/tour/
  TourEngine.svelte      // 순수 엔진: def 받아 마스크·팝오버·키보드·진행 (콘텐츠 0)
  types.ts               // TourStep · TourDefinition · TourRequirement
  guard.ts               // anchor drift 런타임 검출 (dev 경고)
  whatsNew.ts            // 신규기능 큐레이션 SSOT (cardGuide.ts 패턴, [03])
```

> **★open 상태는 surface 로컬 `$state` — 별도 module store 신설 안 함(v0.1 트림).** `?` 버튼도 투어 오버레이도 *같은 surface 컴포넌트*(map=`+page.svelte`, terminal=`TerminalSurface`)가 렌더하므로, map이 이미 쓰는 `let tourOpen = $state(false)` 로컬 패턴으로 충분하다. `viewerEntry.svelte.ts` 스토어는 *형제 컴포넌트 간 통신*이 필요할 때만 정당한데 투어엔 그 경계가 없다(YAGNI — feedback_always_check_clutter). 진짜 cross-component 트리거(외부에서 특정 챕터 강제 오픈 등)가 생기면 *그때* `tourStore`를 추가한다.

### 1.2 TourStep 데이터 스키마

기존 map `Step`(`selector?/title/body/why?/demo?`)의 `demo.run`은 map전용 클로저(`colorMetric='roe'` 등)다 — **이 클로저 결합이 재사용 불가의 근원**. 엔진이 콘텐츠를 surface-agnostic하게 다루려면 `run`을 surface가 주입하는 *액션 핸들에 위임*(§1.3).

```ts
// _shared/tour/types.ts
export type TourAnchorId = string;          // surface별 union 으로 좁힘 (§2.2)

export interface TourRequirement {
  kind: 'always' | 'localOnly' | 'service'; // 'localOnly'=로컬 전용, 'service'=특정 서비스 가용성
  serviceId?: string;                        // kind:'service' (미래 수렴, [02] §4 — 지금 미사용)
}

export interface TourStep {
  anchor?: TourAnchorId;          // [data-tour="..."] 와 1:1. '.'/'#' 시작 시 raw selector 폴백(map 호환)
  title: string;
  body: string[];                 // **bold**·\n 인라인포맷 (map renderBody 재사용)
  why?: string;
  demo?: { label: string; actionId: string };  // run 클로저 금지 — actionId → surface actionMap
  requires?: TourRequirement;     // 생략=always. 엔진이 runtime 으로 자동 판정해 skip/안내 ([02] §1)
  track?: string;                 // 챕터 분기 (퀵/풀 일반화, 00 §4). null=퀵 선형
  sinceVersion?: string;          // 신규기능 강조용 — whatsNew 와 공유 ([03])
}

export interface TourDefinition {
  id: 'map' | 'terminal' | string; // surface 식별 (localStorage seen 키 파라미터화)
  quickCount: number;              // 퀵투어 스텝 수 (map=3)
  steps: TourStep[];
}
```

### 1.3 demo 클로저 결합 끊기 — actionId + actionMap 주입

기존 map은 `demo.run`이 surface 내부 상태를 직접 건드린다(`colorMetric='roe'`). 엔진이 이를 모르게:

```ts
// 콘텐츠(map.tour.ts)는 actionId 만 선언
demo: { label: '▶ ROE 로 바꿔보기 (화면 색 변화)', actionId: 'setColorMetric:roe' }

// surface(+page.svelte / TerminalSurface)가 actionMap 주입 — 클로저는 여기 (기존 함수 재사용)
<TourEngine def={mapTour} actions={{
  'setColorMetric:roe': () => colorMetric = 'roe',
  'selectCompany:005930': () => demoSelectCompany('005930'),
}} />
```

엔진의 `runDemo()`는 `actions[step.demo.actionId]?.()`로 일반화. **이 한 번의 간접화가 엔진을 surface-agnostic으로 만든다** — map의 8개 액션 prop이 전부 사라지고 1개 `actions` 맵으로 수렴. actionId도 surface별 타입 union으로 좁혀 오타를 빌드타임 검출(§5 D3).

## 2. anchor 전략 — Panel.svelte SSOT 주입

### 2.1 핵심 발견: 터미널 anchor 부착점은 이미 1곳으로 수렴

실측: **모든 터미널 패널이 `ui/Panel.svelte` 단일 래퍼를 통과**한다(`<section class={'panel '+className}>`). 즉 39개 패널에 일일이 data-tour를 박을 필요가 없다. **Panel에 `tourId?` prop 1개만 추가**하면 전 패널이 앵커 가능:

```svelte
<!-- ui/Panel.svelte 수정 (3줄) -->
let { title, sub, lang, className='', tourId, ... }: Props = $props();
<section class={'panel '+className} data-tour={tourId}>
```

호출측은 `<Panel title="..." tourId="terminal.priceChart" />`처럼 **선언적**으로. KPI티커·헤더 같은 Panel 밖 요소만 직접 `data-tour` 부착(소수).

### 2.2 하드코딩 셀렉터 vs 레지스트리 — 타입 union 채택

전역 레지스트리(런타임 register/unregister)는 **과설계**(등록 순서 의존·생명주기 버그·테스트 어려움). 대신 **빌드타임 타입 union**:

```ts
// terminal/terminalTourAnchors.ts — anchor id SSOT (닫힌 집합)
export const TERMINAL_ANCHORS = [
  'terminal.cmdBar', 'terminal.priceChart', 'terminal.finCards', 'terminal.gradePanel',
  'terminal.verdict', 'terminal.dupont', 'terminal.valuation', 'terminal.viewerBtn',
  'terminal.risks', 'terminal.percentile', 'terminal.statements', 'terminal.screener',
] as const;
export type TerminalAnchor = typeof TERMINAL_ANCHORS[number];
```

`TourStep.anchor: TerminalAnchor`로 좁히면 — **콘텐츠에 오타/없는 앵커 쓰면 tsc 빌드 실패**. Panel의 `tourId`도 이 타입으로 받으면 부착측·참조측이 같은 닫힌 집합 공유.

### 2.3 drift 조기검출 (리팩토링 시 앵커 증발 방어)

타입은 "id 존재"만 보장하지 "DOM 마운트"는 못 보장한다(조건부 렌더로 사라질 수 있음). 2중 가드:

- **런타임 dev 가드**(`guard.ts`): 투어 open 시 `def.steps`의 모든 `anchor`에 `document.querySelector('[data-tour="..."]')` 검사, 누락이면 `console.warn('[tour] anchor "X" 미발견 — 스텝 N')`. 현 map `position()`은 `querySelector` null이면 `highlight=null`로 *조용히 중앙 모달 폴백* — 이걸 **dev에서만 시끄럽게**(prod는 우아한 폴백 유지). "조용히 깨짐"을 막는 유일한 방법.
- **테스트**(선택, feedback_ui_rules Playwright 정량): 투어 e2e가 각 스텝 `next()` 후 하이라이트 박스 존재를 assert. tutorial_video_pipeline이 이미 Playwright로 뷰어 결정론 구동 중 — 동일 toolkit 재사용.

## 3. 로컬/퍼블릭 공통배선 (엔진 측 요약 — 상세 [02])

`TourStep.requires`만 데이터로 선언하고 **엔진이 `useDartLabRuntime()`으로 판정**한다(콘텐츠에 `if(local)` 하드코딩 금지):

```ts
// TourEngine 내부 — 스텝 평가
function evalStep(step: TourStep): 'show' | 'showLocalOnly' | 'skip' {
  const r = step.requires;
  if (!r || r.kind === 'always') return 'show';
  if (r.kind === 'localOnly')
    return rt.env.kind === 'local' ? 'show' : 'showLocalOnly';
  // r.kind === 'service' 는 미래 수렴 ([02] §4) — 지금은 services 미배선이라 콘텐츠가 안 씀
  return 'show';
}
```

`showLocalOnly`는 퍼블릭에서 *숨기지 않고* 팝오버 상단 배지("🖥 로컬 전용") + `publicNote` + 설치 CTA, 데모 버튼 비활성. **포트를 절대 touch 안 함**(퍼블릭에서 `runtime.services`/`ai`/`navigation`은 접근만 해도 getter throw). SSOT·카피·정직 모델은 [02](02-local-public-common-wiring.md).

## 4. map 100% 동작 유지 마이그레이션 (무중단)

map 동작은 *시각 회귀 위험*(feedback_ui_rules — 푸시 전 스크린샷 눈검수). 순서:

1. `TourEngine.svelte` = 현 TutorialTour.svelte의 **로직만** 복사(position·$effect·maxStep·next/prev/finish·popStyle·renderBody·마스크 SVG·전체 `<style>`). STEPS 제거, `def`/`actions` prop 추가. **localStorage 키를 `dartlab.${def.id}.tour.done`로 파라미터화**(현 하드코딩 `dartlab.map.tour.done`).
2. `map/map.tour.ts` = 현 STEPS 13개를 그대로 옮기되 `selector→anchor`, `demo.run→demo.actionId` 치환. **map은 className 셀렉터(`.brand-bar`·`.color-switch`)를 이미 안정적으로 쓰므로** anchor가 `.`로 시작하면 셀렉터 폴백(§1.2) → map은 data-tour 부착 0으로 추출 가능 = 회귀면 최소.
3. `map/components/TutorialTour.svelte` = **얇은 어댑터로 축소**(삭제 아님 — `map/index.ts` 공개 export라 landing import 유지): 내부에서 `TourEngine` + `mapTour` + map actionMap 조립. `landing/+page.svelte`의 import·prop **무변경** = 회귀 표면 0.
4. svelte-check + **map 스크린샷 눈검수(13스텝 전부)** 후에만 터미널 착수.

이 순서면 map은 어댑터 뒤에서 기존 계약 유지, 터미널은 새 엔진 직접 소비 — 공존이 자연스럽다.

## 5. 적대검증 — 유지보수 지옥 5 + 방어

| # | 지옥 | 방어 |
|---|---|---|
| D1 | **콘텐츠 폭주**: surface 늘수록 `*.tour.ts` 비대(map STEPS 이미 ~192줄). | 콘텐츠는 데이터지 로직 0 — diff/리뷰 쉬움. quickCount로 핵심 4스텝 강제. 풀투어 opt-in. "성공지표=스텝 수 아님". |
| D2 | **anchor 증발**: className 변경→스텝 깨짐을 아무도 모름. | §2.2 타입 union(빌드실패) + §2.3 dev 가드(warn) + prod 우아한 폴백. 3중. |
| D3 | **actionId 결합 재발**: actionMap 키 오타→데모 무반응. | actionId도 타입 union. 엔진 `runDemo` 미존재 키 시 dev warn. |
| D4 | **엔진/콘텐츠 경계 침식**: 누군가 TourEngine에 map전용 `if`를 다시 넣음(map이 그렇게 시작됨). | 엔진은 `useDartLabRuntime`·`def`·`actions` 외 import 0 강제 — surface 타입 import 금지. `_shared/`는 surface 폴더를 import 못함(단방향). PR 리뷰 체크. |
| D5 | **z-index·키보드 충돌**: 투어 키핸들러가 cmdBar 입력·차트 전체화면 키와 싸움. | 엔진 키핸들러에 input/textarea 가드 이식(map +page.svelte 패턴). z-index를 토큰화해 surface 주입(터미널 `.scrimWrap=200`보다 위). |

### 새 의존성(driver.js/shepherd/intro.js) → 전부 기각
① 외부 투어 라이브러리 없음·새 의존성 비선호(surfaces 의존성은 도메인 필수 cosmograph·klinecharts뿐). ② 자체구현이 이미 마스크 SVG·데모 액션·퀵/풀·반응형 바텀시트까지 갖춰 라이브러리보다 *풍부*. ③ driver.js는 `requires`/런타임 판정·actionId·신규기능을 못 해 어차피 래핑 필요 = 순손실.

## 6. KILL 목록 (아키텍처)

1. **❌ 새 패키지 `@dartlab/ui-tour`** — `_shared/tour/`로 충분.
2. **❌ `exports`에 `_shared` subpath 공개** — 투어는 내부 부품.
3. **❌ 런타임 anchor 레지스트리**(register/unregister) — 타입 union으로 정적 해결.
4. **❌ CHANGELOG/git tag 자동파싱** — 문화 위반([03] §1). `whatsNew.ts` 큐레이션.
5. **❌ demo.run 클로저를 콘텐츠에 유지** — 재사용 불가의 근원. actionId 간접화 필수.
6. **❌ 콘텐츠에 `if(env.kind==='local')` 하드코딩** — `requires` 선언 + 엔진 판정. 콘텐츠는 환경 무지.
7. **❌ map TutorialTour.svelte 즉시 삭제** — 공개 export. 얇은 어댑터로 축소(계약 보존).
8. **❌ 39패널 일일이 data-tour 부착** — `Panel.svelte` `tourId` 1개로 전 패널 커버.
9. **❌ 별도 엔진/커널/그래프/노드/디스패처 신설** — `Step[] + spotlight 1컴포넌트` 상한. no-graph-regression 동형.

## 추천 거처

| 산출물 | 경로 |
|---|---|
| 투어 엔진(로직만) | `ui/packages/surfaces/src/_shared/tour/TourEngine.svelte` |
| 타입·가드·신규기능 | `ui/packages/surfaces/src/_shared/tour/{types.ts,guard.ts,whatsNew.ts}` |
| open 상태 | surface 로컬 `$state` — 별도 store 신설 안 함 (§1.1, v0.1 트림) |
| map 콘텐츠 | `ui/packages/surfaces/src/map/map.tour.ts` |
| map 어댑터(축소) | `ui/packages/surfaces/src/map/components/TutorialTour.svelte` (기존, export 유지) |
| terminal 콘텐츠·앵커 | `ui/packages/surfaces/src/terminal/{terminal.tour.ts,terminalTourAnchors.ts}` |
| anchor 부착점 | `ui/packages/surfaces/src/terminal/ui/Panel.svelte` (`tourId` prop 추가 — 전 패널 커버) |
| terminal 마운트·`?`버튼 | `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` (hdrLinks에 버튼 + TourEngine 조립) |

## 핵심 주장 3줄

1. map TourTour는 엔진+콘텐츠+map전용 prop이 융합돼 재사용 불가 — 엔진/콘텐츠/배선 3분리, 콘텐츠를 surface별 `*.tour.ts` 데이터로 외부화, 거처는 `_shared/tour/`(새 패키지 과잉).
2. anchor는 `Panel.svelte` 단일 SSOT에 `tourId` prop 1개로 전 패널 커버 + 타입 union(빌드 가드) + dev 런타임 가드(drift 검출). className 셀렉터 하드코딩 금지.
3. 로컬/퍼블릭은 `requires` 1필드 + 엔진이 `env.kind` 판정해 자동 skip/안내 — 콘텐츠는 환경 무지. 엔진은 `Step[] + spotlight 1컴포넌트`에서 못 벗어남(그래프/커널 신설 reject).
