# 08. Public ↔ Local 공동배선 Parity & 유지보수 플레이북

> 상태: 가변 운영 문서(런북). 01~07 은 리팩토링 *설계/실행* SSOT, 본 문서는 그 결과물인
> 두 앱(public·local)의 **공유 배선 계약 + 드리프트 방지 + 장애 런북 + 변경 절차** SSOT.
> 01 §4(타깃 아키텍처)·02 §9(런타임 책임경계)·03(디자인 시스템)의 운영판 후속.

---

## 0. 이 문서를 언제 읽나

- public(깃헙페이지) 또는 local(pip 앱) 중 **한쪽만 깨졌을 때** → §8 런북.
- surface·runtime·design·app shell 중 **무엇이든 손대기 전** → §9 변경 위치 결정 트리 + parity 체크리스트.
- "두 앱이 왜 같은 코드인데 달라 보이나" 의문 → §2(공유 vs 앱별) + §5(의도된 발산).
- 자산·폰트·CSS·링크 동기화 누락 의심 → §6 드리프트 레지스트리.

---

## 1. 한 줄 정의 + 명칭 표준

**공동배선(shared wiring)** = 두 앱이 *같은 UI surface 와 runtime 패키지*를 소비하되, 각자의
**composition root** 에서 basePath·자산·CSS·데이터 포트만 다르게 주입하는 구조. UI 는 1벌, 주입은 2벌.

명칭은 **코드의 `kind` 판별자**를 그대로 쓴다(대화어 = 코드어, 번역손실 0):

| 정식 | = 코드 | = 디렉터리 | = 서빙 | 별칭(같은 대상) |
|---|---|---|---|---|
| **public** | `kind:'public'`, `createPublicRuntime` | `landing/` | GitHub Pages `eddmpython.github.io/dartlab` (정적 prerender) | landing, 공개 셸, 공표, 깃헙페이지 |
| **local** | `kind:'local'`, `createLocalRuntime` | `ui/apps/local/` | Python 서버(pip wheel)가 `/`에 서빙 | 로컬 앱, pip wheel UI, 로컬 터미널 |

- ⚠ "local" = **항상 그 앱(ui/apps/local)**. public 을 `npm run dev` 로 내 PC에 띄운 건 "**public dev**" 라 부른다(localhost ≠ local 앱).
- ⚠ `ui/web`(React 레거시, `DARTLAB_UI_LEGACY`)은 **세 번째 것** — 폐기 경로, 본 문서 범위 밖. "그 UI" 단독 표현 금지.

---

## 2. 아키텍처 — 무엇이 공유고 무엇이 앱별인가

### 2.1 공유 4 패키지 (`ui/packages/*`) — 한 번 고치면 양쪽 자동 반영

| 패키지 | 역할 | 핵심 파일 |
|---|---|---|
| `@dartlab/ui-contracts` | 포트 인터페이스(타입 계약) | `contracts/src/*.ts` |
| `@dartlab/ui-design` | 디자인 토큰 CSS(`--dl-*`) | `design/src/styles/{tokens,v2-tokens,typography}.css` |
| `@dartlab/ui-runtime` | 데이터 어댑터(public/local/test) + HF 적재·캐시·base | `runtime/src/adapters/**`, `runtime/src/data/{dartlabData,hfRange,origin}.ts` |
| `@dartlab/ui-surfaces` | 모든 UI(terminal·viewer·scan·map) | `surfaces/src/{terminal,viewer,scan,map}/**` |

### 2.2 앱별 composition root 2 개 — 같은 surface 에 다른 포트를 주입

```
            ┌─────────────────── @dartlab/ui-surfaces (UI 1벌) ───────────────────┐
            │  TerminalSurface · ViewerStudio · ScanWorkspace · EcosystemMap ...   │
            └──────────────▲───────────────────────────────────────▲──────────────┘
                           │ runtime(포트) 주입                      │ runtime(포트) 주입
        ┌──────────────────┴───────────┐              ┌─────────────┴────────────────┐
        │ landing (public)             │              │ ui/apps/local (local)         │
        │ getPublicRuntime()           │              │ getLocalRuntime()             │
        │ = createPublicRuntime(...)   │              │ = createLocalRuntime(...)     │
        │ publicRuntime.ts             │              │ localRuntime.ts               │
        └──────────────────────────────┘              └───────────────────────────────┘
```

