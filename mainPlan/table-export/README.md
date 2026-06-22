# Table Export — 공시 테이블 엑셀 내보내기 PRD Index

상태: 비전 PRD v0.1 (2026-06-13 전문 에이전트 2종 — 성능·아키텍처 / 제품·정합 — 토론·적대검증 후 확정)
범위: 한 회사 공시(사업보고서 등)의 **모든 테이블**을 엑셀로 내보낸다. 미리보기에서 테이블을 보고 클릭해 내보내기 양식을 구성하고, 목차(TOC)를 시트 구조로 삼아 각 테이블을 시트로 낸다. 엔진(Python) → GitHub Pages(landing) → 로컬 터미널(ui/packages) 3 표면.

---

## 한 줄 결정

별도 "내보내기 화면"을 만들지 않는다. **뷰어 격자가 곧 미리보기**다 — 사용자는 이미 `PanelMatrix`에서 공시의 모든 테이블을 보고 있다. 우리가 더하는 것은 ① 그 위 셀렉션 레이어(기존 glow 메커니즘 재사용) ② 선택 바구니 드로어(AskDrawer 슬롯 공유) ③ 선택을 `ExcelTemplate`로 직렬화하는 경로뿐이다. 참조 외부 서비스의 "미리보기를 따로 띄운다"를 우리는 *이미 가진 뷰어가 미리보기*라는 더 강한 형태로 흡수한다. 그리고 우리 **panel(공시 수평화 격자)**을 레버로 외부 서비스가 원천 불가능한 2가지 — **다기간 시계열(horizontalized) 내보내기**·**회사 간 양식 이식** — 를 토글/버튼 각 1개로 얹어 차별화한다.

---

## 핵심 결정 요약 (v0.1)

- **재발명 금지 — 기존 자산 확장**: 엔진엔 이미 `exportWithTemplate(c, ExcelTemplate)` + `SheetSpec` + `TemplateStore`(~/.dartlab/templates, JSON CRUD) + `discoverSources()` + 서버 `/api/export/*` 전체 CRUD가 배선돼 있다. landing엔 `dataExport.ts`(`panelToCsv`/`financeToExcel`/`splitHtmlAndText`)와 `cell.ts`(`normalizeDartXml` — colspan/rowspan 보존) 가 있다. **신규 코드는 갭만 채운다.** → [01-engine-export.md](01-engine-export.md) §1.
- **갭 5종**: ① 템플릿 `source`가 "모듈명"(IS/dividend)일 뿐 "공시 테이블"(sectionKey/disclosureKey)을 표현 못 함 ② `<TABLE>`(colspan/rowspan)→2D 격자→병합셀 경로가 export writer에 미배선(엔진 `cellGrid` 존재하나 export는 깨끗한 DataFrame만 씀, 브라우저는 텍스트로 납작화) ③ 미리보기 클릭→양식 선택 UX 부재 ④ export용 런타임 계약 부재 ⑤ 브라우저 진짜 .xlsx 생성기 부재.
- **엔진 = 권위 산출물 (Phase 1)**: `exportWithTemplate`에 `PanelTableSource` 핸들러 추가 — `cellGrid`로 병합 보존 시트(openpyxl `merge_cells`). DART 대문자 XML용 `normalizeDartXml` Python 포팅 선결. → [01-engine-export.md](01-engine-export.md).
- **브라우저 = zero-dep 진짜 .xlsx (Phase 2)**: SpreadsheetML 2003 `.xls`(현대 Excel "확장자 불일치" 경고)·SheetJS(200KB 과잉) 둘 다 기각. **STORE(무압축) ZIP + CRC32 + 표준 `<mergeCell>` 로 OOXML `.xlsx`를 라이브러리 0으로 직접 생성**(~250줄 순수 TS). 3 표면 포맷이 .xlsx로 통일된다(엔진은 스타일링이 더 풍부할 뿐). → [02-browser-xlsx-and-parity.md](02-browser-xlsx-and-parity.md).
- **파싱 패리티**: raw `<TABLE>`→2D 격자(병합 정보 포함) 변환을 엔진(`cellGrid` 권위)·브라우저(`tableGrid.ts` 미러) 둘 다 한다. **공유 골든 픽스처**(`*.xml` + `*.grid.json`)를 양쪽 CI 게이트로 둬 발산을 빨강으로 잡는다. → [02-browser-xlsx-and-parity.md](02-browser-xlsx-and-parity.md) §3.
- **3-표면 계약**: 신 `ExportPort`(contracts) — `ServiceCommandResult`는 Blob을 못 싣는다. public 어댑터=브라우저 OOXML 생성, local 어댑터=`/api/export/excel` 프록시. 둘 다 동일 `ExcelTemplate` JSON 스키마(패리티). `ServiceGroup 'export'`(이미 존재)는 command palette 진입점으로만. → [03-surfaces-and-contract.md](03-surfaces-and-contract.md).
- **미리보기 선택 UX**: `PanelMatrix` 셀 체크박스 오버레이(`data-cell` 키·glow 재사용) + `PanelTocTree` 체크박스 → `ExportDrawer`(AskDrawer 슬롯, 상호배타) 선택 바구니(드래그 정렬·시트명 편집·모드 토글). → [04-preview-selection-ux.md](04-preview-selection-ux.md).
- **차별화 (panel 레버)**: (a) 테이블당 2모드 as-filed↔horizontalized **1순위** (b) 회사 간 양식 이식 **2순위** (c) 재무는 숫자 DataFrame·공시는 raw 구조 **자동 판정**(토글 없음) (d) provenance+honest-gap **기본 ON**. 덕지덕지 3종(3번째 모드·수식 주입·차트 삽입) 명시 기각. → [00-product-prd.md](00-product-prd.md) §3.

