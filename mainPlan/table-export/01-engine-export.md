# 01. Engine Export — 엔진(Python) 권위 산출물 (Phase 1)

상태: v0.1
범위: `src/dartlab/viz/export/` 확장 — source 모델, 병합 보존 시트, DART XML 정규화, 정합 정규화, 일괄 내보내기, CLI/서버. 엔진은 **권위 .xlsx 생산자**이며 UI 의존이 없어 **독립 착수** 가능.

---

## 1. 기존 자산 (재발명 금지 — 이걸 확장한다)

| 파일 | 보유 | 한계(갭) |
|---|---|---|
| `viz/export/excel.py` | `exportToExcel(c, outputPath, modules)`·`exportWithTemplate(c, template, outputPath)`·`listAvailableModules(c)`. openpyxl styled .xlsx, 헤더 fill·`_NEGATIVE_FMT`·`_autoWidth`·`freeze_panes`. | `_writeDataFrameSheet`는 **깨끗한 pl.DataFrame만** 시트로 씀. raw `<TABLE>` 병합 구조를 못 씀. |
| `viz/export/template.py` | `@dataclass SheetSpec(source:str, label, columns, years, sortBy, maxRows)` + `ExcelTemplate(name, sheets, ...)` (toJson/fromJson/addSheet/removeSheet/moveSheet) + `PRESETS{full,summary,governance}`. | `source`가 모듈명 문자열("IS"/"dividend")일 뿐 **공시 테이블 식별자 표현 불가**. |
| `viz/export/store.py` | `TemplateStore` — `~/.dartlab/templates/{id}.json` CRUD, `preset_` 불변, path-traversal 가드. | `fromDict/toJson`만 호출 → 스키마 확장 시 **코드 변경 0**. |
| `viz/export/sources.py` | `discoverSources(c)→SourceTree`(finance/report/disclosure/notes/analysis/raw), `SourceItem`. 소비처: excel·서버 API·UI 패널·LLM tool. | 모듈 단위 디스커버리. 공시 테이블(panel row) 디스커버리는 없음 → §6. |
| `providers/dart/parse/htmlTableParser.py` | **`cellGrid(html)→list[list[HtmlTableCell]]`** — rowspan/colspan을 직사각 격자로 전개, 병합셀=동일 인스턴스 공유. `HtmlTableCell{text,colspan,rowspan,align,valign,isHeader}`. `parseHtmlTable`·`extractItemValuePairs`. | 입력이 **소문자 표준 HTML** 전제. DART raw는 대문자(`<TABLE><TE><TU>`) → §3 정규화 선결. |
| `providers/dart/panel/text.py` | `panelXmlTables`·`panelTableRows` (XML 테이블 추출). | **병합 정보를 버린다**(`"".join(cell.itertext())`). export 격자 경로에서 **호출 금지**. |
| `server/api/data.py` | `/api/export/{modules,sources,templates[CRUD],excel}` 전부 배선. `exportWithTemplate`·`TemplateStore` 호출. | 신 source union을 `fromDict`로 흡수(변경 최소). 일괄 엔드포인트 없음 → §5. |

핵심: **병합 보존 격자기(`cellGrid`)는 이미 있다.** export writer에 배선되지 않았을 뿐이다.

---

## 2. source 모델 확장 — discriminated union

`SheetSpec.source: str`(모듈명)을 공시 테이블도 표현하도록 확장한다. 타입세이프 union을 채택한다(`panel:` prefix 문자열 인코딩은 파싱 취약·확장 불가라 기각 — `feedback_clean_module_tree`).

```python
# template.py (제안)
from typing import Literal, Union

@dataclass
class ModuleSource:
    kind: Literal["module"]
    name: str                      # "IS"/"BS"/"CF"/"ratios"/"dividend"/...

@dataclass
class PanelTableSource:
    kind: Literal["panelTable"]
    sectionKey: str                # gridBySection 키 = "chapter␟sectionLeaf"
    blockLeaf: str                 # 테이블 식별 (PanelRow.blockLeaf)
    disclosureKey: str | None      # 회사 간 이식 키 (필수 권장)
    scope: str | None              # "consolidated"/"separate"/None
    periodMode: Literal["asFiled", "horizontalized"]
    period: str | None = None      # asFiled면 단일 기간; horizontalized면 None(전 기간)

SheetSource = Union[ModuleSource, PanelTableSource]
```

`SheetSpec`은 `source: SheetSource`로 바꾸되, **하위호환 정규화**를 둔다:

```python
# SheetSpec.__post_init__ / fromDict 규칙
# - source 가 str  →  ModuleSource(kind="module", name=source)   (기존 템플릿·PRESETS 무변경 통과)
# - source 가 dict →  kind 로 분기 (ModuleSource | PanelTableSource)
# 직렬화는 항상 신 dict 형식으로 write. PRESETS 정의는 문자열 source 유지 가능(정규화가 흡수).
```

