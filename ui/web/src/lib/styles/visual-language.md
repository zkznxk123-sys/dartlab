# UI/Web 시각 언어 SSOT

> ui/web 의 시각 표현 단일 진원천. 컴포넌트별 즉흥 스타일을 막는 룰.
> 정체성: **분석 워크벤치 — 채팅 UI 가 아니라 분석 흐름의 표면.**
> 단 진입·대화 표면은 부드러워야 한다.

이 문서는 ui/web 안에서 정합성을 강제한다. 토큰 정의는 [app.css](../../app.css), 의미 클래스 인덱스는 본 문서의 §6.

---

## 1. 정보 위계

가장 위가 가장 강한 시각 강조. 한 메시지 안에서 이 순서가 *시각적으로* 드러나야 한다.

| 순위 | 종류 | 어디에 |
|---|---|---|
| 1 | **view-spec** (차트·테이블·대시보드) | 분석의 주체. 본문 안에 또는 우측 패널에 풀 사이즈로 |
| 2 | **text** (markdown 답변) | 본문 폭 가득 |
| 3 | **tool / activity** | footnote 농도 (`dl-text-dim`, 11px) |
| 4 | **refs / artifacts / 칩** | 작은 알약, 한 종 |

**원칙**: tool/activity 가 text 보다 시각적으로 앞서면 안 된다. 도구 호출은 *증거 footnote* 이지 답변이 아니다.

---

## 2. 컨테이너 1 종 원칙

지금까지 ConversationMessage 한 곳에 컨테이너 5 종 (rounded-2xl/lg/xl/full) + 보더 농도 4 종 + 배경 농도 3 종이 혼재. **이 즉흥성이 "더러움" 의 정체.** 폐기.

### 표준 컨테이너 (1 종)

```css
/* tailwind */
rounded-md border border-dl-border/30 bg-dl-bg-card/40
```

또는 의미 클래스 `.tool-run-card`, `.assistant-surface` (§6 참조).

### 강조는 *padding 과 폰트 크기* 로

- 약: padding `0.5rem 0.75rem`, font 11px
- 중: padding `0.75rem 1rem`, font 13px
- 강: padding `1rem 1.25rem`, font 15px

### 예외 (의미 충돌 방지)

- **failure** — `border-red-500/35 bg-red-500/10` (의미 클래스: `.failure-notice`)
- **view-spec** — 보더 없는 풀폭 캔버스 (분석 결과는 시각 자체가 컨테이너)

이외 모든 카드는 표준 컨테이너 1 종. **rounded-2xl, rounded-xl, rounded-full 신규 사용 금지** (기존 사용처는 4 단계 채팅 표면 재설계에서 정리).

---

## 3. 아바타 규칙

### 출현 빈도

- **대화 단위 1 회 또는 0 회.** 응답 시작 헤더에서만 등장.
- **activity·tool·artifact 단위 절대 금지.** (ConversationMessage activity-group 마다의 7x7 아바타 폐기 대상.)
- **사이드바 collapsed 상태**: Brand 1 회만. 대화 항목마다 MessageSquare 반복 폐기.

### 자산 사용

- 기본: `/avatar.png`
- 컨텍스트 변종 (이미 `public/` 에 12 종 존재 — `avatar-analyze.png`, `avatar-chart.png`, `avatar-code.png`, `avatar-curious.png`, `avatar-detective.png`, `avatar-discover.png`, `avatar-singing.png`, `avatar-study.png`, `avatar-verify.png`, `avatar-celebrate.png`, `avatar-writing.png`)
- **변종 사용 원칙**: 한 응답 안에서는 *같은 변종*. 변종 전환은 대화 단위 또는 응답 시작 시점에만. 도중에 깜빡이듯 바뀌면 안 됨 (시각 안정성 우선).

### 크기

- 응답 헤더: 24x24 또는 28x28
- 사이드바 Brand: 24x24
- 그 외 위치 사용 금지

---

## 4. 진행 표현 어휘 (단일)

같은 "진행 중" 정보를 4 가지 방식으로 표현하던 중복 폐기. **메시지당 인디케이터 1 개.**

### 금지 패턴 (현재 ConversationMessage)

❌ "응답 중" 라벨 + Loader2 + activity-group progress bar + tabular-nums 시간 + 단계 카운트 + status 아이콘 동시 노출

### 표준 패턴

✓ Cursor 스타일 한 줄. 의미 클래스: `.work-progress`, `.work-progress-row`, `.work-progress-active`.

```
[icon] [phase 11px bold] [text 11px ellipsis]
```

예:
```
🔵  scan         Polars 행 23,481 → 매출 컬럼 추출 중
✓   evidence     ref 14 발급 완료
🔵  review       시각화 spec 결정 중...
```

### 어휘