---

## 문서 지도

1. [00-product-prd.md](00-product-prd.md) — 제품 비전, 사용자 문제, 흡수한 개념, **차별화(더 좋은 개념)**, 범위·비범위, 사용자 흐름, 성공 기준, 개발자·PM 이중 평가.
2. [01-engine-export.md](01-engine-export.md) — 엔진(Python, Phase 1). 기존 자산, source 모델 확장(discriminated union), `cellGrid` 병합 보존 시트, `normalizeDartXml` 포팅, 정합 정규화, 일괄(batch) 내보내기·OOM 규율, CLI/서버.
3. [02-browser-xlsx-and-parity.md](02-browser-xlsx-and-parity.md) — 브라우저(landing, Phase 2). zero-dep OOXML .xlsx writer, 격자 파서, 정합 정규화, 엔진↔브라우저 패리티 골든 픽스처.
4. [03-surfaces-and-contract.md](03-surfaces-and-contract.md) — 3-표면. `ExportPort` 계약, public/local 어댑터, command palette, 템플릿 CRUD 표면차, 터미널 통합(뷰어 이관 의존), tier UX.
5. [04-preview-selection-ux.md](04-preview-selection-ux.md) — 미리보기 선택 인터랙션, selection 모델, ExportDrawer, TOC→시트 매핑, 시트명 규칙, 사용자 여정.
6. [05-validation-and-rollback.md](05-validation-and-rollback.md) — 테스트 매트릭스(패리티·정합·직렬화), 롤백, OOM 테스트 규율, 성능 리스크 톱3, 단계별 AC.
7. [06-progress-ledger.md](06-progress-ledger.md) — 현재 결정·문서 상태·워크스페이스 변동·NEXT 포인터(세션 재개용)·미결.

---

## 설계 원칙 (전 문서 관통)

- **추측 금지·원본 truth**: 단위(천원/백만원)는 임의 환산하지 않고 헤더 라벨로만. 모르는 단위·결손은 빈칸(0 대체 절대 금지 — `feedback_panel_wide_identity`, honest-gap).
- **계산 가능성이 충실도의 기준**: "예쁜 표"가 아니라 사용자가 엑셀에서 바로 `=SUM()` 할 수 있어야 한다. 숫자는 콤마 없는 Number 타입, 괄호·△ 음수 정규화, 병합셀 보존이 임계 3종.
- **표면별 역량 명시**: 공개(브라우저)는 로컬(엔진 권위 .xlsx)의 상위 스타일링을 *숨기지 않고* tier 라벨 + 설치 hint로 보인다(funnel). fallback·우회가 아니라 역량 차이를 있는 그대로 노출.
- **덕지덕지 금지**: 강함은 쌓아서가 아니라 깎아서. 모드는 2개, 수식·차트 자동삽입 없음. 추가 의심 시 안 붙인다(`feedback_always_check_clutter`).
- **본진 0줄까지**: 신규 정합 정규화 로직(숫자/음수/단위/격자)은 졸업 게이트 통과 전 `tests/_attempts/tableExport/`에서 개념확립. 단 기존 `viz/export/`·`dataExport.ts` 확장은 검증된 본진의 점진 보강이라 _attempts 우회.

---

## 의존성·착수 조건

- **Phase 1(엔진)은 독립**: UI 플랫폼 리팩토링·뷰어 이관과 무관하게 착수 가능. 운영자 go 시 바로.
- **Phase 2(브라우저)는 현 landing 뷰어에 바로 배선** 가능(뷰어가 아직 landing에 있음).
- **Phase 3(터미널)은 뷰어 `landing→ui/packages/surfaces` 이관에 편승** — `project_ui_platform_refactor`(운영자 go 대기)의 후행. 단 공유 모듈(격자 파서·xlsx writer·selection 모델·ExportPort)을 표면 이식 가능하게 작성하므로, 이관이 export를 그대로 실어 나른다.