영향:
- `store.py` — `fromDict/toJson`만 호출하므로 **CRUD 코드 변경 0**.
- `server/api/data.py::apiExportTemplateSave` — `ExcelTemplate.fromDict(req)` 그대로. 신 dict source 통과.
- `exportWithTemplate` — source 분기 확장(§4).
- 저장돼 있는 기존 사용자 템플릿(JSON에 `"source":"IS"`)·3개 PRESET 전부 무변경 로드.

---

## 3. 선결 — `normalizeDartXml` Python 포팅

`cellGrid`는 소문자 HTML 전제인데 panel `contentRaw`는 DART 대문자 XML(`<TABLE><TR><TE>`, `<TU>`=헤더). 브라우저엔 `landing/src/lib/viewer/cell.ts::normalizeDartXml`(대문자→표준 태그 맵 + colspan/rowspan/align 보존)이 이미 있다. **이 함수의 Python 포팅**을 `providers/dart/parse/`에 신설한다(또는 `cellGrid` 진입부가 DART 태그 맵을 인식하도록 확장).

- 태그 맵: `TABLE→table, THEAD→thead, TBODY→tbody, TR→tr, TH/TU→th, TE/TD→td, BR→br` (cell.ts `DART_TAG_MAP` 동일).
- 보존 속성: `colspan/rowspan/align`.
- 제거: ACODE/ACONTEXT 등 정부 메타.
- **이 정규화는 브라우저 cell.ts와 1:1 패리티** — 같은 골든 픽스처(`*.xml`)로 양쪽 검증(02 §3).

`panelXmlTables`/`panelTableRows`(병합 버리는 경로)는 export 격자 경로에서 호출하지 않는다. 기존 텍스트 소비처(finance pipeline 등)는 유지(회귀 0).

---

## 4. 병합 보존 시트 writer

`exportWithTemplate`의 source 분기에 `PanelTableSource` 핸들러를 추가한다.

```python
# excel.py (제안)
def _writePanelTableSheet(wb, spec: PanelTableSource, c: Company, *, label: str):
    rows = c.panel  # wide pl.DataFrame, 또는 c.panel(sectionLeaf) 조회
    row = _selectPanelRow(rows, spec)          # sectionKey/blockLeaf/scope 로 행 1개
    if spec.periodMode == "asFiled":
        rawXml = row[spec.period]              # 단일 기간 contentRaw
        grid = cellGrid(normalizeDartXml(rawXml))   # §3
        _writeGridSheet(wb, label, grid)       # openpyxl + merge_cells
    else:  # horizontalized
        _writeHorizontalizedSheet(wb, label, row, periods)   # 항목×기간
```

`_writeGridSheet` 규칙(정합 — §5 공유):
- `grid[r][c]` 가 병합셀이면(동일 인스턴스가 인접 좌표 공유) **앵커 좌표에만 값 쓰고** `ws.merge_cells(start, end)`로 범위 병합.
- 셀 값 = `_coerceCell(htmlCell.text)` — 숫자 패턴이면 Number, 음수 패턴(`(1,234)`·`△`)이면 음수, 그 외 텍스트.
- caption/unit(`absorbCaptionUnitFromText` 대응)은 시트 1행 머지셀.
- `align="right"`/`isHeader`는 openpyxl 정렬·볼드.

`_writeHorizontalizedSheet`:
- 행 = 표의 row label(첫 컬럼), 열 = period(최신 좌측). finance 정량은 이미 `FinanceStatement{rows:[{label, values}]}` 구조라 `_writeFinanceSheet` 경로 재사용.
- 일반 공시 표는 canonical account_id가 없어 라벨 정렬이 불확실 → **불확실하면 as-filed로 자동 폴백 + 시트 노트 "수평화 미지원(원본 구조)"**(honest-gap, 거짓 정렬 금지).

`ModuleSource` 분기는 기존 `_writeFinanceSheet`/`_writeRatiosSheet`/`_writeDataFrameSheet` 그대로(회귀 0).

---

## 5. 정합 정규화 (엔진·브라우저 공유 명세)

"바로 계산 가능"의 임계 3종 + 보조. 엔진(`_coerceCell`)과 브라우저(`tableExtract.ts`)가 **동일 규칙**을 구현하고 같은 픽스처로 검증한다(02 §3).

