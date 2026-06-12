# 05. Validation, Release, Rollback

상태: v1 확정 기준 문서  
범위: 테스트, 시각 검증, PyPI 릴리스, GitHub Pages 검증, rollback/fix-forward, legacy 제거

---

## 1. 테스트 원칙

1. Surface는 fake runtime으로 테스트한다.
2. 네트워크 의존 단위 테스트를 금지한다.
3. public/local adapter는 같은 fixture로 conformance를 검증한다.
4. UI 작업은 console error 0을 기준으로 한다.
5. 시각 변경은 screenshot 기준을 남긴다.
6. `landing` build 실패는 작업 단위 완료 실패다.
7. 신규 stale reference, 신규 legacy import, 신규 public API drift는 실패다.

---

## 2. 단위 테스트

대상:

- contracts type guard
- runtime adapters
- service registry
- tool registry
- model selectors
- viewer search index
- terminal derived metrics
- price/filing normalize

합격:

- 네트워크 없이 실행
- fake runtime fixture green
- public/local type conformance green

---

## 3. 통합 테스트

대상:

- public runtime + `TerminalSurface`
- local runtime + `TerminalSurface`
- local runtime + `ViewerSurface`
- public runtime + disabled AI
- local runtime + enabled AI
- local terminal mode + services command
- chat mode -> terminal mode 전환

합격:

- route 직접 참조 없음
- local-only command public 노출 없음
- provider 없는 상태 graceful disabled
- provider 있는 상태 stream response 가능
- tool call 실패 표시

---

## 4. 브라우저 테스트

필수 route:

- `/chat`
- `/terminal/005930`
- `/ask`
- `/analysis/005930`
- `/analysis/005930/viewer`
- public terminal route
- public viewer route
- provider settings

필수 flow:

- chat -> terminal
- company search -> terminal
- terminal -> viewer overlay
- regular filing list -> filing open
- viewer selection -> Ask evidence
- service command palette -> command execute
- fullscreen open/close

합격:

- console error 0
- network 404 없음
- iframe/component viewer nonblank
- full-screen overlay close 가능
- keyboard Escape 동작
- focus restore

---

## 5. 시각 테스트

도구:

- Playwright screenshot
- pixel diff
- layout assertions
- canvas nonblank pixel check

필수 assertion:

- terminal main grid column count stable
- left rail visible
- center chart visible
- right panel visible
- regular filing list visible
- viewer overlay width/height >= viewport 95%
- text overflow 없음
- panel overlap 없음
- button text clipping 없음
- chart axis/toolbar/tooltip 존재
- command palette keyboard navigation

Viewport:

- 1440x900
- 1280x720
- 1024x768
- 390x844
- 1920x1080

---

## 6. Landing 무중단 검증

각 UI 전환 작업 단위에서 확인한다.

필수:

- `landing` build
- public home route
- blog route
- docs route
- SEO metadata route
- sitemap
- static asset
- 기존 product deep link
- GitHub Pages base path
- asset path
- deep link refresh

실패 시:

- 작업 단위 완료 금지
- 기본 route 전환 되돌림
- wrapper/hidden route로 격리

---

## 7. PyPI 릴리스 전 검증

릴리스 전 순서:

1. CHANGELOG 사용자 관점 작성
2. local UI build
3. package copy
4. wheel build
5. wheel bundle 검증
6. local preflight
7. Guard/UI/landing/e2e 통과

필수 gate:

```text
uv run python -X utf8 tests/run.py preflight
Guard strict/full
ui app typecheck/build/test
landing check/build
필요한 Playwright
wheel bundle smoke
```

원칙:

- version bump는 마지막에 한 번만 한다.
- tag와 pyproject version 불일치 금지.
- 미해결 회귀가 남은 상태에서 릴리스하지 않는다.

---

## 8. PyPI 릴리스 후 검증

새 venv에서 검증한다.

필수:

```text
pip install -U dartlab==X.Y.Z
Company("005930")
주요 API smoke
local server boot
local UI serve
asset loading
/chat
/terminal/005930
/analysis/005930
/analysis/005930/viewer
provider settings 화면
```

실패 원칙:

- 같은 version 덮어쓰기 금지
- 새 patch로 fix-forward
- 임시로 `DARTLAB_UI_DIR`로 이전 build 지정 가능해야 한다.

---

## 9. Rollback과 Fix-forward

작업 단위 중 실패:

- 해당 작업 단위 변경만 되돌린다.
- 다른 세션의 변경은 되돌리지 않는다.
- `ui/web` fallback과 `landing` wrapper가 유지되어야 한다.

릴리스 전 실패:

- 기본 route 전환을 되돌린다.
- hidden route 또는 feature flag off 상태로 둔다.
- failing test를 기존 실패/신규 실패로 분류한다.

릴리스 후 실패:

- PyPI artifact는 immutable로 본다.
- rollback이 아니라 새 patch fix-forward로 처리한다.
- local/desktop은 `DARTLAB_UI_DIR`로 이전 build 지정 가능성을 유지한다.

공개 사이트 실패:

- 미검수 상태를 publish하지 않는다.
- 공개 route가 깨지면 즉시 기존 wrapper/fallback으로 복귀한다.
- content route는 제품 route 전환과 별도로 보호한다.

---

## 10. Legacy 제거 조건

`ui/web` 제거 전 조건:

1. `ui/web/src/features/terminalSvelte` 참조 0
2. `svelteKitCompat` 참조 0
3. `$lib` migration alias 0
4. `.svelte` React mount 참조 0
5. React-only terminal route 호출 경로 0
6. `/chat`, `/terminal/:code`, `/analysis/:code`, `/analysis/:code/viewer` parity 통과
7. publish workflow와 server UI build 경로가 새 local app을 기준으로 동작
8. PyPI 후검증 1회 이상 green
9. fallback 실제 호출 경로 0
10. landing public route 무중단 검증 완료

삭제는 default switch와 같은 작업 단위에 섞지 않는다. 별도 최종 작업 단위로만 처리한다.

---

## 11. 최종 완료 Gate

최종 완료 전:

- public/local terminal same surface
- public/local viewer same surface
- local AI through `AiPort` and Ask engine
- terminal services through `ServicesPort`
- design tokens centralized
- landing product UI source removed or wrapper-only
- landing content routes intact
- GitHub Pages artifact green
- local wheel smoke green
- screenshot parity acceptable
- console error 0
- `ui/web` fallback removed or archive state confirmed