- 진입 디스패처: `runtime/src/createRuntime.ts` (`kind:'public'|'local'|'test'`).
- 컴포지션 루트는 **앱당 1곳**: `landing/src/lib/runtime/publicRuntime.ts`, `ui/apps/local/src/lib/runtime/localRuntime.ts`.
- surface 는 `$app/paths`·`window`·`kind` 를 **모른다**(02 §1) — 셸이 basePath·navigation·hosts·links 를 주입.

---

## 3. public ↔ local 1:1 매핑표 (앱 셸 레벨)

| 축 | public(landing) | local(ui/apps/local) | 동일? |
|---|---|---|---|
| 컴포지션 루트 | `publicRuntime.ts` | `localRuntime.ts` | 패턴 동일, 주입 다름 |
| basePath | `/dartlab` (`BASE_PATH`) | `''` (루트) | **발산(의도)** |
| 빌드 | adapter-static, prerender, `fallback:404.html` | adapter-static, SPA, `fallback:index.html` | **발산(의도)** |
| SSR | prerender(정적) | `ssr=false`+`prerender=false` SPA | **발산(의도)** |
| 글로벌 CSS reset | `+layout.svelte <style>` | `+layout.svelte <style>` | **미러(수동 동기화)** §6 |
| 디자인 토큰 import | `+layout.svelte` 3종 | `+layout.svelte` 3종 | 동일(공유 패키지) |
| 폰트(app.html) | Pretendard+Inter+JetBrains Mono | Pretendard+Inter+JetBrains Mono | **미러(수동)** §6·§7 |
| favicon | 있음 | 있음(2026-06-14 복사) | **미러(수동)** §7 |
| robots / feed / SEO | index,follow + atom feed | noindex,nofollow | **발산(의도)** |
| 헤더 브랜드 링크 | `terminalLinks`←`brand.ts` | `localLinks`(하드코딩) | **미러(수동 동기화)** §6 |
| 터미널 뷰어 host | 컴포넌트 임베드(`viewerStudio` 로더) | iframe(`viewerStudio:null`) | **발산(의도)** |
| 정량재무 다이얼로그 | DuckDB-WASM(`financeDialog` 로더) | 강등 안내(`financeDialog:null`) | **발산(의도)** |

---

## 4. 데이터 경로 — 무엇이 공유 HF直, 무엇이 앱별인가

> 핵심: **시장 전체 씨드 + 재무 + 매크로 = 양쪽 동일 HF直**(그래서 스크리너·생태계맵·동종비교·차트 재무카드가 두 앱에서 같다).
> **회사 단위 실시간 상세만** public=HF parquet 직접 / local=`/api`(Python 엔진)로 갈린다. 둘 다 **단일 경로**(silent fallback 없음).

| 데이터 | public 소스 | local 소스 | 동일 값? |
|---|---|---|---|
| 터미널 씨드 7종(finance/macro/meta/prices/index/eco/quarters JSON) | HF直(`loadJson`, `HF_RESOLVE/landing/*`) | HF直(동일) | ✅ |
| 회사 재무 번들(`finance.bundle`) | `loadTerminalFinance`(HF `dart/finance/{code}.parquet`) | **동일** `loadTerminalFinance` | ✅ |
| 매크로(`macro`) | `createHfMacroPort`(HF) | **동일** `createHfMacroPort` | ✅ |
| 공시뷰어 격자(panel) | 브라우저 HF parquet(`hfRange`) | 브라우저 HF parquet(동일) | ✅ |
| 주가 candle(`price`) | gov/naver/recent HF parquet | `/api`(Python) | 형태 동일, 소스 발산 |
| 회사 products·relations | HF parquet | `/api` | 형태 동일 |
| 공시 목록(`filing.regular/nonRegular`) | HF parquet | `/api` | 형태 동일 |
| 정기보고서 팩트(`report.*`) | HF parquet | `/api` | 형태 동일 |
| `scan.changes` | DuckDB-WASM(셸 주입) | `/api` | 형태 동일 |
| AI(`ai`) | 브라우저(WebLLM/Tier0, AskDrawer) | `/api/agent` SSE(`localAiPort`) | **발산(의도)** |
| export | 브라우저 워크북(셸 주입) | 엔진 `.xlsx`(`/api`) | 산출 동형 |

