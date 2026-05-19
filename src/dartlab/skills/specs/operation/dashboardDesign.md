---
id: operation.dashboardDesign
title: 대시보드 배치·설계 원칙 (bento·정사각·위계·Playwright loop)
kind: curated
scope: builtin
status: observed
category: operation
purpose: dashboard 페이지의 카드 배치 규칙 · sub 분류 원칙 · 시각 위계 · 인터랙션 표준 · Playwright visual loop 의 SSOT. 외부 표준 (Apple WWDC25 / PatternFly / Geckoboard / Koyfin / Bloomberg) 합성. P-DASH-V1 통합.
whenToUse:
  - dashboard
  - layout
  - bento
  - sub category
  - visual hierarchy
  - interaction
  - playwright
  - 카드 배치
  - 화면 설계
inputs:
  - 카드 list (tab + sub)
  - 화면 viewport
outputs:
  - 페이지 layout (bento packing)
  - visual snapshot (Playwright PNG)
capabilityRefs: []
knowledgeRefs:
  - engines.dashboard.cardCatalog
  - engines.viz
sourceRefs:
  - dartlab://skills/operation.dashboardDesign
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
---

# 대시보드 배치·설계 원칙

## 1. Bento 5 원칙 (Apple/Vercel/shadcn 합성)

1. **의도적 비대칭** — 동일 grid 위 size 변주로 hierarchy. 모든 카드 같은
   크기 금지.
2. **size = 위계** — Apple WWDC25: 가장 큰 카드 = 가장 중요. dartlab: 자산구조
   dual-stack (XL 4×4) > KPI row 4×(1×1) > supporting trend (M 2×2).
3. **Gestalt 일관** — border radius / shadow / padding 통일. shadcn `rounded-2xl`
   + `gap-4 md:gap-6 p-6 shadow-sm`.
4. **6~12 블록 상한 (view 당)** — 15+ 시 인지부하. dartlab 4 sub × 6~12 카드.
5. **`grid-auto-flow: dense` + 모바일 1-col stack** — CSS Grid 만으로 packing.
   라이브러리 무도입 1차.

## 2. Sub 분류 원칙

- **회계 분류** (default) — dartlab 채택. 재무제표 4 sub: performance /
  capitalStructure / cashflow / risk.
- **질문 단위** (대안) — "돈 진짜 버나? / 망할 위험? / 적정가?". 학습 곡선 ↑.
- **전체 (overview)** = sub 포괄 아님. 5초 진단 view — scoreBadge + 핵심 카드
  + 흐름.

## 3. 시각 위계 (visual hierarchy)

읽기 순서 = narrative 흐름. F-pattern 변형 (top-left = hero).

```
[hero scoreBadge / dualStack hero]  ← 종합 결론
[KPI row × 4]                       ← 핵심 숫자
[supporting trend × 4]              ← 추세
[gauge + topList + phaseIndicator]  ← 위험 한눈
```

각 sub view 의 카드 순서는 `engines.dashboard.cardCatalog` 의 BLOCKS 정의 +
catalog 삽입 순서가 SSOT.

## 4. 인터랙션 표준

- **전역 period selector** (1Y/3Y/5Y/10Y/Max) — 페이지 단일, 카드 분산 금지.
- **Cross-card hover sync** — 한 시계열 hover → 모든 카드 같은 시점 vertical
  line 동기. Bloomberg/Koyfin 표준. (P-DASH-V2)
- **"왜?" drill-down** — gauge/lifeCycle/distress 클릭 → 분해 모달 (DuPont /
  Z 5 인자 / phase 신호). (P-DASH-V2)

## 5. Playwright Visual Loop — 강제 절차서 (P-DASH-V1 T4)

AI 가 catalog/frontend 수정 → frontend 빌드 → 화면 안 보고 "완료" 보고하는
회귀 패턴 차단. **본 절차 위반 시 "완료" 보고 자체가 무효**.

### 절대 규칙

1. dashboard 관련 코드 (`src/dartlab/viz/**`, `ui/web/src/features/dashboard/**`,
   `ui/web/src/routes/analysis.*.tsx`) 수정 시 **commit 직전** 반드시 PNG 검수.
