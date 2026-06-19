# 05 · 정보구조 · UX · 인쇄

## 1. 진입 — 버튼

- 위치: `TerminalSurface` 헤더 topRight, "토론"/"이슈" 옆. lucide `FileText` + "보고서" 라벨(또는 아이콘 only + 툴팁).
- 대상: 현재 `?sym=` 회사. 클릭 → `loadStoryReport(sym)` → ReportDialog mount.
- 404(미발행) → 버튼 disabled 또는 클릭 시 "데이터 부족 — 보고서 미생성(사유)" 토스트.

## 2. 컨테이너 — 다이얼로그 1차, 라우트 P3

**다이얼로그 채택**(MacroLensDialog 전체화면 패턴, mount/unmount). 이유: 기존 패턴 재사용·종목 전환 빠름·무패널 증가(periodic-dossier "6번째 레일 기각" 정신). 전용 라우트(`/terminal/report?sym=&type=`, 공유링크/SNS 인용)는 **P3 polish 로 분리**.

**인쇄 격리.** 모달 scrim/board 가 `@media print` 오염 → 인쇄 타깃은 ReportDialog 본문 `.rptDoc` 만, 그 외 `display:none`.

## 3. 다이얼로그 IA (위→아래)

```
┌─ ReportDialog (.dlTerm scope) ──────────────────────────────┐
│ [메타바] 삼성전자 005930 · 2026Q1 · baked 2026-06-19         │
│          · 사이클 · 등급 A · "dartlab 엔진 자동생성"  [✕][🖨] │  ← 주체중립
├─────────────────────────────────────────────────────────────┤
│ [관점 sticky 탭]  경영요약*  신용  가치평가  성장  대시보드  …  │  ← publishable 만 활성
│                   (미충족 관점은 dim + "발행 기준 미달")        │     executive 기본
├─────────────────────────────────────────────────────────────┤
│ [focusQuestions 칩]  한 문장 결론은?  돈 버는 구조인가?  …      │  ← 참조HTML '한 줄 요약'
├─────────────────────────────────────────────────────────────┤
│ [SummaryCard]  결론 1줄(C-2 통과) · 강점 · 경고 · 영역등급      │  ← 참조HTML '종합 의견'
├─────────────────────────────────────────────────────────────┤
│ [EvidenceStrip]  ★점수 비노출 (F4)                            │
│   sector ●ready  [industry:position][industry:profitPool]    │  ← coverage + evidenceIds 칩만
│   financial ●ready [analysis:scorecard][credit:distress]      │
│   macro ○missing  (근거 미도달)                                │
├─────────────────────────────────────────────────────────────┤
│ [6막 섹션]  제N막 헤더 → 섹션 → 블록                            │
│   각 블록 우상단: [sourceEngine 배지: panel|analysis|credit…]  │  ← 출처 라벨
│   TableBlock=격자 · MetricBlock=KPI델타 칩 · FlagBlock=severity│
│   threads=좌측 색 바(severity) · ChartBlock→ChartRenderer      │  ← 손수 차트 금지
├─────────────────────────────────────────────────────────────┤
│ [하단] quality 정직라벨(접힘): "N섹션 생략 · M축 근거 미도달"   │  ← ★점수 비노출
│        푸터: "데이터 as-of · 모든 수치 출처 · 투자권유 아님"     │
│        [🖨 인쇄 / PDF 저장]                                     │
└─────────────────────────────────────────────────────────────┘
```

**관점 전환** = 탭 클릭 → `buildReportView` 재투영(데이터 재fetch 0, payload 1벌). 즉시.

## 4. 블록 렌더 매핑

| story 블록 | 렌더 | 비고 |
|---|---|---|
| TableBlock | `.dlTerm` 격자 테이블 | sourceEngine 배지 |
| MetricBlock | KPI 카드 + 전월대비/전년동월 델타 칩(참조HTML DNA) | 상승 초록·하락 파랑 |
| FlagBlock | severity 칩(warning ⚠ / opportunity ✦) | enrichedFlags.reference=학술출처 툴팁 |
| ChartBlock | `ChartRenderer` 디스패처(공유 SSOT) | **손수 차트 금지**. 인쇄 시 정적 SVG 스냅/표 대체 |
| threads | 섹션 좌측 색 바 + 제목 | severity 색 |
| EvidenceStrip | coverage 점 + evidenceIds 칩 | ★score 미렌더 |

## 5. 스타일

- `.dlTerm` 스코프, `--dl-*` 토큰, 11.5px, Pretendard, **Tailwind 금지**. lucide. 상승 초록(`#34d399`)/하락 파랑(`#f0616f`) 한국 관례.
- 버튼 = 기존 `Button.svelte`, 패널 = `Panel.svelte` 톤. SupportDialog/MacroLensDialog 구조 참조.

## 6. 인쇄 — zero-dep PDF (간판4)

- 단일 `@media print` 스타일시트: `.dlTerm` 다크 → 화이트 A4. `--dl-bg-base→#fff`, `--dl-ink→#1a1a1a`, 인쇄 채도↓(상승 `#c0392b`/하락 `#1f5fc0`).
- `.rptTabs/.topBar/.printBtn { display:none }`. `.rptSection { break-inside:avoid }`. `.rptDoc` 외 `display:none`.
- running footer: `@page { @bottom-center { content: "..." } }`(CSS `::after` 1회출력 한계 회피).
- ChartBlock: 인쇄 정적 SVG 사전 스냅 또는 표 대체(klinecharts 캔버스 빈출력 방지).
- **인쇄 acceptance = 정량 PASS 아님 → 푸시 전 스크린샷/실제 인쇄 미리보기 눈검수 수동 게이트**([[feedback_ui_rules]] 강행).

## 7. 무중단·push 게이트

- 공개 터미널 무중단: 미배선 커밋·로컬 프리뷰 격리·완결 단위만.
- UI(P2~P3) push = **운영자 명시 승인**. 그 전 commit 까지만 + "검사 대기" 한 줄. 스크린샷 전수 눈검수 후에만.