- `base` 주입 SSOT: `runtime/src/data/dartlabData.ts:setStaticBase`. **public 만 호출**(`+layout.svelte`·`terminal-shell/routeLoad.ts` 모듈평가 시점). local 은 `base=''` 불변이라 미호출(씨드는 HF直이라 base 무관). → §6.7 불변식.
- parquet Range(206) 캐시 충돌 방지: `runtime/src/data/hfRange.ts:fetchResilient` 의 `cache:'no-store'`(양쪽 공유).

---

## 5. 의도된 발산 (parity 아님 — **고치면 안 되는 것**)

> 아래는 "두 앱이 다른 게 정상"이다. 이걸 "미러로 맞춘다"고 통일하려 들면 아키텍처가 깨진다.

1. **basePath** — public 은 `/dartlab` 서브패스, local 은 루트 `''`. 모든 자산/JSON 경로가 여기에 의존.
2. **데이터 포트** — public 은 백엔드 없는 정적(HF直+브라우저 DuckDB), local 은 Python `/api` 백엔드. per-company 상세·AI·scan.changes·export 가 다른 소스(§4). 형태만 같다.
3. **뷰어 임베드** — public=컴포넌트(`viewerStudio` 로더), local=iframe(`viewerStudio:null` → ViewerOverlay 가 `/analysis/[code]/viewer?...` 로드). 챗 진입도 public=컴포넌트 onMount, local=iframe `?ask=1`.
4. **정량재무 다이얼로그** — public 만 DuckDB-WASM. local 은 정직 강등 안내(`financeDialog:null`). 터미널 *기본* 재무카드는 양쪽 동일(HF, §4).
5. **SEO** — public 은 색인+atom feed, local 은 noindex(사적 앱).
6. **렌더 모드** — public prerender 정적, local SPA(`ssr=false`).
7. **theme-color** — public `#050811`, local `#0f0f10`(로딩 한순간만 노출, 터미널이 자체 bg 칠함).

---

## 6. 드리프트 위험 레지스트리 — **수동 동기화 핫스팟**

> 같은 것이 *두 파일에 복제*돼 있어, 한쪽만 고치면 미러가 깨지는 지점. surface/runtime/design 처럼 단일파일이
> 아니라 **앱 셸**이라 공유가 불가능한 부분들이다. 손댈 때마다 짝을 같이 고친다.

| # | 무엇 | public 위치 | local 위치 | 깨지는 증상 |
|---|---|---|---|---|
| 6.1 | static 자산(아바타 26·favicon) | `landing/static/` | `ui/apps/local/static/` | surface 가 새 자산 참조 추가 시 한쪽만 404 → 아바타/아이콘 깨짐 |
| 6.2 | 글로벌 CSS reset(scrollbar 10px·overflow-x clip·word-break) | `landing/src/routes/+layout.svelte <style>` | `ui/apps/local/src/routes/+layout.svelte <style>` | 한쪽만 변경 시 스크롤바 폭·줄바꿈 차이로 wrap 패널 **높이 어긋남** |
| 6.3 | app.html 폰트 | `landing/src/app.html` | `ui/apps/local/src/app.html` | JetBrains Mono 누락 시 터미널 숫자 시스템 mono 폴백 → 글자/정렬 다름 |
| 6.4 | 헤더 브랜드 링크 | `terminalLinks`←`landing/src/lib/brand.ts` | `localLinks`(`ui/apps/local/src/lib/shell/terminalShell.ts` 하드코딩) | URL 변경 시 한쪽만 갱신 → 링크 불일치 |
| 6.5 | 디자인 토큰 import 3종 | `+layout.svelte` | `+layout.svelte` | 공유 패키지라 값은 안전, import 라인 누락 시 토큰 미적용 |
| 6.7 | `setStaticBase` 불변식 | 호출함 | **미호출(`base=''` 가정)** | local 을 서브패스로 서빙하면 `${base}/*` 전부 깨짐. local 은 루트 서빙 불변식에 묶임 |

