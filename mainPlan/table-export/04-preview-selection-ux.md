# 04. Preview & Selection UX — 미리보기 선택 인터랙션

상태: v0.1
범위: 뷰어에서 표를 보고 클릭해 양식을 구성하는 인터랙션. 기존 `ViewerStudio`/`PanelMatrix`/`PanelTocTree`/`AskDrawer`에 1:1 매핑.

---

## 0. 핵심 결정 — 뷰어 격자 = 미리보기

별도 "내보내기 모드/화면"을 만들지 않는다. 사용자는 이미 `PanelMatrix`에서 공시의 모든 테이블을 보고 있다(WYSIWYG). 추가하는 것은 ① 셀렉션 레이어(기존 glow 재사용) ② 선택 바구니 드로어(AskDrawer 슬롯 공유)뿐. 외부 서비스의 "미리보기를 따로 띄운다"를 *이미 가진 뷰어가 미리보기*라는 더 강한 형태로 흡수한다.

---

## 1. 진입점 (채택/기각)

| 후보 | 판정 | 이유 |
|---|---|---|
| **PanelMatrix 셀 체크박스 토글** | **채택(주)** | 셀 = `blockType` `table`/`text` 단위. 미리보기에서 본 그대로 = 셀 단위 선택이 WYSIWYG 정답. `PanelMatrix.svelte`는 셀 DOM에 이미 `data-cell={rowIndex|period}` 키 보유 → 선택 타겟 추가비용 0. |
| **PanelTocTree 항목 체크박스** | **채택(보조)** | section/block 라벨 좌측 체크 = "이 섹션 통째" 거시 선택. 셀 체크와 **같은 selection store 공유**. |
| 별도 "내보내기 모드" 전체 전환 | **기각** | 화면 전환 = 컨텍스트 손실. 헤더 버튼 1개가 셀렉션 레이어를 켜고/끄면 충분. 강함은 깎아서. |

채택 메커니즘: 헤더 기존 `[데이터]` 팝오버(`.data-dl`) 옆에 **`[표 내보내기]`** 버튼 1개. 토글하면:
- `PanelMatrix` body-cell 좌상단에 체크박스 오버레이 fade-in(`position:absolute` — 격자 레이아웃 시프트 0).
- `PanelTocTree` section/block 라벨 좌측 체크박스 동시 표시.
- 우측 `ExportDrawer` 열림(빈 안내).

---

## 2. selection 모델

선택 원자 = **(테이블 정체성 + 기간 범위)**. 셀 단위 선택이지만 내부는 "행(테이블) + 기간"으로 정규화 — 이게 horizontalized를 공짜로 가능케 한다.

```ts
// landing/src/lib/viewer/export/selection.svelte.ts (신규, Svelte 5 rune)
interface SheetSelection {
  id: string;              // 안정 키 = `${sectionKey}|${blockLeaf}` (disclosureKey 우선)
  sectionKey: string;
  blockLeaf: string;
  disclosureKey: string | null;
  scope: string | null;
  label: string;           // 편집 가능 시트명 (기본 = blockLeaf, 31자 트림)
  mode: 'asFiled' | 'horizontalized';   // 00 §3-a
  periods: string[] | 'all';            // 셀 선택이면 그 period, 행 전체면 'all'
  order: number;           // 드래그 정렬 = 시트 순서
}
```

체크 클릭 = add/remove. **선택 셀은 glow 메커니즘 재사용** — 펄스가 아니라 **steady 보더**(`inset 0 0 0 2px #fb923c` 상시) + 체크 표시. `PanelMatrix`에 `selectedCells: Set<string>` prop 추가, `data-cell` 키로 매칭(기존 glow effect 옆, 추가비용 0).

selection은 `ExportInput.selections`(03 §2) DTO로 직렬화 → `generate`. `[양식으로 저장]` 시 `ExcelTemplate`(`SheetSpec`=PanelTableSource)로 변환(01 §2).

---

## 3. ExportDrawer (선택 바구니)

`AskDrawer`가 차지하는 **동일 우측 슬롯**(`.studio.ask-open → grid-template-columns: 240px minmax(0,1fr) 380px`) 재사용. AskDrawer와 **상호배타**(380px 슬롯 1개 — 둘 중 하나만). 신규 `ExportDrawer.svelte`:

```
┌─ studio grid: [TOC 240][격자 1fr][ExportDrawer 380] ──────────────┐
│ TOC tree     │  PanelMatrix (체크박스 오버레이)  │ 표 내보내기      │
│ ☑ 재무제표    │  ┌2024─────┐┌2023─────┐         │ 선택 4개         │
│   ☑ 손익      │  │☑매출 100k││☐매출 95k │         │ ⠿ 손익계산서      │
│   ☐ 재무상태  │  │ 영업 12k ││ 영업 11k │         │   ◉수평 ○원본     │
│ ☐ 주석        │  └─────────┘└─────────┘         │   2024~2020      │
│   ☐ 일반사항  │  ┌2024─────┐                     │ ⠿ 배당내역        │
│               │  │☑배당 ₩361││                    │   ◉수평 ○원본     │
│               │  └─────────┘                     │ ⠿ 일반사항(텍스트) │
│               │                                  │ ─────────────── │
│               │                                  │ ☑ 출처 시트 포함  │
│               │                                  │ □ 회사 이식 ▸     │
│               │                                  │ 4시트·~18행·2024~ │
│               │                                  │ [내보내기 ⬇]      │
└──────────────────────────────────────────────────────────────────┘
```