2. PNG 검수 = `dashboardSnap.py` 호출 + Read tool 로 PNG 열어보기 + 결함 표
   본문 박기 (commit 메시지 또는 검수 보고문). **표 없이 "완료" 단어 금지.**
3. 결함 표는 사용자가 제시한 9 항목 또는 변경 트랙의 명시 요구를 행 단위로.
   각 행마다 ✅/⚠/❌. ❌ 가 1 개 이상이면 다음 트랙 또는 fix 후 재캡쳐.
4. backend 변경 (catalog/builder/adapters/layout) 시 uvicorn 재시작 강제 —
   reload 없으면 변경 무효 (TaskStop → 재기동).
5. 본 룰 위반 사례: 2026-05-17 P-DASH-V1 이전 — 9 요구 중 4 만 지키고
   "완료" 보고 → 사용자가 캡쳐로 4 위반 발견. 본 룰 박힘으로 차단.

### CLI

```bash
uv run python -X utf8 src/dartlab/viz/dashboardSnap.py \
    --code 005930 --views all --base http://localhost:5400 \
    --out .claude/snaps/{track}/ --wait 5000
```

`--base http://localhost:5400` (127.0.0.1 안 됨 — vite IPv6 only).
`--wait 5000` (recharts ResponsiveContainer + ResizeObserver 안정화).

### 5 항목 검수 항목

1. **시각 정사각·portrait**: cs=rs 카드는 width≒height. wide-strip (cs>rs) 은
   phaseIndicator 만 예외. PNG 픽셀 측정 (좌상~우하).
2. **카드 box fill**: 차트 영역이 카드 내부 70%+ fill. h={cellSize·rowSpan-header-footer}
   계산 정확.
3. **카드 내 콘텐츠 잘림 0**: KpiTile range bar "5y 최저/최고" 텍스트 안 잘림.
   ChartMiniTable footer 안 잘림. 라벨 truncate 0.
4. **wiring 실패 표시 0**: "시계열 데이터 없음", "데이터 없음" 카드 0.
   비어있으면 adapter dispatch 또는 dataSpec 추적.
5. **narrative 순서**: KPI 가 hero (좌상단), trend 가 본문, radar/gauge/topList
   가 분해/위험 (하단). _NARRATIVE_KIND_ORDER 가 강제.

### 결함 발견 시

다음 commit 또는 fix 단계 진입. **숨김 0**. 사용자가 발견하기 전에 본인이
표에 ❌ 박고 다음 트랙 정의. 부산물 무시도 위반.

### 대안 검토 (왜 Playwright 단독?)
- **Storybook + Chromatic** — 카드 단위 visual regression 우수, 통합 페이지
  부적합.
- **Percy / Loki** — 외부 service 의존.
- **VS Code Simple Browser** — 사람 검수만, 자동화 어려움.

→ Playwright 단독이 최적 (통합 + AI Read 자체 검수 + headless + 무료).

## 6. 외부 표준 인용

- **Apple WWDC25** `Build a great Liquid Glass app` — bento + 의도적 비대칭.
- **PatternFly Dashboard Guidelines** (RedHat) — 3-tier surface area.
- **Geckoboard Dashboard Design Playbook** — KPI 위계.
- **Koyfin Custom Dashboards** — financial dashboard 정통.
- **Bloomberg Terminal Launchpad** — 카드 자유 배치 + grid snap.
- **Simply Wall St Snowflake** — 5-축 score badge.
- **Stephen Few "Information Dashboard Design"** — 카드 = 의사결정 보조.

## Anti-Patterns

- ❌ catalog 의 모든 카드를 동일 size (M 2×2) 로 — bento 위계 손실.
- ❌ overview 에 모든 sub 카드 펼침 (15+) — 인지부하.
- ❌ KPI 카드 폭 절반만 사용 (우측 빈 공간) — KpiTile 사이즈 또는 sparkline.
- ❌ trend 카드 wide 4×2 강제 — 사용자 1 지시 (정사각 우선) 위반.
- ❌ 카드 수정 후 Playwright snap 누락 — visual 회귀 누적.
