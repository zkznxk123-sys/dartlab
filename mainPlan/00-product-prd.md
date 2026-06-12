# 00. Product PRD

상태: v1 확정 기준 문서  
범위: DartLab 공개 UI와 로컬 AI UI의 제품 목표, 사용자 경험, 성공 기준

---

## 1. 배경

현재 DartLab UI는 역할이 섞여 있다.

- `landing`은 공개 사이트이면서 가장 완성된 terminal, viewer, chart, company UI 자산을 갖고 있다.
- `ui/web`은 로컬 React 앱으로 Ask, provider 설정, 기존 dashboard, 로컬 API 배선을 갖고 있다.
- 사용자가 원하는 장기 방향은 로컬 UI가 `landing`의 터미널 UX를 100% 미러링하면서도 로컬 데이터, 로컬 공시 cache, 로컬 AI provider를 쓰는 것이다.
- 단기 bridge로 React 안에 Svelte terminal을 붙일 수는 있지만, 장기적으로는 접착 코드와 중복 상태가 늘어난다.

따라서 목표는 `landing` UI를 로컬에 복사하는 것이 아니다. 제품 UI 원본을 공용 UI 플랫폼으로 승격하고 public/local 배선을 같은 계약으로 통제하는 것이다.

---

## 2. 제품 목표

1. GitHub Pages 공개 UI와 로컬 AI UI가 동일한 디자인 언어를 사용한다.
2. public/local terminal은 같은 `TerminalSurface`를 렌더한다.
3. public/local viewer는 같은 `ViewerSurface`를 렌더한다.
4. 로컬 앱은 terminal UX를 그대로 쓰면서 local DB/cache/API와 AI provider를 연결한다.
5. 공개 앱은 같은 surface를 쓰되 static/HF/GitHub Pages 데이터와 public-safe runtime을 쓴다.
6. 로컬에는 챗모드와 터미널모드가 있다.
7. 터미널모드는 단순 dashboard가 아니라 가격, 재무, 공시, viewer, screener, export, evidence, cache, AI tool을 다루는 운영 화면이다.
8. 공시뷰어, terminal, company, chart, evidence UI 구현은 한 벌만 존재한다.

---

## 3. 엔지니어링 목표

1. 앱 간 내부 `src` import를 금지한다.
2. 공용 패키지를 통한 단방향 의존만 허용한다.
3. 모든 데이터 호출, viewer URL, AI 호출, navigation, storage, feature flag는 runtime adapter 뒤로 숨긴다.
4. Svelte surface가 `/api`, HF URL, `$app/paths`, `localStorage`, `window.location`에 직접 의존하지 않게 한다.
5. 디자인 토큰과 surface CSS를 중앙화해 public/local 시각 차이를 제거한다.
6. local-only AI, file, DB 권한 코드를 공용 surface에 넣지 않는다.
7. public-only GitHub Pages/HF URL을 공용 surface에 하드코딩하지 않는다.

---

## 4. 운영 목표

1. 대형 리팩토링 시작 전 현재 안정 상태를 PyPI에 한 번 올리고 기준 commit/tag를 기록한다.
2. 리팩토링 기간 중 `ui/web`은 legacy fallback으로 유지한다.
3. `landing`은 리팩토링 완료 전까지 무중단이어야 한다.
4. 각 작업 단위는 독립 검증 가능해야 한다.
5. 실패 시 이전 기준 commit 또는 fallback UI로 되돌릴 수 있어야 한다.
6. 계획 문서는 `mainPlan` 문서 세트 안에서만 관리한다.

---

## 5. 하지 않을 것

1. `landing/src/lib/terminal`을 `ui/local`로 복사하지 않는다.
2. `ui/apps/local`을 새 제품 UI 원본으로 만들지 않는다.
3. `landing`과 `ui/apps/local`이 서로의 `src` 내부를 import하지 않는다.
4. React `ui/web`을 초기에 바로 제거하지 않는다.
5. 기존 public site의 blog, docs, SEO, sitemap, static content를 초기 단계에서 옮기지 않는다.
6. runtime adapter 계약 없이 화면 컴포넌트를 대량 이동하지 않는다.
7. 화면을 비슷하게 보이게 하려고 CSS override를 덕지덕지 붙이지 않는다.
8. AI provider key, provider SDK, local file permission을 surface에 노출하지 않는다.
9. public route에 local-only API 또는 secret 설정을 노출하지 않는다.
10. 대형 파일 이동과 동작 변경을 같은 작업 단위에 섞지 않는다.

---

## 6. 핵심 사용자 흐름

### 6.1 Public Terminal

사용자는 GitHub Pages 공개 사이트에서 회사를 검색하고 terminal 화면을 연다.

기대:

- 같은 terminal layout을 본다.
- static/HF/public-safe 데이터만 사용한다.
- AI는 disabled 또는 public-safe explain/demo 상태로 표시된다.
- local-only service command는 숨김 또는 disabled 상태다.
- 기존 공개 URL과 deep link가 유지된다.

### 6.2 Local Chat Mode

사용자는 로컬 앱에서 챗모드로 질문한다.

기대:

- AI provider는 로컬 설정을 통해 직접 연결된다.
- 모든 요청은 Ask 엔진을 통한다.
- 회사 검색, 최근 회사, workspace context를 기반으로 terminal mode 전환이 가능하다.
- 같은 Ask thread와 evidence context가 terminal mode로 이어진다.

### 6.3 Local Terminal Mode

사용자는 챗모드 또는 route에서 terminal mode로 들어간다.

기대:

- 별도 탭 없이 전체 terminal 화면이 열린다.
- 좌측은 탐색/검색/필터, 중앙은 chart/시각화/fullscreen, 우측은 정기공시/정성 정보/서비스 패널이다.
- 정기공시 리스트와 viewer는 terminal 우측 패널 또는 fullscreen 흐름에서 동작한다.
- 가격, 재무, 공시, viewer, screener, export, cache refresh, AI tool 대부분이 service command로 접근 가능하다.

### 6.4 Viewer

사용자는 terminal 또는 company 화면에서 viewer를 연다.

기대:

- standalone viewer와 terminal overlay가 같은 `ViewerSurface`를 쓴다.
- TOC, period timeline, panel matrix, compare matrix, ask drawer가 한 surface 안에 있다.
- 선택 문단/표/기간이 evidence로 Ask 엔진에 전달된다.

---

## 7. 성공 기준

제품 성공:

1. public/local 화면이 같은 제품처럼 보인다.
2. 로컬에서 AI provider를 연결해 챗모드와 터미널모드를 모두 쓸 수 있다.
3. terminal mode에서 주요 로컬 서비스가 command palette 또는 service panel로 접근 가능하다.
4. viewer와 terminal이 같은 evidence와 source 표시 규칙을 쓴다.
5. 공개 사이트 사용자는 리팩토링 기간 동안 중단을 경험하지 않는다.

엔지니어링 성공:

1. public/local surface fork가 없다.
2. adapter conformance test로 데이터 계약 drift를 잡는다.
3. 디자인 token drift가 없다.
4. `landing/src`와 `ui/apps/local/src` 사이 직접 import가 없다.
5. `ui/web`은 fallback 이후 삭제 가능 상태가 된다.