| 항목 | 규칙 |
|---|---|
| **숫자 타입 (임계)** | `/^-?[\d,]+(\.\d+)?$/` 매칭 → 콤마 제거 후 int/float. "1,234" 텍스트가 아니라 1234 숫자. **콤마는 값에 넣지 않음**(표시서식은 엑셀이 담당, `#,##0`). |
| **음수 정규화 (임계)** | `(1,234)`→-1234, `△1,234`/`▲1234`→-1234. 한국 공시 괄호·삼각형 음수 흔함. |
| **단위 (임계)** | "(단위: 백만원)" 흡수 → **시트 상단 라벨/컬럼 주석**. 값은 원본 스케일 그대로(임의 환산 금지 — `feedback_xml_native_truth`). 단위 모르면 빈칸(추측 금지). |
| 천단위 구분 | 값은 콤마 없이, 표시서식 `#,##0`. |
| 병합셀 | colspan/rowspan → `merge_cells`(엔진)/`<mergeCell>`(브라우저). |
| 빈 셀 (honest-gap) | 결손 = 빈 셀. **0 대체 절대 금지.** horizontalized 미보고 기간 = 빈칸. |
| 텍스트 줄바꿈 | as-filed 텍스트 블록 `<br>`→`\n` + `wrap_text`. 평문 뭉개기 금지. |
| provenance | 시트(또는 `_출처` 시트)에 회사/종목코드/rceptNo/period/dartUrl/asOf/가공표기. |

---

## 6. 일괄(batch) 내보내기 — OOM 규율

회사 간 양식 이식(00 §3-b). panel이 disclosureKey 정렬이라 같은 양식을 N사에 적용 가능. **단 메모리가 율속** — Company 1개 200~500MB, `gc.collect()` 회수 0(CLAUDE.md 강행규칙).

결정:
- **회사당 개별 워크북**. 한 워크북에 N사 시트 누적 금지(openpyxl이 전 회사를 메모리에 들고 있으면 OOM).
- 순차 루프 + 회사당 즉시 디스크 flush + 참조 해제:
  ```python
  for code in codes:
      c = Company(code)
      exportWithTemplate(c, template, out_dir / f"{code}.xlsx")
      del c   # 다음 회사 전 해제
  ```
- **동시 ≤2 절대**(병렬 폭주 = Rust 힙 OOM). 서버는 `asyncio.to_thread` 직렬화.
- 결과 = 회사당 .xlsx → ZIP 묶음(디스크 레벨, 메모리 누적 아님).
- 신 엔드포인트 `POST /api/export/excel/batch` — 코드 리스트 + 양식 → 순차 생성 → ZIP `FileResponse`.

---

## 7. CLI / 서버

- CLI `dartlab excel <code>`는 유지. 양식 기반은 `--template <id>` 이미 서버에 있고 CLI에도 연결 가능(후속).
- 서버 기존 `GET /api/export/excel/{code}?modules=&templateId=` — 신 source union 통과(변경 최소).
- 신규 `POST /api/export/excel`(selection body) — 뷰어 선택을 임시 양식으로 받아 즉시 .xlsx(저장 없이). `templateId` 없이 selection→`ExcelTemplate` 직변환.
- 신규 `POST /api/export/excel/batch`(§6).

---

## 8. 영향 파일 / 함수

신규:
- `providers/dart/parse/` — `normalizeDartXml` Python 포팅(또는 `cellGrid` DART 태그 인식 확장).
- `viz/export/excel.py::_writePanelTableSheet`·`_writeGridSheet`·`_writeHorizontalizedSheet`·`_coerceCell`·`_selectPanelRow`.
- `server/api/data.py` — `POST /api/export/excel`(selection)·`/batch`.

수정:
- `viz/export/template.py` — `SheetSource` union(ModuleSource/PanelTableSource), `SheetSpec.source` 타입 변경 + `__post_init__`/`fromDict` 하위호환 정규화. PRESETS 무변경.
- `viz/export/excel.py::exportWithTemplate` — source `isinstance` 분기.
- `viz/export/sources.py` — (선택) 공시 테이블 디스커버리 추가. 단 미리보기 테이블 목록은 UI가 PanelBundle에서 직접 뽑으므로(03 §4) 엔진 디스커버리는 LLM/CLI용 보조.

불변(회귀 0):
- `store.py`, 기존 `exportToExcel`/`_writeDataFrameSheet`/`_writeFinanceSheet`, `panelXmlTables`/`panelTableRows`(텍스트 소비처).

---

## 9. 테스트 (요지 — 상세 05)

- source union round-trip(str→ModuleSource 흡수, dict→분기), 기존 PRESET·저장 템플릿 무변경 로드.
- `_coerceCell` 단위테스트: "1,234"→1234, "(1,234)"→-1234, "△5"→-5, "삼성전자"→문자열, ""→빈셀.
- `cellGrid` 병합 골든(02 §3 공유 픽스처) — colspan/rowspan/중첩/불규칙 행.
- horizontalized 폴백(라벨 정렬 불확실 → as-filed + 노트).
- 일괄 OOM 규율: 직접 `pytest tests/ -v` 금지 → `bash tests/test-lock.sh tests/<path> -m "<marker>" -v` 경유, 회사당 flush·동시 ≤2 검증.
