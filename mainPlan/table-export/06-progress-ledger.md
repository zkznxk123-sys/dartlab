# 06. Progress Ledger — 결정·상태·NEXT

상태: v0.1 (2026-06-13 작성)
용도: 끊긴 세션이 NEXT 포인터만 읽고 재개. 내용 복제 금지 — 결정·상태·열린 질문만.

---

## 1. 확정 결정 (전문 토론 판정 후)

| 크럭스 | 결정 | 기각 |
|---|---|---|
| 브라우저 포맷 | zero-dep 진짜 OOXML `.xlsx`(STORE zip+CRC32+`<mergeCell>`) | .xls SpreadsheetML(경고)·SheetJS(200KB 과잉) |
| source 모델 | discriminated union `ModuleSource\|PanelTableSource` + str 하위호환 | `panel:` prefix 문자열 |
| 파싱 패리티 | 엔진 `cellGrid` 권위 + 브라우저 `tableGrid` 미러 + 공유 골든 픽스처 | 엔진→브라우저 전달(공개 서버0 불가) |
| 3-표면 계약 | 신 `ExportPort`(contracts) | ServicesPort 단독(Blob 못 실음) |
| 미리보기 데이터 | 이미 로드된 `PanelBundle`에서 순수 함수 추출 | 별도 API call |
| 선택 UX | 별도 모드 0, 뷰어 격자=미리보기 + 셀/TOC 체크박스(glow 재사용) + ExportDrawer(AskDrawer 슬롯) | 화면 전환 모드 |
| 차별화 | 2모드(as-filed↔horizontalized)·회사이식·자동 재무/공시 판정·provenance | 3번째 모드·수식·차트·수동 raw/clean |

## 2. 코드 실측으로 확인된 load-bearing 사실

- 엔진 `providers/dart/parse/htmlTableParser.py::cellGrid`(177) — rowspan/colspan 직사각 격자 전개, 병합셀 동일 인스턴스 공유. **이미 존재, export에 미배선.** 입력은 소문자 HTML(DART 대문자 정규화 선결).
- 엔진 `panel/text.py::panelXmlTables`/`panelTableRows` — **병합 버림**(itertext). export 격자 경로 사용 금지.
- 브라우저 `landing/src/lib/viewer/cell.ts` — `normalizeDartXml`(대문자→표준, colspan/rowspan/align 보존, 43줄), `SANITIZE_CONFIG.ALLOWED_ATTR`에 colspan/rowspan(62줄), `splitHtmlAndText`(raw table 무손실, 66줄), `absorbCaptionUnitFromText`(단위 흡수, 91줄). **병합 정보 브라우저까지 생존, 격자 전개기만 신규.**
- 엔진 `viz/export/{excel,template,store,sources}.py` — `exportWithTemplate`·`SheetSpec`·`ExcelTemplate`(toJson/fromJson)·`TemplateStore`(~/.dartlab/templates)·`discoverSources`. 서버 `data.py` `/api/export/*` CRUD 전부 배선. `SheetSpec.source`만 모듈명 문자열 한계.
- landing 브라우저 deps: hyparquet·dompurify, **xlsx/jszip 없음**. `dataExport.ts::financeToExcel`은 .xls SpreadsheetML 수작업.
- 공용 `ui/packages/contracts/src/services.ts` — `ServiceGroup`에 `'export'` 이미 존재, `ServiceCommandResult`는 status/toast/panel/ask만(Blob 불가).

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README | ✅ v0.1 |
| 00-product-prd | ✅ v0.1 |
| 01-engine-export | ✅ v0.1 |
| 02-browser-xlsx-and-parity | ✅ v0.1 |
| 03-surfaces-and-contract | ✅ v0.1 |
| 04-preview-selection-ux | ✅ v0.1 |
| 05-validation-and-rollback | ✅ v0.1 |
| 06-progress-ledger | ✅ v0.1 (본 문서) |

## 4. 워크스페이스 변동

- 신규 폴더 `mainPlan/table-export/`(8 문서). 코드 변경 0(PRD만).

## 5. NEXT

✅ **Phase 1 착수 전 개념검증 — 완료(2026-06-14)**: `tests/_attempts/tableExport/`(gitignore 스크래치)에서 삼성 005930 실데이터로 `normalizeDartXml`→`cellGrid`→`coerceCell` 파이프라인 입증. 병합 보존(rowspan=683 극단 케이스도 단일 인스턴스), 3 정합 임계(숫자/괄호·△음수/단위 캡션) 실셀 확인, 9 엣지케이스 카탈로그. 골든 픽스처 3종 `*.xml`+`*.grid.json` → `tests/fixtures/xmlTables/` 승격(엔진↔브라우저 패리티 SSOT).

✅ **Phase 1 엔진 — 완료(2026-06-14)**: 
  - `providers/dart/parse/dartXmlNormalize.py`(신규, 9섹션 docstring) = normalizeDartXml/coerceCell/detectUnit 본진 승격.
  - `viz/export/template.py` = `ModuleSource|PanelTableSource` source union + 하위호환 정규화(str→ModuleSource·dict→kind 분기). **PRESETS 3종·저장템플릿 무변경 round-trip 검증**. ★PanelTableSource 필드는 실 panel(`readWide`)로 그라운딩 정정 — `disclosureKey` 선택(87% None), `leafSeq` 추가(7-tuple 0충돌 유일선택).
  - `viz/export/excel.py` = `_writePanelTableSheet`/`_writeGridSheet`(cellGrid 병합→openpyxl merge_cells, id() dedup 극단 rowspan 단일범위, coerceCell 값·honest-gap 빈셀→None)/`_writeHorizontalizedSheet`(일반표 as-filed 폴백+노트). ModuleSource 경로 회귀 0.
  - `server/api/data.py` = `POST /api/export/excel`(selection→임시 양식→.xlsx) + `/batch`(회사당 순차·`del c`·디스크 ZIP·≤50·to_thread 직렬화, OOM 규율).
  - 검증: 38 유닛(격자 패리티·source round-trip) + 1 realData + 12 htmlTableParser 회귀 PASS(test-lock), 실회사 export(merge 9범위·음수 13·Number) 입증, 독립 재검증 통과. AC(05 §1) 충족.

다음:
3. **Phase 2 — 공개 브라우저**: zero-dep OOXML writer(`xlsx/{zipStore,workbook,tableGrid,tableExtract,buildWorkbook}`) + ExportDrawer + selection. ⚠ viewer 가 `ui/packages/surfaces/src/viewer/` 로 이관됨 — PRD의 `landing/src/lib/viewer/xlsx/` 경로 stale, 신 거처로 재그라운딩. 같은 골든 픽스처로 엔진↔브라우저 패리티.
4. **Phase 3 — 터미널**: `ExportPort`(contracts) + public/local 어댑터 + command palette.

## 6. 열린 질문 (deferred, 착수 시 판단)

- 한 섹션 다중 block "한 시트로 합치기"를 v0.1에 넣을지(드로어 드래그 겹침) — 기본 1:1로 출시 후 수요 보고 결정.
- horizontalized 일반 공시 표 라벨 정렬 휴리스틱의 폴백 임계 — 실측 후 결정(보수적으로 as-filed 폴백 우선).
- EDGAR(US) 동일 경로 검증 — DART 안착 후.
- AI `viewerActions` `{kind:'exportSelection'}` 자연어 경로 — 계약은 받게 두되 구현 후속.
- 공개 일괄 회사이식 LRU 8개 초과 시 정확한 안내 카피 — UX 카피 단계.
