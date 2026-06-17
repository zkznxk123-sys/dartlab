# 05. 검증 · 리스크 · 롤백

상태: 설계 v0.1
범위: 구현 시 필요한 검증과 주요 실패 모드.

---

## 1. 영향 파일

기획 기준 예상 영향 파일이다. 구현 전 재조사한다.

### UI surface

- `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte` — 신규 다이얼로그.
- `ui/packages/surfaces/src/terminal/lib/macroLens.ts` — 신규 view-model.
- `ui/packages/surfaces/src/terminal/TerminalSurface.svelte` — open state와 다이얼로그 mount.
- `ui/packages/surfaces/src/terminal/panels/LeftRail.svelte` — 마켓 펄스/섹터 칩 진입점.
- `ui/packages/surfaces/src/terminal/panels/CenterStack.svelte` — KPI ticker 진입점.
- `ui/packages/surfaces/src/terminal/charts/ChartMenus.svelte` — ECON 메뉴 진입점 또는 액션.
- `ui/packages/surfaces/src/terminal/charts/ChartRibbon.svelte` — 전체화면 ECON 진입점.
- `ui/packages/surfaces/src/terminal/terminal.css` — 다이얼로그 스타일.

### contracts/runtime

첫 구현은 contracts/runtime 변경 없이 가능해야 한다. 변경이 필요하면:

- `ui/packages/contracts/src/macro.ts` — MacroLens 타입 export 여부.
- `ui/packages/runtime/src/adapters/public/sources/macroSource.ts` — 기존 `MacroPort` 확장 여부.
- `ui/packages/runtime/src/data/origins` — 새 artifact origin이 필요한 경우만.

### tests

- `tests/audit/checkUiDataWiring.mjs` 또는 현재 UI data wiring audit — raw fetch/URL/cache 회귀 확인.
- ui package check/build.
- Playwright visual smoke.

---

## 2. 영향 함수/심볼

예상 신규 심볼:

- `MacroLensDialog` — Svelte dialog component.
- `buildMacroLensSnapshot()` — terminal data → dialog view-model.
- `MacroLensSnapshot` — view-model type.
- `MacroLensOpenState` — open tab/focus state.
- `openMacroLens(tab, focusId?)` — TerminalSurface 또는 store 함수.

이름은 camelCase/PascalCase 규칙을 따른다.

---

## 3. 테스트

구현 시 기본 검증:

```bash
npm run check -w @dartlab/ui-runtime
npm run check -w @dartlab/ui-surfaces
npm run build -w @dartlab/ui-surfaces
uv run python -X utf8 tests/audit/dartlabGuard.py quick
```

UI 데이터 배선 변경 시:

```bash
node tests/audit/checkUiDataWiring.mjs
```

정확한 audit 명령은 구현 직전 현재 repo에서 재확인한다.

브라우저 검증:

- public terminal에서 좌측 마켓 펄스 → 다이얼로그 열림.
- KPI ticker 지표 → 지표 탭 해당 row focus.
- 차트 ECON 메뉴/리본 → 다이얼로그 열림.
- 다이얼로그 row `차트에 겹치기` → ECON 오버레이 토글.
- `:8400` 로컬 백엔드 없이 public floor 동작.
- 모바일/좁은 폭에서 다이얼로그 탭·표가 넘치지 않음.

정직 문구 검증:

- DOM에 `매수`, `매도`, `목표주가`, `위기 임박`, `수혜 확정`이 Macro Lens 문맥에서 등장하지 않아야 한다.
- `상관은 인과가 아님` 문구가 co-movement 근처에 있어야 한다.

---

## 4. 주요 리스크

| 리스크 | 설명 | 대응 |
|---|---|---|
| stale macro | `macro.json` asOf가 오래되면 국면 오해 | 기준일 상단 고정, staleRisk 라벨 |
| 인과 오독 | corr를 영향으로 읽음 | Co-Movement Falsifier로 명명, 인과 아님 라벨 |
| 지표 과밀 | 40개 지표가 카드 벽이 됨 | 그룹 표, 다섯 탭 상한 |
| L2 경계 침범 | macro/analysis 내부 import 결합 | 첫 구현 UI view-model only |
| public/local 드리프트 | local만 되는 기능이 생김 | public floor 우선, notWiredYet 라벨 |
| 메모리 위험 | macro summary를 회사별 Python 호출 | 브라우저 HF 산출물 재사용, 회사별 macro 호출 금지 |
| 추천처럼 보임 | macro score를 종목 판단으로 오해 | 점수/등급 대신 경로·checkpoint 표시 |
| 결손 은폐 | missing을 0 또는 중립으로 처리 | missing ledger와 출처 탭 |

---

## 5. 롤백

구현 시 단일 UI commit으로 묶는다.

롤백:

```bash
git revert <sha>
```

새 HF artifact나 sync workflow가 추가된 경우에는 UI commit과 산출물/sync commit을 분리하고 각각 revert 가능하게 한다. public/local 화면 작업은 운영자 명시 승인 전 push하지 않는다.

---

## 6. 평가

### 개발자 렌즈

- 기존 `MacroPort`, `macro.json`, `co.tailwind`, `rankCoMovers`를 재사용하므로 첫 구현 blast radius가 낮다.
- 위험한 부분은 새 데이터 호출과 L2 내부 import다. 문서에서 첫 구현을 UI view-model only로 제한해 회피가 아니라 경계를 지킨다.
- 다이얼로그가 차트를 복제하지 않도록 `차트에 겹치기` 액션만 제공한다.
- 회귀 기반 심층 분석은 nObs/R²/기준기간 계약 전까지 Phase 5로 미뤘다.

### PM 렌즈

- 사용자 목표는 "경제지표를 보는 것"이 아니라 "이 종목에 닿는 외부환경을 이해하는 것"이다. 5탭 구조가 이 목표에 맞다.
- 상주 패널을 늘리지 않으므로 터미널 밀도와 기존 워크플로를 해치지 않는다.
- 첫 성공 기준이 30초 3질문이라 수용성이 명확하다.
- 강한 분석은 많지만, 출시 범위는 전파 경로와 반증 조건으로 제한해 과장 리스크를 줄였다.

