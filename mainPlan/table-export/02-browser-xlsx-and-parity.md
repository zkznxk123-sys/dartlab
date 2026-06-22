# 02. Browser XLSX & Parity — 공개면 zero-dep .xlsx + 엔진 패리티 (Phase 2)

상태: v0.1
범위: GitHub Pages(landing, 서버 0)에서 병합셀을 가진 진짜 .xlsx를 라이브러리 0으로 생성. 엔진과의 격자 파서·정합 패리티.

---

## 1. 결정 — zero-dep 진짜 OOXML `.xlsx` 직접 생성

GitHub Pages는 정적 사이트(서버 0). 후보 3종을 정량 비교한 끝에 **STORE(무압축) ZIP + CRC32 + 표준 `<mergeCell>` 로 OOXML `.xlsx`를 라이브러리 0으로 직접 생성**한다(~250줄 순수 TS).

| 후보 | 판정 | 근거 |
|---|---|---|
| **(채택) zero-dep OOXML .xlsx** | **채택** | `.xlsx` = ZIP 컨테이너 + 정적 XML 몇 개. 병합 = 시트 XML `<mergeCells><mergeCell ref="A1:C1"/></mergeCells>` (표준, 모든 Excel/Sheets/Numbers가 **경고 없이** 엶). STORE 메서드로 ZIP 쓰면 압축 라이브러리도 0(CRC32만 ~20줄). 추가 번들 ≈ 0. 동적 import 지연 0. **3 표면 포맷이 .xlsx로 통일**(엔진은 스타일링만 더 풍부). |
| (기각) SpreadsheetML 2003 `.xls` | 기각 | MergeAcross/MergeDown로 병합은 되나, 현대 Excel이 `.xls` 확장자 + XML 본문에 **"파일 형식과 확장자 불일치" 경고**를 띄움(레거시 Office 포맷). 일반인 공개 기능에서 매 다운로드 경고는 결함. macOS Numbers·Sheets import 병합 누락 사례. 기존 `financeToExcel`가 이미 이 경고를 유발 — **확장이 아니라 교체** 사유. |
| (기각) SheetJS/exceljs 동적 import | 기각 | min+gz 180~270KB. **결정적 기각은 크기가 아니라 중복** — 우리 출력은 쓰기 전용·좁다(셀 텍스트 + colspan/rowspan + 시트 분할). 수식·차트·읽기 파서 전부 불필요. 200KB 라이브러리를 병합 2개 API 위해 들이는 건 `feedback_always_check_clutter` 위반. |

> 구현 범위: `.xlsx`=ZIP+XML, STORE 메서드, `<mergeCell>`, CRC32는 모두 공개 표준이라 구현 위험이 낮다. 단 ZIP 로컬 헤더·중앙 디렉토리·EOCD·CRC32·크기 필드의 정확한 바이트 레이아웃은 한 번에 맞춰야 하므로 골든 픽스처 + 실제 Excel/Sheets 라운드트립 검증을 게이트로 둔다(05). LOC ~250·STORE 크기는 추정.

---

## 2. 브라우저 writer 아키텍처

신규 모듈 `landing/src/lib/viewer/xlsx/`:

- **`zipStore.ts`** — STORE(method 0) ZIP 작성기. local file header + central directory + EOCD. `crc32(bytes)` 테이블 구현. `addEntry(name, bytes)` → `finalize()→Uint8Array`.
- **`workbook.ts`** — OOXML 부품 emit:
  - `[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/_rels/workbook.xml.rels`, `xl/styles.xml`(최소: 헤더 볼드·`#,##0`·`#,##0;[Red]-#,##0`·`@`text·`wrapText`), `xl/sharedStrings.xml`(또는 inlineStr), 시트별 `xl/worksheets/sheetN.xml`.
  - 시트 XML: `<sheetData>` row/cell + `<mergeCells>`. 셀 타입 = `n`(number)/`inlineStr`(text). number는 콤마 없는 raw 값 + styleId로 `#,##0` 서식.
- **`tableGrid.ts`** — `cellGrid`(엔진) 알고리즘의 TS 포팅(§3).
- **`tableExtract.ts`** — raw `<table>` HTML → 정합 정규화된 2D 셀(숫자/음수/단위, 01 §5 공유 규칙).
- **`buildWorkbook.ts`** — selection + PanelBundle → 워크북 부품. TOC→시트 매핑(04 §4) 적용.

기존 `dataExport.ts`의 `financeToExcel`(.xls SpreadsheetML)은 deprecate → 신 .xlsx writer로 재배선. `panelToCsv`(CSV)는 유지(가벼운 대안). `downloadText`는 `downloadBlob(Uint8Array, name, mime)`로 확장(현재 string Blob).

브라우저는 회사 진입 시 `buildPanelBundle`로 `gridBySection`·`toc`를 **이미 메모리 보유** → 테이블 추출은 추가 fetch 0(순수 함수). 셀 raw XML은 `normalizeDartXml`(cell.ts, 이미 존재) → `splitHtmlAndText`(이미 존재) → `tableGrid`(신규) → 정규화 → OOXML.

---

## 3. 격자 파싱 패리티 (엔진 ↔ 브라우저)