- 6.1 자산 참조 SSOT(현재 전수): surface 가 쓰는 static 자산 = `avatar.{png,webp}`, `avatar-detective.*`, `avatar-study.*`, `avatar-curious.*`(+ AskDrawer/Export/Viewer/Terminal 의 picture 태그). CSS `url()` 자산 의존은 **없음**(Newsreader 만 `typography.css` 가 `@import`, 공유). 새 아바타/아이콘 추가 시 양쪽 `static/` 에 둘 다 복사.

---

## 7. 이번 감사(2026-06-14)에서 확인·수정한 것

**전수 감사 결과**: 두 composition root 배선·자산·base·캐시 모두 정공 설계 확인. 발견된 **진짜 갭 2건 수정**:

1. **폰트(6.3)** — local `app.html` 이 Pretendard 만 로드 → 터미널 `--dl-font-mono`(JetBrains Mono)·`--dl-font-ui`(Inter) 가 시스템 mono/sans 로 폴백돼 public 과 숫자 모양·tabular 정렬·격자 높이가 미세히 어긋남. → public 과 동일한 Google Fonts(Inter+JetBrains Mono) + preconnect 추가.
2. **favicon(6.1)** — local `static/` 에 favicon 부재 + `app.html` 링크 없음 → 탭 아이콘 기본 globe + `/favicon.ico` 낭비 요청. → `favicon.{ico,png}` 복사 + `app.html` 링크 추가.

검증: `npm run build -w @dartlab/ui-local` 성공, 빌드 산출 `index.html` 에 폰트 링크·`/favicon.*` 반영, `build/favicon.{ico,png}` 존재 확인.

**직전 세션 수정분(맥락)**: base-timing 404(`setStaticBase` 모듈평가), parquet 206 캐시충돌(`cache:'no-store'`), 아바타 basePath 주입, 터미널 헤더 AI 챗 진입 버튼 — 모두 public LIVE 검증 완료(이력은 git).

---

## 8. 향후 문제 발생 시나리오 → 증상 → 진단 → 처방 (런북)

