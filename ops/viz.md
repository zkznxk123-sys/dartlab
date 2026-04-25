# Viz

**주체**: viz 패키지 (`dartlab.viz` — `emit_chart` · `emit_diagram`).
**현재**: 교차 관심사 — 모든 레이어에서 import 허용 · stdout marker (`<!--DARTLAB_VIZ:-->`) · webview·extension 파싱.
**방향**: 차트 타입 확대 · 다이어그램 템플릿 통일 · viz → dashboard 직결.

통합 시각화 엔진. 차트·다이어그램을 하나의 패키지에서 관리한다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 — `emit_chart` · `emit_diagram` 하나로 시작한다

```python
from dartlab.viz import emit_chart, emit_diagram

emit_chart({
    "chartType": "line",
    "title": "삼성전자 매출",
    "categories": ["2022", "2023", "2024"],
    "series": [{"name": "매출", "data": [302.2, 258.9, 300.9]}],
})
emit_diagram("mermaid", "graph LR\n  매출-->영업이익-->FCF")
```

viz 는 헬퍼 엔진. 별도 노트북 없이 다른 분석 노트북 내에서 `emit_chart` 호출.

| 항목 | 내용 |
|---|---|
| 레이어 | 교차 관심사 (guide/ 와 동일 위치) |
| 진입점 | `dartlab.viz` · `emit_chart()` · `emit_diagram()` |
| 소비 | Company (finance · docs), analysis (insight), AI runtime |
| 생산 | story (ChartBlock), AI (CHART 이벤트), Jupyter (Plotly Figure) |
| 프로토콜 | VizSpec (ChartSpec JSON 100% 하위호환) |

---

## 2. VizSpec 프로토콜 — 이 구조로 넘긴다

기존 ChartSpec JSON 과 동일. `vizType` 필드로 chart·diagram 분기.

```json
{
    "chartType": "combo|bar|line|radar|waterfall|heatmap|sparkline|pie",
    "title": "str",
    "series": [{"name": "str", "data": [number], "color": "str", "type": "bar|line"}],
    "categories": ["str"],
    "options": {"unit": "str", "stacked": bool},
    "meta": {"source": "str", "stockCode": "str", "corpName": "str"}
}
```

diagram 일 때: `{"vizType": "diagram", "diagramType": "mermaid", "source": "...", "title": "..."}`.

---

## 3. AI → 차트 파이프라인 — stdout 마커로 전달한다

```
AI 코드 실행 → emit_chart() → stdout 마커 → extract_viz_specs() → CHART 이벤트 → SSE → 클라이언트
```

- `emit_chart(spec)` — ChartSpec dict 를 stdout 마커로 출력.
- `emit_diagram(type, source)` — 다이어그램 소스를 stdout 마커로 출력.
- `extract_viz_specs(stdout)` — 마커 추출 + 텍스트 정제.
- `AnalysisEvent("chart", {"charts": [spec]})` — SSE 로 전달.

**반복 실패** — stdout 에 섞이는 다른 출력과 구분하려면 `<!--DARTLAB_VIZ:-->` 마커 누락 없이 `emit_*` 헬퍼만 사용한다. dict 를 직접 `print` 하면 파싱 실패.

---

## 4. Company → ChartSpec 자동 생성기 8 종

| 함수 | chartType | 소스 |
|---|---|---|
| `spec_revenue_trend` | combo | IS annual |
| `spec_cashflow_waterfall` | waterfall | CF annual |
| `spec_balance_sheet` | bar (stacked) | BS annual |
| `spec_profitability` | line | ratioSeries |
| `spec_dividend` | combo | report.dividend |
| `spec_insight_radar` | radar | insights |
| `spec_ratio_sparklines` | sparkline | ratioSeries |
| `spec_diff_heatmap` | heatmap | diff() |

---

## 5. 렌더링 대상 — 6 경로로 낸다

| 대상 | 방식 |
|---|---|
| **VSCode Extension** | SSE chart 이벤트 → Svelte ChartRenderer (SVG) |
| **Web UI (SPA)** | SSE chart 이벤트 → Svelte ChartRenderer (SVG) |
| **Jupyter · Marimo** | `VizSpec.toPlotly()` → Plotly Figure |
| **Story (터미널)** | `[chart: title]` 플레이스홀더 |
| **Story (HTML)** | `<div class="dl-chart" data-spec='...'/>` |
| **Story (JSON)** | spec dict 그대로 |

---

## 6. 컬러 팔레트 — Python·JS 같은 값으로 동기화한다

8 색. Python `viz/palette.py` + JS `ui/shared/chart/colors.ts` 동일 값 유지.

**반복 실패** — Python·JS 팔레트 한쪽만 수정 → 차트 색 불일치.

---

## 7. 관련 코드

| 경로 | 역할 |
|---|---|
| `src/dartlab/viz/__init__.py` | 공개 API (`emit_chart` · `emit_diagram` · `VizSpec` · `COLORS` · `auto_chart` · …) |
| `src/dartlab/viz/spec.py` | VizSpec dataclass |
| `src/dartlab/viz/palette.py` | COLORS 단일 원천 |
| `src/dartlab/viz/plotly.py` | ChartSpec → Plotly Figure 변환 |
| `src/dartlab/viz/extract.py` | AI stdout 마커 추출 |
| `src/dartlab/viz/generators.py` | Company → ChartSpec 8 종 |
| `src/dartlab/viz/charts/` | DataFrame → Plotly Figure (line · bar · pie · waterfall · revenue · …) |
| `src/dartlab/story/blocks.py` | ChartBlock 타입 |
| `ui/shared/chart/` | Svelte SVG 차트 컴포넌트 (source of truth, web · vscode 공유) |

---

## 요약 — 명제 6 줄

1. `emit_chart` · `emit_diagram` 두 헬퍼로 시각화를 시작한다.
2. VizSpec 프로토콜 (`chartType`/`title`/`series`/`categories`/`options`/`meta`) + diagram 분기.
3. AI 는 stdout 마커로 전달 — `emit_*` → `extract_viz_specs` → CHART 이벤트 → SSE → 클라이언트.
4. Company → ChartSpec 자동 생성기 8 종 (revenue · cashflow · BS · profitability · dividend · radar · sparkline · heatmap).
5. 렌더링은 VSCode · Web SPA · Jupyter · Story (터미널·HTML·JSON) 6 경로.
6. 팔레트는 Python `viz/palette.py` + JS `ui/shared/chart/colors.ts` 한 값으로 동기화.