드로어(위→아래):
1. **선택 시트 목록** — 항목별: 드래그 핸들(⠿=시트 순서) + 시트명 인라인 편집(`contenteditable`, 31자 카운터) + 모드 토글(◉수평/○원본) + 기간 칩 + ✕.
2. **글로벌 옵션** — `[☑ 출처 시트 포함]`(provenance 기본 ON), `[회사 이식 ▸]`(펼치면 비교모드 `CompanySearch` 재사용 → N사 종목코드).
3. **액션** — `[내보내기 ⬇]` + 위 회색 라이브 카운트("4시트·약 18행·2024~2020").

---

## 4. TOC → 시트 매핑 규칙

| 레벨 | 시트 매핑 | 근거 |
|---|---|---|
| `chapter`("재무에 관한 사항") | 시트명 prefix만(엑셀에 시트 그룹 없음) | 충돌 방지용 |
| `section`(sectionLeaf "손익계산서") | 선택 단위, 시트 1:1 아님 | 섹션 통째 체크 = 하위 block 전부 시트 전개 |
| `block`(blockLeaf/disclosureKey, 1테이블) | **시트 1:1 (기본)** | 미리보기 격자 셀=block=시트 1개 = WYSIWYG |

**기본 = 테이블 1:1 시트.** 같은 섹션 여러 block을 한 시트에 세로로 쌓는 건 옵션(드로어에서 시트끼리 드래그로 겹치면 "한 시트로 합치기" 제안). 1:1이 기본인 이유 — 격자에서 block들이 별개 셀로 보이므로 별개 시트가 WYSIWYG에 충실.

시트명(엔진 `excel.py`·`dataExport.ts::sheetName` 통일 SSOT):
1. 기본 = `blockLeaf`(없으면 `sectionLeaf`). 한글 그대로.
2. 금칙문자 `: \ / ? * [ ]` → 공백.
3. 유니코드 길이 31자 트림(한글 1자=1).
4. 충돌 → chapter 약어 prefix(`[재무] 손익`) → 그래도 충돌 `_2`,`_3`.
5. 빈/숫자시작 방지 → `시트{n}`.
6. 사용자 편집명 우선(31자 카운터 빨강 경고).

### 4.1 as-filed vs horizontalized 구조

- **as-filed(period 1개)**: 셀 raw XML → `normalizeDartXml`→`splitHtmlAndText`→`tableGrid` 그 표 구조 그대로 transcribe. 병합셀 보존. caption/unit 시트 상단 머지셀.
- **horizontalized(전 기간)**: 행=row label, 열=period(최신 좌측, `toc.periods` 순서). finance 정량은 `FinanceStatement` 구조 재사용. 일반 공시 표는 라벨 정렬 불확실하면 **as-filed 자동 폴백 + 시트 노트 "수평화 미지원(원본 구조)"**(honest-gap).

---

## 5. 사용자 여정 (클릭 1번 → 다운로드)

1. 헤더 `[표 내보내기]` → 선택 모드 on, 체크박스 fade-in, ExportDrawer 열림(빈 안내 "격자/목차에서 표를 체크하세요").
2. 격자 셀 체크 또는 TOC 섹션 체크 → 드로어 목록에 시트 추가, 선택 셀 steady glow.
3. (선택) 드로어 드래그 정렬 / 시트명 편집 / 모드 토글 / 기간 좁히기.
4. (선택) `[출처 시트]` 확인, `[회사 이식]`으로 N사 추가.
5. `[내보내기 ⬇]` → 표면별 산출(공개=브라우저 .xlsx 즉시 / 로컬=엔진 .xlsx). 다운로드 토스트, selection 유지(연속 내보내기), `[표 내보내기]` 재클릭으로 모드 종료.

선택→양식 빌드는 **암묵적**(중간 "양식 저장" 강제 없음 — selection state가 곧 임시 양식). `[양식으로 저장]`은 보조(명시 저장, `TemplateStore`/localStorage).

---

## 6. 3 표면 UX — 같음/다름

같아야: 선택 인터랙션(셀/TOC 체크박스·드로어·드래그·모드 토글)은 **3 표면 100% 동일**. `ViewerStudio`는 `embedded` prop으로 터미널/공개를 같은 본체로 마운트 → selection UI는 공통, 다운로드 백엔드만 분기.
다름: 포맷 충실도(공개=zero-dep .xlsx, 로컬=openpyxl 완전판 스타일) — 03 §7 tier UX로 명시.

---

## 7. 영향 파일 / 함수

신규(landing):
- `landing/src/lib/viewer/export/selection.svelte.ts` — selection store.
- `landing/src/lib/components/viewer/ExportDrawer.svelte` — 선택 바구니(AskDrawer 슬롯 공유).

수정(landing):
- `PanelMatrix.svelte` — `selecting` mode prop + 셀 체크박스 오버레이 + `selectedCells` steady glow(기존 glow·`data-cell` 재사용).
- `PanelTocTree.svelte` — section/block 체크박스(기존 onpick/onpickBlock 옆).
- `ViewerStudio.svelte` — `[표 내보내기]` 헤더 버튼, ExportDrawer 마운트(`.studio` 슬롯 로직에 `export-open` 추가, AskDrawer와 상호배타), 기존 `downloadFinanceExcel`/`downloadPanelCsv` 버튼 유지.

불변:
- `panelWide.ts`의 `PanelBundle`/`PanelRow`(순수 입력 재사용, 변경 0), `AskDrawer.svelte`(슬롯만 공유), 비교모드 `CompanySearch`(이식에서 재사용).