| 시나리오 | 증상 | 어느 앱 | 진단 | 처방 |
|---|---|---|---|---|
| **S1 base-timing 404** | 콘솔 `/<file>:404`(앞 슬래시, basePath 누락), 씨드 HF 폴백으로 느림 | public | `+page.ts load` 가 `setStaticBase` 보다 먼저 도는가 | 새 라우트 로더는 `routeLoad.ts` 처럼 **모듈평가 시점** `setStaticBase(base)` 보장 |
| **S2 parquet 캐시충돌** | `ERR_CACHE_OPERATION_NOT_SUPPORTED`, 우측패널/정기공시 빈값 | 양쪽 | 206 Range 응답을 HTTP 캐시에 쓰려다 실패 | `hfRange.ts` 신규 fetch 는 Range 면 `cache:'no-store'` 경유(이미 SSOT) |
| **S3 아바타/아이콘 깨짐** | 이미지 broken, 한쪽만 | 한쪽 | surface 새 자산 추가 후 한쪽 `static/` 누락 or basePath 미주입 | 양쪽 `static/` 복사(§6.1) + surface 는 `{base}`/`{basePath}` prop 경유 참조 |
| **S4 챗 아이콘 없음/안 열림** | 터미널 헤더 AI 없음 or 클릭 무반응 | 한쪽 | surface 진입점 vs 셸 host 배선 | 진입은 surface(`TerminalSurface` AI 버튼). public=컴포넌트 onMount, local=iframe `?ask=1` 경로 확인 |
| **S5 폰트 폴백** | 숫자 글자폭/모양 다름, 격자 높이 미세 차이 | 보통 local | `app.html` 에 JetBrains Mono 링크 유무 | 양쪽 app.html 폰트 미러(§6.3·§7) |
| **S6 씨드 동결** | prices/매크로 asOf 가 옛 날짜로 고정 | public | `preferLocal` 이 정적 사본을 영원히 우선 | prices-snapshot·macro·ecosystem 은 **HF-first**(`loadJson` 옵션, `shouldCacheJson` 제외) 유지 |
| **S7 prerender 404** | 새 동적 라우트가 GitHub Pages 에서 404.html | public | `svelte.config.js` prerender entries 누락 | 회사별 정적 shell 패턴(`viewerEntries`)처럼 entry 생성 or `handleHttpError` 관용 |
| **S8 MDX `<` 빌드중단** | landing prerender 실패 `Expected a valid element name` | public(블로그) | 본문 bare `< `(less-than+공백)가 JSX 로 오인 | 블로그 본문 `<`→`&lt;`(생성 파이프라인 차원 escape = 운영자 도메인) |
| **S9 브랜드 링크 불일치** | 헤더 SNS 링크가 앱마다 다름 | 한쪽 | `brand.ts` ↔ `localLinks` 드리프트 | 양쪽 동시 갱신(§6.4) |
| **S10 local 서브패스 배포** | local 모든 자산 404 | local | `base=''` 불변식 위반 | local 도 `setStaticBase` 배선 + `BASE_PATH` 도입(현재 미지원, 도입 시 §6.7 해제) |
| **S11 공시 로딩 느림** | 공시 목록·뷰어 격자 수초~수십초 | public | 회사 panel(10~13MB)을 **프록시 경유 byte-range** 직독 = 요청당 ~2.8s(HF 직결 0.38s) | **range→HF 직결**(`hfRangeUrl`), 통파일/JSON만 프록시 — §11 상세 |
| **S12 prices/매크로 1년 캐시 동결** | 시세·매크로가 옛값 고정 | public | 소형 통파일을 **HF 직결로** 받으면 HF `Cache-Control: max-age=31536000` 적용 | 통파일은 **프록시 유지**(worker 가 recent=600s·기타=3600s 재발급). range 만 직결 |

---

## 9. "계속 손대야 하는 부분" — 변경 위치 결정 트리 + 절차

### 9.1 무엇을 어디서 고치나 (이 순서로 판단)

1. **UI 모양/동작** 변경? → `ui/packages/surfaces/**` **한 곳**. 한 번 고치면 public·local 자동 반영. **절대 앱에 복붙 금지**([[feedback_no_patterns]] facade/복붙 금지).
2. **데이터 적재 로직**(HF resolve·캐시·base·파서)? → `ui/packages/runtime/**`. 양쪽 공유.
3. **디자인 토큰/CSS 변수**? → `ui/packages/design/**`. 양쪽 공유.
4. **"어떤 소스에서 데이터를 가져오나"**(포트 주입)? → composition root(`publicRuntime.ts` / `localRuntime.ts`). **앱별 = 의도된 발산**, parity 아님(§5).
5. **앱 셸**(폰트·favicon·robots·글로벌 CSS·라우트·prerender·브랜드 링크)? → `landing/` 또는 `ui/apps/local/`. **드리프트 핫스팟(§6)** — 짝을 반드시 같이 본다.

> 규칙: 1~3(공유 패키지)에서 풀 수 있으면 거기서 푼다. 5(앱 셸)는 최후이자 수동 동기화 비용이 드는 곳.

### 9.2 앱 셸 또는 static 손댈 때 parity 체크리스트

