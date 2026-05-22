---
id: engines.dashboard.viewerSpec
title: viewerSpec — 공시뷰어 UI 설계 v1.0
kind: curated
scope: builtin
status: observed
category: engines
purpose: viewerSpec 은 dartlab landing 의 공시뷰어 (sections viewer) UI 설계 SSOT 다. 다크 배경 (#050811) 위 한글 본문 가독성 + 컴플라이언스팀 스크린샷 정확성 + 50+ 보고서 빠른 스캔 3 원칙 위 typography · diff · timeline · table 규칙을 명시. 트리거 — '공시뷰어', 'viewer 디자인', 'diff 표시', '취소선'.
whenToUse:
  - viewer
  - 공시뷰어
  - 다크 본문 가독성
  - diff 표시
  - 한글 한 글자당 50자/줄
  - section timeline
  - 테이블 정렬
inputs:
  - section text + table payload
  - 기간 timeline
  - diff (선택 시점 ↔ 직전 동주기)
outputs:
  - 다크 본문 (rgba 0.82) + heading 계층
  - diff 색상 (삭제 빨강 흐림 / 추가 초록 정상)
  - 좌→우 최신→과거 timeline
  - sticky 첫 컬럼 + tabular-nums 표
capabilityRefs: []
toolRefs:
  - EngineCall
  - RunPython
knowledgeRefs:
  - engines.company.sections
  - engines.dashboard
sourceRefs:
  - dartlab://skills/engines.dashboard.viewerSpec
requiredEvidence:
  - target
  - period
  - topic
expectedOutputs:
  - 본문 폰트 14px / 줄간격 1.85 / 최대 너비 720px
  - 다크 배경 #050811 + 본문 rgba(241, 245, 249, 0.82)
  - 좌→우 최신→과거 timeline
  - 취소선 0 (한글 글리프 읽기 불가)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: supported
  pyodide:
    status: limited
failureModes:
  - 한글 본문에 취소선 (글리프 가독성 0)
  - 본문 폰트 13.5px (한글 밀도 부족)
  - 최대 너비 900px (한글 50자/줄 초과)
  - 본문 색상 rgba 0.75 (다크 배경에서 너무 어두움)
  - annotated blame 색칠 (크리스마스 트리)
  - 테이블 컬럼 자체 정렬 (원본 행 순서 변형)
forbidden:
  - 다크 배경에서 한글 본문에 취소선 사용
  - 본문 행 최대 너비 720px 초과
  - 테이블 정렬 변경 — 원본 행 순서 유지
  - 본문에 아이콘 사용 (TOC 한정)
  - 애니메이션 300ms 초과
examples:
  - 다크 본문 14px / 1.85 / 720px
  - 삭제 diff 좌측 3px 빨강 + 텍스트 흐림
  - 좌→우 timeline 절대 라벨 (2025 · 2025Q1)
procedure:
  - text section 상단 timeline — 좌(최신) → 우(과거).
  - timeline 클릭 시 선택 period 원문 + 직전 동주기 diff 렌더.
  - 같은 button 재누름 → 최신 원문 복귀.
  - 테이블은 본문 뒤 별도 구간, 첫 컬럼 sticky.
  - 본문 색상 rgba(241, 245, 249, 0.82) + 폰트 14px + 줄간격 1.85.
linkedSkills:
  - engines.company.sections
  - engines.dashboard
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-12'
---

## 엔진 역할

`viewerSpec` 은 dartlab landing 의 공시뷰어 UI 사양서. python capability 가 아니라 SvelteKit 페이지 디자인 SSOT 다.

3 원칙:

1. **스캔 속도** — 애널리스트가 50 + 보고서를 아침에 봄. 인지 부하 최소화.
2. **증거 수준** — 컴플라이언스팀이 스크린샷 찍음. 기간 / 출처 모호함 없음.
3. **다크 가독성** — 배경 `#050811` 에서 팔 길이 거리에서 읽을 수 있어야 함.

## 공개 호출 방식

본 spec 은 landing 빌드의 다음 라우트에서 적용:

- `/company/[code]/sections/[topic]` — section viewer
- `/company/[code]/diff/[topic]` — 기간 diff 표시

CSS 변수 · component prop 매핑:

```css
.docViewerBody {
  font-size: 14px;
  line-height: 1.85;
  max-width: 720px;
  color: rgba(241, 245, 249, 0.82);
  margin-bottom: 10px;
}
.docViewerDiffDelete {
  border-left: 3px solid var(--diff-delete);
  background: rgba(220, 50, 50, 0.08);
  color: rgba(241, 245, 249, 0.55);
}
.docViewerDiffAdd {
  border-left: 3px solid var(--diff-add);
  background: rgba(50, 200, 50, 0.08);
  color: rgba(241, 245, 249, 0.82);
}
```

## 호출 동작

### 본문 텍스트

- **기본 단위는 topic 이 아니라 body text block**
- **기본 문서는 textDocument (section timeline snapshot)**
  - heading 블록은 다음 body 블록의 section header 로 흡수
  - body 앞머리의 짧은 heading line 도 구조 anchor 로 분리
  - 각 section 은 `latest`, `timeline[]`, `views[label]` 를 가진다
  - `views[label]` 는 `선택 period 원문 + 직전 동주기 diff` 를 담는다
  - 최신 topic 기간과 다르면 `과거 유지 (stale)` 배지 표시
- 기본 화면은 `최신 원문` 우선
  - 처음에는 diff 를 열지 않는다
  - section timeline 클릭 시에만 해당 시점 변화가 열린다
  - 테이블 / 정형 데이터는 텍스트 문서 뒤 별도 구간으로 분리
- 폰트: 14px (13.5 아님 — 한글 밀도 고려)
- 줄간격: 1.85
- 문단 간격: margin-bottom 10px
- 최대 너비: 720px (900 아님 — 한글 50 자/줄 최적)
- 본문 색상: `rgba(241, 245, 249, 0.82)` (0.75 는 너무 어두움)

### 제목 계층

- `[대괄호]` — mt-32 mb-10, 15px, bold 700
- `가. 나.` — mt-24 mb-8, 14.5px, semibold 600
- `(1) (가)` — mt-16 mb-6, 14px, medium 500, opacity 0.88

### Diff 표시 (변경 사항)

**취소선 절대 금지** — 한글 글리프에서 읽기 불가능.

- diff 는 `선택 시점 원문 위치` 기준으로 붙인다.
- 삭제 — 좌측 3px 빨간 테두리 + rgba 배경 + 텍스트 0.55 투명도 (읽을 수 있지만 흐림)
- 추가 — 좌측 3px 초록 테두리 + rgba 배경 + 텍스트 0.82 투명도 (정상 밝기)
- 숫자 — 이전값 (흐림) → 현재값 (굵게 밝게)
- 문단 granularity 우선, 토큰 diff 는 digest 의 숫자 / 짧은 구절에만 제한

### 타임라인

- **위치** — 각 text section 상단
- **방향** — 좌 = 최신, 우 = 과거 (테이블 컬럼과 동일)
- 절대 라벨 표시 (`2025`, `2025Q1`, `2024Q3`)
- 클릭 — 해당 시점 원문과 직전 동주기 diff 렌더
- 같은 버튼 재누름 — 최신 원문 상태로 복귀
- 10 기간 초과 시 최근 10 개만 표시

### 테이블

- **기간 정렬 — 최신 먼저 (역순)**
- 단위 — 테이블 위 우측 정렬
- 첫 컬럼 sticky, 배경 불투명
- 숫자 — `tabular-nums`, 우측 정렬
- zebra — `rgba(255, 255, 255, 0.012)` (매우 약하게)
- hover — `rgba(255, 255, 255, 0.04)`

### 간격 규칙

| 사이 | 간격 |
|------|------|
| heading → 테이블 | 4px |
| body → digest | 12px |
| digest → 다음 블록 | 28px |
| 테이블 → 다음 heading | 28px |

## 대표 반환 형태

뷰어 페이지 상태 (Svelte component prop):

```ts
type SectionView = {
  topic: string;
  latest: { period: string; payload: string; type: "text" | "table" };
  timeline: { period: string; payload: string }[];   // 좌→우 최신순
  views: Record<string, {
    period: string;
    payload: string;
    diff: { delete: string[]; add: string[] };
  }>;
  stale: boolean;  // 최신 topic 기간과 불일치 시 true
};
```

## 제거 목록

| 항목 | 이유 |
|---|---|
| annotated blame 색칠 | 크리스마스 트리 효과 |
| 기본 화면 기간 선택기 | 본문 읽기 방해, 이력 패널로 이동 |
| 텍스트 더보기/접기 | 전문 표시 필수 |
| 취소선 | 한글 읽기 불가 |
| 애니메이션 300ms+ | 120ms 이하 |
| 본문에 아이콘 | TOC 에만 |
| 테이블 정렬 | 원본 행 순서 유지 |

## 검증 체크리스트

- [ ] 회사 개요 본문 읽기 가능 (24 인치 팔 거리)
- [ ] 각 section 에 최신 / 최초 / 상태 배지가 보이는가
- [ ] stale block 이 과거 유지로 표시되는가
- [ ] 타임라인을 누르면 해당 시점과 직전 동주기 diff 가 나온다
- [ ] 다시 누르면 최신 원문으로 돌아간다
- [ ] 취소선 어디에도 없음
- [ ] 삭제 diff 읽기 가능 (흐림이지 투명 아님)
- [ ] digest 숫자 변경 이전 / 현재 구분 명확
- [ ] 재무상태표 최신 기간이 왼쪽
- [ ] 첫 컬럼 sticky 정상
- [ ] 타임라인이 section 상단에서 절대 라벨로 보인다
- [ ] 720px 최대 너비

## 기본 검증

viewer spec 변경 시 동기화 경로:

- 위 체크리스트가 viewer 회귀 가드 (타임라인 토글 · sticky 첫 컬럼 · 최신기간 좌측 · 720px 최대 너비).
- viewer 라우트 (`landing/src/routes/company/[code]/docs/...`) 변경 시 본 sub-spec 체크리스트도 동시 갱신. 누락 시 사용자 시점 회귀.
- 결손 표시: viewer 가 비정상 상태일 때 빈 화면 X → "타임라인 로드 실패" 명시 + console 에 reason 출력.

## 변경 이력

- 2026-05-12 — `providers/dart/docs/dev/viewerSpec.md` → 본 sub-spec 통합 (Skill OS 운영 SSOT 승격)