- 진행 중: phase 색 = `dl-text-muted`, icon = pulse 또는 spinner-sm
- 완료: phase 색 = `dl-text-dim`, icon = check (조용히)
- 오류: phase 색 = `dl-primary-light`, icon = alert

진행률 (%) 가 *의미 있는* 경우만 한 줄 안에 추가 (`23%`). progress bar 와 tabular-nums 시간 동시 노출 금지.

### 펼침

기본 접힘. 사용자가 "어떻게 진행됐나" 궁금할 때만 펼침. 펼침 어휘: `<details>` + `.assistant-activity-details`.

---

## 5. 아이콘 사용 규칙

### 의미 단위 1 회

같은 의미 (status) 에 아이콘 2 개 동시 노출 금지.

❌ `CheckCircle2` + `Terminal` 동시 — status 와 종류를 둘 다 박는 것
✓ `Terminal` + 텍스트로 status 표현 ("완료")

### 종류 제한

- **컴포넌트당 lucide 아이콘 import ≤4 종.**
- 같은 의미군 (status: check / alert / loader / clock) 에서 2 종 이상 사용 시 의도 명문화.

### 색

- status 아이콘은 의미 색 1 종:
  - 진행 중: `dl-accent` (orange)
  - 완료: `dl-text-dim` (조용히, success 색 X)
  - 경고: `dl-warning` (amber)
  - 오류: `dl-primary-light` (red)
- 의미 없는 장식 아이콘 (`Sparkles`, `Circle`) 금지.

---

## 6. 의미 클래스 인덱스 (app.css 정의 — 우선 사용)

**중요**: 아래 클래스들이 이미 [app.css](../../app.css) 에 정의되어 있다. 컴포넌트는 인라인 tailwind 를 쓰기 전에 *반드시* 이 클래스를 확인하고 우선 사용한다.

### 응답 표면

| 클래스 | 용도 |
|---|---|
| `.assistant-surface` | 응답 컨테이너 (gap 8px, max-w 100%) |
| `.assistant-answer` | text 본문 (15px, line-height 1.75) |
| `.assistant-activity` | activity 그리드 (11px, dim) |
| `.assistant-activity-head` | activity 헤더 (24px min-height) |
| `.assistant-activity-row` | activity 항목 한 줄 |
| `.assistant-activity-details` | 펼침 details |

### 도구 실행

| 클래스 | 용도 |
|---|---|
| `.tool-run-card` | 도구 카드 (보더 1px / radius 6px) |
| `.tool-run-error` | 오류 변종 |
| `.tool-run-header` | grid 4 칼럼 헤더 |
| `.tool-run-name` / `.tool-run-summary` | 이름·요약 |
| `.tool-block` / `.tool-header` / `.tool-section` | 확장형 도구 IN/OUT/LOG 섹션 |

### 진행 표시

| 클래스 | 용도 |
|---|---|
| `.work-progress` | 컴팩트 trace |
| `.work-progress-row` | grid 3 칼럼 (icon · phase 72px · text) |
| `.work-progress-active` | 현재 단계 강조 |

### 실패

| 클래스 | 용도 |
|---|---|
| `.failure-notice` | 실패 알림 (red 28% / 6% bg) |
| `.failure-retry` | 재시도 버튼 |

### 아티팩트 / 인용

| 클래스 | 용도 |
|---|---|
| `.artifact-preview`, `.source-strip` | 칩 1 종 (radius 6px / dl-text-muted) |
| `.cite-ref` | 인용 super 번호 |

### Markdown / Table

| 클래스 | 용도 |
|---|---|
| `.prose-dartlab` | 답변 markdown 본문 |
| `.finance-table` | 재무 표 (sticky 첫열) |
| `.structured-table` | 일반 구조화 표 |
| `.code-fold` | Python > 3 줄 자동 접기 |
| `.code-block-wrap` + `.code-copy-btn` | 코드 블록 + 복사 |

### Skeleton / 입력

| 클래스 | 용도 |
|---|---|
| `.skeleton-line`, `.skeleton-block` | 로딩 placeholder |
| `.input-box`, `.input-textarea`, `.send-btn` | 입력 영역 |

**원칙**: 새 컨테이너가 필요하면 위 인덱스에서 가장 가까운 클래스를 *재사용*. 없으면 본 인덱스에 *추가* 후 [app.css](../../app.css) 에 정의. **컴포넌트 안에 인라인 tailwind 로 카드 스타일 새로 만들기 금지.**

---

## 7. 색·폰트

### 색

- `dl-*` 토큰만 사용. 인라인 hex·rgb 금지.
- text 위계 3 단: `dl-text` (본문) > `dl-text-muted` (보조) > `dl-text-dim` (footnote). **4 종 이상 금지** (현재 `/dim/80`, `/dim/85`, `/dim/60` 같은 농도 분기 폐기).