두 표면은 **입력이 분리**돼 있다 — 엔진은 panel `contentRaw`를 Python에서, 브라우저는 같은 `contentRaw`를 hyparquet으로 직접 읽는다(파생 artifact 0). 공개면(서버 0)은 Python을 못 부르므로 "엔진이 격자 만들어 전달"이 **불가능**하다. 따라서 브라우저는 자체 격자기가 **반드시** 있어야 하고, 패리티는 *공유 명세 + 양쪽 독립 구현 + 동일 입출력 픽스처 강제*로 보장한다.

확인된 사실(코드 실측):
- 엔진 `cellGrid`(htmlTableParser.py:177) — rowspan carry + colspan 펼침으로 직사각 격자, 병합셀=동일 인스턴스 공유. **권위 구현.**
- 브라우저 `normalizeDartXml`(cell.ts:34) — DART 대문자→표준 태그, **colspan/rowspan/align 보존**(line 43). `SANITIZE_CONFIG.ALLOWED_ATTR`에 colspan/rowspan 포함(line 62). `splitHtmlAndText`(line 66)는 `<table>` raw 블록 무손실 추출. → **병합 정보가 브라우저까지 살아있다.** 격자 전개기만 신규.

패리티 메커니즘(정공법):
1. **공유 골든 픽스처** — `tests/fixtures/xmlTables/*.xml`(DART 대문자 원본) + 기대 `*.grid.json`(2D 셀 + 병합 범위 + 정규화 값). 병합 케이스 망라: 단순 colspan 헤더, rowspan 항목, colspan+rowspan 중첩, 불규칙 행(셀 부족), multi-row header, 괄호/△ 음수, "(단위:백만원)" 흡수.
2. **엔진 테스트**(`tests/parse/test_htmlTableParser.py` 확장): 픽스처 → `normalizeDartXml`(Python 포팅) → `cellGrid` → `_coerceCell` → `.grid.json` 일치.
3. **브라우저 테스트**(landing vitest): 동일 픽스처 → `normalizeDartXml`(cell.ts) → `tableGrid` → `tableExtract` 정규화 → 동일 `.grid.json` 일치.
4. 양쪽이 **같은 JSON 파일** 기준 → 알고리즘 발산 시 즉시 빨강.

추가 패리티: 같은 `ExcelTemplate` JSON으로 public(브라우저 OOXML)·local(엔진 openpyxl)이 **동일 시트 구조** .xlsx를 내야 한다. 픽스처 회사 1개로 양 경로 산출물의 시트명·시트수·셀값·`<mergeCell>`을 비교(브라우저 XML 직접 파싱, 엔진 openpyxl read). **셀 스타일은 패리티 제외**(엔진 스타일링 vs 브라우저 최소 — 값·구조·병합만 강제).

---

## 4. 정합 정규화 (01 §5와 동일 명세)

브라우저 `tableExtract.ts`는 엔진 `_coerceCell`과 같은 규칙:
- 숫자 `/^-?[\d,]+(\.\d+)?$/` → 콤마 제거 Number(`t="n"`), `#,##0` styleId.
- `(1,234)`/`△`/`▲` 음수 정규화.
- 단위 `absorbCaptionUnitFromText`(cell.ts, 이미 존재) → 시트 상단 라벨. 값 환산 금지.
- 병합 colspan/rowspan → `<mergeCell ref>`(앵커에만 값).
- 결손 빈 셀(0 금지). 텍스트 `<br>`→`\n`(`wrapText`).

브라우저 `.xls`(SpreadsheetML)의 충실도 격차(병합 약함·Number 미흡)가 이번 결정으로 **해소**된다 — .xlsx는 병합·Number·서식이 표준.

---

## 5. 영향 파일 / 함수

신규(landing):
- `landing/src/lib/viewer/xlsx/zipStore.ts`·`workbook.ts`·`tableGrid.ts`·`tableExtract.ts`·`buildWorkbook.ts`.

수정(landing):
- `dataExport.ts` — `financeToExcel`(.xls) deprecate → 신 .xlsx 재배선. `downloadText`→`downloadBlob` 확장. `panelToCsv` 유지.
- (소비 — 04) `ViewerStudio.svelte`의 기존 `downloadFinanceExcel()` 버튼이 신 writer 사용.

신규(테스트):
- `tests/fixtures/xmlTables/*.xml` + `*.grid.json`(엔진·브라우저 공유).
- 엔진 `tests/parse/test_htmlTableParser.py` 확장(정규화+격자 패리티).
- landing vitest — `tableGrid`/`tableExtract` 픽스처 패리티 + zip 바이트 유효성(실제 unzip 가능) + Number/mergeCell 산출.

---

## 6. 성능 (단일 회사)

한 공시 모든 테이블 ≈ 수십~수백 개, 텍스트 합계 수백KB~수MB. `gridBySection`은 이미 메모리 → 격자 전개 + XML emit은 동기 수십ms. web-llm 같은 GPU 잼과 무관(순수 문자열). **스트리밍·워커 불필요**. 100+ 테이블 동시 전개가 메인 스레드를 점유하면 시트 단위 yield 루프(`requestIdleCallback`)로 분할 — 단 선제 Web Worker는 측정 전 금지(`feedback_always_check_clutter`). STORE ZIP은 무압축이라 파일이 다소 크나(텍스트 수MB) 다운로드엔 실용적.
