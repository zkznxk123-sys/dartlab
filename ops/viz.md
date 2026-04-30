## Appendix. Visual Explanation Engine

`dartlab.viz` 는 차트를 그리는 보조 기능이 아니라 시각적 설명 엔진이다. Financial Workspace Agent 는 숫자 변화·비교·랭킹은 chart 로 설명하고, 인과·사업구조·재무흐름은 diagram 으로 설명한다.

1차 공식 visual type 은 `chart` 와 `diagram` 이다. Workspace agent 는 계산표에서 만든 visual spec 만 `chart` event 와 Workspace Visual Ledger 로 승격한다. legacy 실행 경로의 `emit_chart()` / `emit_diagram()` stdout marker 는 호환으로 유지한다.

AI 응답에서 visual 은 장식이 아니다. visual 필요 여부는 Intelligence Map 이 노출하는 generated `Process Map.requiredVisuals` 와 workspace 질문 유형이 정하고, 각 visual spec 은 계산표나 observation 에서 컴파일되어야 한다. 질문 유형별 목적은 분명해야 한다: 시계열은 변화, 비교는 차이, 랭킹은 순위, 다이어그램은 인과·구조를 설명한다. evidence 와 연결되지 않은 visual 은 만들지 않는다.

차트는 최소한의 해석 가능한 축을 가져야 한다. `bar`/`line`/`combo`/`pie`/`waterfall` 은 서로 다른 category 2개 이상과 숫자값 2개 이상이 없으면 visual 로 승격하지 않는다. 단일 `summary` 막대, 단일 종목 현재값 막대, evidence 축을 설명하지 못하는 spec 은 runtime 과 UI 양쪽에서 버린다. 단일 값은 차트가 아니라 표·문장·limit 로 설명한다.

visual 의미 판정의 SSOT 는 runtime 과 UI 의 공유 contract 다. Python 쪽은 workspace visual contract 가 `isMeaningfulVisualSpec` 과 CSV 기반 auto visual compiler 를 제공하고, web/VSCode 는 `ui/shared/api/visualContract.ts` 를 사용한다. 같은 규칙을 각 surface 에 다시 복붙하지 않는다.

visual 생성 여부는 수동 체크리스트가 아니다. docstring/capabilities 의 visual 계약이 Analysis Graph 와 Process Map 으로 컴파일되고, runtime 이 질문 유형과 Workspace evidence 를 보고 자동으로 `chart` 또는 `diagram` 후보를 만든다. 사람이 손으로 관리하는 것은 visual 계약과 VizSpec 프로토콜뿐이다.

랭킹·시계열·비교 질문은 primary evidence 와 visual 이 함께 있어야 한다. 예: KRX 급등주 질문은 `run_python` 계산 결과에서 ranking evidence 20개와 primary CSV artifact 를 만들고, 같은 evidenceIds 에 연결된 chart visual 을 만든다. CSV/visual 은 부가 장식이 아니라 UI 와 사용자가 같은 계산 결과를 재사용하게 하는 Result Bundle 의 일부다.

Remotion/영상형 설명은 다음 단계다. 현재 구현 계약은 chart/diagram spec 까지이며, 영상형 visual 도 같은 원칙을 따른다: 장식이 아니라 판단 근거를 사용자가 더 빨리 이해하게 하는 설명 도구다.

**반복 실패** → visual 을 “보기 좋은 차트”로만 취급하거나 evidence 와 연결하지 않는 것. visual spec 은 근거와 연결되어야 하며, 연결되지 않은 visual 은 품질 게이트에서 `unsupported_visual` 로 본다.

---

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
| `src/dartlab/viz/extract.py` | legacy stdout 마커 추출 |
| `src/dartlab/viz/generators.py` | Company → ChartSpec 8 종 |
| `src/dartlab/viz/charts/` | DataFrame → Plotly Figure (line · bar · pie · waterfall · revenue · …) |
| `src/dartlab/story/blocks.py` | ChartBlock 타입 |
| `src/dartlab/ai/runtime/workspace_visual.py` | workspace agent visual 의미 판정 + CSV 기반 visual compiler |
| `ui/shared/api/visualContract.ts` | web · VSCode 공통 visual 의미 판정 |
| `ui/shared/chart/` | Svelte SVG 차트 컴포넌트 (web · vscode 공유) |

---

## 요약 — 명제 6 줄

1. `emit_chart` · `emit_diagram` 두 헬퍼로 시각화를 시작한다.
2. VizSpec 프로토콜 (`chartType`/`title`/`series`/`categories`/`options`/`meta`) + diagram 분기.
3. AI 는 stdout 마커로 전달 — `emit_*` → `extract_viz_specs` → CHART 이벤트 → SSE → 클라이언트.
4. Company → ChartSpec 자동 생성기 8 종 (revenue · cashflow · BS · profitability · dividend · radar · sparkline · heatmap).
5. 렌더링은 VSCode · Web SPA · Jupyter · Story (터미널·HTML·JSON) 6 경로.
6. 팔레트는 Python `viz/palette.py` + JS `ui/shared/chart/colors.ts` 한 값으로 동기화.