### 폰트 크기

컴포넌트당 ≤3 종. 표준 4 단:

| 토큰 | 크기 | 용도 |
|---|---|---|
| `--text-body` | 15px | 답변 본문 |
| `--text-body-sm` | 13px | 보조 / 라벨 |
| (인라인) | 12px | 도구 이름·아티팩트 |
| `--text-meta` | 11px | footnote / activity |

10px 사용은 *uppercase tracking 라벨* 에서만 (예: `WORK PROGRESS`).

### 폰트 굵기

`--font-weight-*` 토큰만 사용. `font-bold` (700) 은 데이터 강조 (숫자) 에서만. 본문 강조는 `font-semibold` (600).

---

## 8. 부드러움 (motion)

### 토큰

- `--motion-fast: 120ms` — hover, button state
- `--motion-base: 180ms` — 카드 transition, 펼침
- `--motion-slow: 260ms` — 페이지 전환, 사이드바

### 룰

- 스트림 도착 시 layout shift 금지. 새 part 추가는 `fadeInDraft 0.15s ease-out` (이미 정의됨).
- 카드 hover/active: `--motion-fast` 이내.
- 펼침 (chevron rotate): 200ms ease-out.
- `prefers-reduced-motion: reduce` 준수 (이미 정의됨).

### 스트림 깜빡임 방지

- 새 part 가 본문에 추가될 때 기존 본문이 jump 하지 않게 `min-height` 확보.
- code block 스트리밍 시 `.message-live-tail pre::after` 의 typing 애니메이션 사용.
- `content-visibility: auto` + `contain-intrinsic-size` 로 재계산 비용 감축 (이미 `.message-committed` 에 적용됨).

---

## 9. 사이드바 룰 (5 단계 재설계 시 적용)

- **그룹 라벨 폐기** — 오늘/어제/이번 주/이전 4 헤더 제거. 핀 영역만 분리.
- **MoreHorizontal hover 메뉴 폐기** — 키보드 단축키 (E 이름변경, P 핀, D 삭제) + 우클릭 컨텍스트 메뉴.
- **Brand 축소** — 8x8 아바타 + 캡션 → 워드마크 또는 텍스트 한 줄.
- **collapsed 정리** — MessageSquare 반복 폐기. 핀 표시 + 검색 입구만.

참조: Linear Inbox, Anthropic Claude.ai 사이드바.

---

## 10. landing 토큰과 정합

- `landing/src/lib/styles/tokens.css` 의 `dl-*` 네이밍·색 컨벤션 공유.
- ui/web `app.css` 변경 시 landing tokens.css 동시 검토. 충돌 시 *공통 기본은 landing*, *ui/web 전용 컴포넌트 클래스는 app.css*.
- 새 토큰 추가 시 두 파일 모두 등록.

---

## 11. 검사 (lint)

`scripts/dev/checkVisualLanguage.mjs` — 컴포넌트당 다음 카운트 임계 초과 시 경고:

| 항목 | 임계 |
|---|---|
| `rounded-(2xl\|xl\|sm\|full)` 종류 | ≤2 (failure 등 의미 예외 포함) |
| `border-dl-border/\d+` 농도 종류 | ≤2 |
| `bg-dl-bg-card/\d+` 농도 종류 | ≤2 |
| `<img src="/avatar` 출현 | ≤1 |
| `lucide-svelte` import 종류 | ≤4 |
| 인라인 hex·rgb 색 | =0 |

CI 또는 pre-commit 시 실행. 임계 초과는 경고 (실패 X) — 점진 마이그레이션 가능.

---

## 12. 변경 절차

1. 새 컨테이너·진행 표현·아이콘 사용처 등장 시 **본 문서 먼저 갱신** → app.css 의 의미 클래스 추가/수정 → 컴포넌트 적용.
2. SSOT 위반 발견 시 *새 룰* 가 아니라 *이미 있는 룰을 못 따른 사례*. 컴포넌트 수정으로 해결.
3. 본 문서와 app.css 가 어긋나면 **app.css 가 진실** (실제 렌더되는 것). 본 문서는 app.css 정합성 유지.

---

## 13. 마이그레이션 순서

본 SSOT 가 정립된 후 4 단계 (ConversationMessage 재작성) 와 5 단계 (Sidebar 재설계) 가 이 룰을 따른다. 기존 컴포넌트 일괄 변경은 점진:

1. **신규 컴포넌트** — SSOT 강제 적용.
2. **수정되는 기존 컴포넌트** — 손댈 때 SSOT 따라 정리.
3. **변경 없는 기존 컴포넌트** — lint 경고로 추적, 다음 큰 작업 시 정리.

ConversationMessage 와 Sidebar 는 4·5 단계 plan 에서 일괄 재작성 — 점진 마이그레이션의 예외.
