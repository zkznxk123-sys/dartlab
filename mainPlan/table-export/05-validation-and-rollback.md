# 05. Validation & Rollback — 검증·롤백·단계 AC

상태: v0.1
범위: 테스트 매트릭스, 롤백 경로, OOM 테스트 규율, 성능 리스크, 단계별 수용 기준(AC).

---

## 1. 단계(Phase)와 AC

### Phase 1 — 엔진 (독립 착수)
산출: source union + `_writePanelTableSheet`(cellGrid 병합) + `normalizeDartXml` 포팅 + `_coerceCell` + 일괄.
AC:
- 기존 PRESET 3종·저장된 사용자 템플릿이 **무변경 로드**(하위호환 회귀 0).
- 임의 회사 1개의 공시 테이블을 `PanelTableSource`로 .xlsx 생성 — 병합셀 보존(openpyxl read로 mergeCells 확인), 숫자=Number·음수 정규화.
- horizontalized 모드가 finance 표에서 항목×기간 시트, 일반 표에서 폴백+노트.
- 일괄 N사: 회사당 개별 .xlsx + ZIP, 동시 ≤2, 회사당 flush(메모리 누적 없음).

### Phase 2 — 공개(landing) 브라우저
산출: zero-dep OOXML writer + `tableGrid`/`tableExtract` + ExportDrawer + selection.
AC:
- 브라우저 산출 .xlsx가 Excel·Google Sheets·Numbers에서 **경고 없이** 열림.
- `<mergeCell>` 병합·Number·음수·단위 헤더가 엔진 산출과 **동일 시트 구조**(골든 패리티).
- 미리보기 선택→드로어→다운로드 e2e(셀 체크·TOC 체크·드래그·모드 토글·다운로드·콘솔 0·svelte-check 0).
- 추가 npm 의존 0(번들 diff 확인).

### Phase 3 — 터미널 (뷰어 이관 편승)
산출: ExportPort public/local 어댑터 + command palette + surfaces 마운트.
AC:
- 로컬 터미널에서 같은 selection UX로 엔진 완전판 .xlsx.
- 공개에서 tier hint + `[설치]` 노출(숨김 0).
- 같은 `ExcelTemplate` JSON이 public/local 동일 시트 구조.

---

## 2. 테스트 매트릭스

| 영역 | 테스트 | 위치 |
|---|---|---|
| source 직렬화 | str→ModuleSource 흡수, dict→분기, round-trip, PRESET·저장템플릿 무변경 | 엔진 unit |
| 정합 정규화 | "1,234"→1234, "(1,234)"→-1234, "△5"→-5, "삼성"→str, ""→빈셀, 단위 흡수 | 엔진 `_coerceCell` + landing `tableExtract` (동일 케이스) |
| 격자 패리티 | colspan/rowspan/중첩/불규칙행/multi-row header → 공유 `*.grid.json` 일치 | 엔진 `cellGrid` + landing `tableGrid` (같은 픽스처) |
| xlsx 패리티 | 회사 1개 양 경로 .xlsx 시트명·시트수·셀값·mergeCell 일치(스타일 제외) | 엔진 openpyxl read + landing XML 파싱 |
| zip 유효성 | 브라우저 산출 바이트가 실제 unzip 가능·OOXML 스키마 유효 | landing vitest |
| horizontalized 폴백 | 라벨 정렬 불확실 → as-filed + 노트 | 엔진 + landing |
| 시트명 | 충돌·31자·금칙문자·한글·빈/숫자시작 | 공유 규칙 단위테스트 |
| 일괄 OOM | 회사당 flush·동시 ≤2·메모리 누적 없음 | 엔진(test-lock 경유) |
| e2e | 선택→드로어→다운로드, 회사이식, 양식 저장/불러오기 | landing Playwright |

### 2.1 공유 골든 픽스처 (패리티 SSOT)
`tests/fixtures/xmlTables/*.xml`(DART 대문자 원본) + `*.grid.json`(2D 셀 + 병합 범위 + 정규화 값). 엔진·브라우저 **양쪽 CI 게이트**. 발산 시 빨강. 새 병합 패턴 발견 시 픽스처 추가(부채 원장처럼 누적).

---

## 3. OOM 테스트 규율 (강행)

- `pytest tests/ -v` 전체 직접 호출 **금지**. `uv run python -X utf8 tests/run.py preflight`(CI 게이트 SSOT) + 단일 파일 `bash tests/test-lock.sh tests/<path> -m "<marker>" -v`.
- 신규 정합 로직 개념검증은 `tests/_attempts/tableExport/`에서(검증 전 src/ 오염 가드). 단 기존 `viz/export/`·`dataExport.ts`·`cell.ts` **확장**은 검증된 본진 보강이라 _attempts 우회 허용.
- 일괄 테스트는 회사 ≤2 + flush. fixture scope `module`.

---

## 4. 롤백

- **단계 독립 가역**: Phase 1(엔진)·2(공개)·3(터미널)은 각각 독립 commit 단위. 실패 시 직전 commit 복귀.
- **기존 경로 보존**: `exportToExcel`·`exportWithTemplate`(모듈 source)·`panelToCsv`·`financeToExcel`(.xls)·기존 다운로드 버튼은 신 경로 안착까지 **남긴다**. 신 .xlsx writer 안정 후 `financeToExcel`(.xls) deprecate(즉시 삭제 아님).
- **source 스키마**: 하위호환 정규화라 신 스키마 도입이 기존 저장 템플릿을 깨지 않음 — 롤백해도 데이터 손실 0.
- **번들**: 공개 writer가 문제면 기능 플래그로 `[표 내보내기]` 숨기고 기존 CSV/. xls 버튼만 노출(공개 무중단 — `feedback_ui_rules` 공개 터미널 무중단).

---

## 5. 성능 리스크 톱3 + 완화

1. **일괄(N사) 엔진 OOM** — Company 200~500MB, `gc.collect` 회수 0. 한 워크북 누적·병렬>2 = 즉시 OOM.
   - 완화: 회사당 개별 워크북 → 즉시 flush → `del c`. 동시 ≤2 절대. ZIP은 디스크 레벨. `asyncio.to_thread` 직렬화.
2. **브라우저 100+ 테이블 격자 전개 메인스레드 점유** — rowspan/colspan 전개는 셀 공유라 안전하나 전 테이블 동시 grid화 + XML 빌드가 UI 잼.
   - 완화: 텍스트 페이로드라 가볍지만 안전하게 시트 단위 yield(`requestIdleCallback`). 선제 Web Worker 금지(측정 후, `feedback_always_check_clutter`).
3. **엔진↔브라우저 파서 발산** — 두 독립 구현이 rowspan carry·불규칙 행·DART XML 정규화에서 미세 차이 → 같은 공시가 표면마다 다른 .xlsx.
   - 완화: 공유 골든 픽스처를 양쪽 CI 게이트. `normalizeDartXml`도 동일 픽스처. `panelXmlTables`(병합 버림)의 export 사용 차단을 리뷰/lint로.

---

## 6. 개발자 · PM 이중 평가 (00 §7 요약 재확인)

- 개발자: 신규 핵심 3(정합 정규화·source union·zero-dep OOXML), 나머지 배선. 리스크 2(zip 정확도·파서 발산) 모두 골든 픽스처로 통제. 단계 독립이라 부분 출시 가능.
- PM: 외부 UX 1:1 흡수 + panel 차별화 2(시계열·회사이식) 즉시 가시. 덕지덕지 4종 명시 제거. 공개→로컬 funnel 자연 배치. 단계가 독립 출시 가치.