- [ ] surface 가 **새 static 자산** 참조? → 양쪽 `static/` 에 복사(§6.1). surface 참조는 `{base}`/`{basePath}` prop 경유인지 확인.
- [ ] **app.html 폰트/메타** 변경? → 다른 앱 app.html 도 동일 변경. 단 robots/feed/theme-color 는 **의도적 발산(§5)** 이라 제외.
- [ ] **+layout 글로벌 CSS reset** 변경? → 다른 앱 +layout `<style>` 미러(§6.2).
- [ ] **브랜드 링크** 변경? → `brand.ts` + `localLinks` 둘 다(§6.4).
- [ ] **새 동적 라우트** 추가? → public prerender entry 필요한지(`svelte.config.js`), local 은 SPA fallback 이라 무관.
- [ ] **새 데이터 포트** 추가? → contracts 인터페이스 → public·local 어댑터 둘 다 구현(또는 한쪽 `notWiredYet` 정직 게이트). silent fallback 금지.

### 9.3 commit 전 검증 게이트 (싼 것부터)

```bash
# 1. 공유 패키지 타입 (runtime/surfaces 손댔으면)
npm run check -w @dartlab/ui-surfaces        # svelte-check
# 2. public 빌드 — ⚠ PowerShell 로(Git Bash 는 /dartlab 를 윈도경로로 변환해 깨짐)
#    PowerShell:  $env:BASE_PATH='/dartlab'; npm run build -w landing
# 3. local 빌드 (app.html/static 손댔으면 충분 — 자산·폰트 반영 확인)
npm run build -w @dartlab/ui-local
# 4. Playwright(빌드 산출물): 터미널 첫 페인트·챗아이콘·아바타 broken=0·정기공시 행수·콘솔 404=0
```

- public 풀 prerender 는 로컬에서 HF seed 미보유로 일부 404 → **CI 가 권위**(로컬 게이트 = check/build).
- 자산만 바꿨으면 public 재빌드 불필요(공유 패키지 무변경이면 영향 없음).

---

## 10. 빠른 참조 — 파일 인덱스

| 역할 | 파일 |
|---|---|
| kind 디스패처 | `ui/packages/runtime/src/createRuntime.ts` |
| public 어댑터 | `ui/packages/runtime/src/adapters/public/createPublicRuntime.ts` |
| local 어댑터 | `ui/packages/runtime/src/adapters/local/createLocalRuntime.ts` |
| public 컴포지션 루트 | `landing/src/lib/runtime/publicRuntime.ts` |
| local 컴포지션 루트 | `ui/apps/local/src/lib/runtime/localRuntime.ts` |
| base 주입 SSOT | `ui/packages/runtime/src/data/dartlabData.ts` (`setStaticBase`) |
| HF Range 캐시 가드 | `ui/packages/runtime/src/data/hfRange.ts` (`cache:'no-store'`) |
| public 터미널 로더(setStaticBase 모듈평가) | `landing/src/lib/terminal-shell/routeLoad.ts` |
| local 터미널 로더(HF直) | `ui/apps/local/src/lib/shell/routeLoad.ts` |
| public 셸 주입(hosts·links) | `landing/src/lib/terminal-shell/terminalShell.ts` |
| local 셸 주입(hosts·links) | `ui/apps/local/src/lib/shell/terminalShell.ts` |
| 글로벌 CSS reset | `landing/src/routes/+layout.svelte` ↔ `ui/apps/local/src/routes/+layout.svelte` |
| app.html(폰트·favicon·SEO) | `landing/src/app.html` ↔ `ui/apps/local/src/app.html` |
| 디자인 토큰 | `ui/packages/design/src/styles/{tokens,v2-tokens,typography}.css` |
| 터미널 surface(AI 버튼·아바타) | `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` |
| 빌드 config | `landing/svelte.config.js` ↔ `ui/apps/local/svelte.config.js` |
| HF resolve SSOT(프록시/직결 분리) | `ui/packages/runtime/src/data/origin.ts` (`HF_RESOLVE`·`HF_RANGE_RESOLVE`) |

---

## 11. 공시(공시데이터) 로딩 속도 — 측정·근본원인·정공 수정 (2026-06-14)

### 11.1 증상
public(깃헙페이지)에서 공시 목록·뷰어 격자 로딩이 수초~수십초. local 은 빠름(=프록시 미경유, 아래 참조).

### 11.2 측정 (프로덕션 프록시 직접 호출, .NET HttpClient)
| 항목 | 값 |
|---|---|
| `dart/panel/005930.parquet` | **13.4 MB** (000080 = 10.4 MB) — 회사당 공시 panel 통째로 큼 |
| **프록시** range 요청 1건 | **2,600~3,456 ms** (반복해도 동일 = 엣지캐시 안 됨) |
| **HF 직결** 동일 range | **380 ms** → 프록시가 **7~9배 느림** |
| 프록시 206 `cf-cache` | 비어있음 — worker 가 부분응답 엣지캐시 안 함([worker.js:16](../infra/workers/hfProxy/worker.js#L16)) |
| HF 직결 CORS | `ACAO: https://eddmpython.github.io` echo → **브라우저 직결 가능** |

### 11.3 근본원인 (3중 누적)
1. 공시 데이터가 **회사당 10~13MB panel parquet** 1파일 → hyparquet 가 footer·메타·컬럼청크를 **직렬 byte-range 다수 왕복**으로 읽음.
2. 그 range 한 건이 **프록시에서 ~2.8s**(HF 직결 0.38s). 프록시는 206 을 엣지캐시 안 하므로 range 엔 순수 오버헤드.
3. 206 은 `cache:'no-store'`(ERR_CACHE 회피)라 브라우저 캐시도 없음 → 열 때마다 풀비용.

### 11.4 정공 수정 (공동호출·재사용, **새 프리빌드 없음**)
공유 runtime 한 곳만 고쳐 public·local 이 같은 경로를 재사용:
- **range 읽기 → HF 직결**(`origin.ts:hfRangeUrl` / `HF_RANGE_RESOLVE`, 기본 직결, 가역 env). probe·세션 전부.
- **소형 통파일(≤1.5MB)·JSON 씨드 → 프록시 유지**(`hfUrl` / `HF_RESOLVE`): 엣지캐시·per-file cache-control(recent=600s 신선도)·403 흡수. ← S12 동결 방지.
- `headHfObjectFresh` 는 **안정 resolve URL** 보관(서명 cas-bridge 리다이렉트 URL 캐시 금지 = 만료 깨짐 차단).
- 책임경계: "**bulk byte-range → CDN 직결**(프록시는 부분응답 이득 0) / **소형 cacheable object → 엣지 프록시**" — worker 가 명시한 2층 정책과 정확히 일치. 특수케이스 누적 아님.
- 기각: **공시 목록용 slim index JSON 발행**(= 새 프리빌드) — 운영자 방침 "프리빌드 더이상 안 함"에 따라 폐기. 라이브 직결로 해결.

> local 이 원래 빠른 이유: local 빌드는 `VITE_DARTLAB_HF_RESOLVE`(프록시)를 안 박아 이미 HF 직결. 이번 수정으로 public 도 range 는 동일 직결 → parity.

---

## 12. 터미널 클러터(죽은 코드) 인벤토리 — grep 확증, 제거 후보

> 2026-06-14 전수 감사(전문 에이전트 31 tool + 재grep). 본진 `ui/packages/surfaces/src/terminal/**`.
> ⚠ 운영자가 surfaces 를 병행 편집 중 + 아래는 운영자 생성 파일 → **임의 삭제 보류, 운영자 "지워" 시 1 커밋 제거**.

| 후보 | 상태 | 근거(0-ref 확증) | 비고 |
|---|---|---|---|
| `terminal/charts/Radar.svelte` (통째) | 고아 중복 | import 0. 라이브 = `ui/shared/chart/RadarChart.svelte`(다른 이름) | 단 `types.ts:RadarAxis`·`co.radar` 데이터는 `engine.ts:268,285` 사용 = **타입은 유지**, 컴포넌트만 삭제 |
| `terminal/charts/TrendChart.svelte` (통째) | 고아 중복 | import 0. 라이브 = `ui/shared/chart/TrendChart.svelte`(동명) | 마이그레이션 잔재 |
| `terminal/lib/indicators.ts` `stochastic`/`Stochastic`/`obv` | 미사용 함수 | TS 트리 참조 0 (backtest 는 sma/rsi/macd/bollinger 만) | 함수·인터페이스만 삭제 |
| `terminal/lib/types.ts` `ChartSpec`(:7)·`IndustryStat*`/`IndustryStatsFile`/`IndustryDistribution` | 미사용 타입 | 외부 참조 0 (`RawData` 에 industryStats 필드 없음) | 고아 타입 |
| `terminal/charts/PriceChart.svelte:960` `pushTick` | 죽은 메서드 | 호출자 0, `bind:this` 없이 마운트(CenterStack:352) = 도달불가 | livePrice 와 함께 폐기된 라이브틱 기능 |
| `terminal/ui/helpers.ts:31` `fmtAbbr` | 미사용 헬퍼 | repo 전체 1회(정의뿐) | |
| `terminal/lib/livePrice.ts` (통째 36줄) | 보류 스캐폴딩 | import 0. 단 `contracts/price.ts:36`·`naverPriceSource.ts:16` 주석이 "단계-4a livePrice 포트화" 로 **의도적 보류** 명시 | 삭제 시 위 주석 2개 정정 동반 필요. 운영자 설계 의사결정 사안 |

> 양호(클러터 아님, 건드리지 말 것): 두 평행 셸(public/local routeLoad·terminalShell)=의도된 어댑터 평행 / `dev/DevTerminal`=`/lab/terminal-dev` 라이브 / ViewerOverlay iframe·컴포넌트 2경로=문서화된 "두 입구" / naver fresh-tail=env 게이트 가역. **TODO/FIXME·주석처리 코드·silent fallback 위반 = 0건**(터미널 surface 는 대체로 깨끗).

---

## 13. 프리빌드 소비자 지도 — "scan 전용 아님" (조사 2026-06-14)

> 운영자 방침: **새 프리빌드(사전계산 산출물) 추가 금지** — 호출은 프런트 공동호출(직결)로. 기존 프리빌드 현황:

- **오프라인 빌더 9개 중 scan 은 1개**(`.github/scripts/prebuild/prebuildData.py` → `dart/scan/*.parquet`). 나머지 8개는 **terminal·map·viewer 씨드**(dashboards/*.json, map/*.json) 생성용.
- **terminal 이 단일 최대 소비자**: 부팅 시 7종 병렬 로드([routeLoad.ts:36-47](../landing/src/lib/terminal-shell/routeLoad.ts#L36)). scan 은 3종(ecosystem/prices-snapshot/meta)만.
- **라이브 대체 불가(사전계산 강제)**: `dart/scan/*`·`map/atlas`·`ecosystem`·`prices-snapshot`·`search-index`·`movers`·`insights`·`timeline`·`companies/*`·`industries/*` = **전종목 집계/그래프**(브라우저 라이브 불가, panel 92K seed OOM). 이건 프리빌드가 정공.
- **라이브 대체 가능(회사 단위, 이미 라이브 경로 존재)**: `dashboards/finance·quarters·meta·macro`, `map/companies/{code}`·`industries/{id}` — `browser/companyLive.ts` 가 라이브 버전 보유. 현재는 부팅 지연·HF 비용 절감 위한 씨드 우선일 뿐 구조적 불가 아님.
- 시간민감 3종(`ecosystem`·`prices-snapshot`·`macro`)은 6h 캐시 제외([dartlabData.ts:53-57](../ui/packages/runtime/src/data/dartlabData.ts#L53)) — 정적사본 동결 사고 가드.

> 결론: 공시 속도 수정은 **새 프리빌드를 만들지 않고**(목록용 index JSON 기각) 기존 panel 을 **직결 range** 로 빠르게 읽는 정공으로 처리했다(§11).
