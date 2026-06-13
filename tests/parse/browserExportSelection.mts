// table-export Phase 2b — 선택 스토어 → buildWorkbook 입력 파생 → 진짜 .xlsx parity 게이트 (standalone node, vitest 0).
//
// SOURCE OF TRUTH = ui/packages/surfaces/src/viewer/lib/export/selection.svelte.ts (선택 스토어 + 파생). 본 파일은
// 브라우저 본체를 그대로 import 한다. selection.svelte.ts 는 Svelte 5 runes($state) 를 createSelectionStore 함수
// *본문* 에서만 쓰므로(모듈 top-level 0), runes 미해석 node 에서도 임포트 가능 — 호출 직전 $state 글로벌 shim 만 깐다.
// shim 은 $state(v)=v (런타임 동작상 정확: $state 는 reactive proxy 지만 평문 객체 변이도 본 스토어 로직과 동치).
//
//   uv 무관. 실행: npx tsx tests/parse/browserExportSelection.mts
//
// 4 게이트:
//   (1) 스토어 add/toggle/reorder/setLabel/setMode/clear 동작.
//   (2) 파생 — selection 2개(표 + 텍스트) → deriveWorkbookInput → SheetInput[] (출처 시트 포함).
//   (3) buildWorkbook → 진짜 .xlsx(EOCD/central dir/CRC32 STORE) + 시트 수 일치.
//   (4) 데이터 없는 선택 자동 제외(honest, 빈 시트 0).

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';

// ── Svelte 5 runes shim (호출 직전 — selection.svelte.ts 모듈 top-level 엔 rune 0이라 import 자체는 무관) ──
// $state(v) = v : 본 스토어는 평문 배열·객체 변이(push/splice/필드대입)만 쓰므로 reactive proxy 없이도 로직 동일.
(globalThis as unknown as { $state: <T>(v: T) => T }).$state = <T>(v: T): T => v;

import { normalizeDartXml } from '../../ui/packages/surfaces/src/viewer/lib/cell.ts';
import {
	createSelectionStore,
	deriveWorkbookInput,
	selectionToSheet,
	selectionId,
	trimLabel,
	type SheetSelection
} from '../../ui/packages/surfaces/src/viewer/lib/export/selection.svelte.ts';
import { buildWorkbook } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/buildWorkbook.ts';
import { crc32 } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/zipStore.ts';
import type { PanelBundle, PanelRow } from '../../ui/packages/surfaces/src/viewer/lib/types.ts';

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(here, '..', 'fixtures', 'xmlTables');

let failures = 0;
function ok(label: string): void {
	console.log(`  PASS  ${label}`);
}
function fail(label: string, detail: string): void {
	failures += 1;
	console.log(`  FAIL  ${label}\n        ${detail}`);
}
function eq(label: string, got: unknown, want: unknown): void {
	if (got === want) ok(label);
	else fail(label, `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
}

// ── 픽스처 PanelBundle 합성 — 실제 DART 표 XML(small_merged) 한 행(table) + narrative 텍스트 한 행 ──
const SECTION_KEY = 'III. 재무에 관한 사항␟손익계산서';
const tableXml = readFileSync(join(FIXTURES, 'small_merged.xml'), 'utf-8');

const tableRow: PanelRow = {
	chapter: 'III. 재무에 관한 사항',
	sectionLeaf: '손익계산서',
	blockLeaf: '손익계산서',
	leafType: 'TABLE',
	disclosureKey: 'IS',
	scope: 'consolidated',
	blockType: 'table',
	cells: { '2024Q4': tableXml, '2023Q4': tableXml }
};
const textRow: PanelRow = {
	chapter: 'III. 재무에 관한 사항',
	sectionLeaf: '손익계산서',
	blockLeaf: '일반사항',
	leafType: 'NARR',
	disclosureKey: null,
	scope: null,
	blockType: 'text',
	cells: {
		'2024Q4': '<P>당기 매출은 전년 대비 증가하였다.</P>',
		'2023Q4': '<P>전기 매출은 안정적이었다.</P>'
	}
};

const bundle: PanelBundle = {
	stockCode: '005930',
	corpName: '삼성전자',
	toc: { stockCode: '005930', corpName: '삼성전자', chapters: [], periods: ['2024Q4', '2023Q4'] },
	periods: ['2024Q4', '2023Q4'],
	gridBySection: new Map<string, PanelRow[]>([[SECTION_KEY, [tableRow, textRow]]]),
	dartUrlByPeriod: { '2024Q4': null, '2023Q4': null },
	periodKind: { '2024Q4': 'annual', '2023Q4': 'annual' }
};

// ── (1) 스토어 동작 ──
console.log('\n[1] 선택 스토어 add/toggle/reorder/setLabel/setMode/clear');
const store = createSelectionStore();
eq('초기 count 0', store.count, 0);

store.add({ sectionKey: SECTION_KEY, indexInSection: 0, row: tableRow }); // 표 행
store.add({ sectionKey: SECTION_KEY, indexInSection: 1, row: textRow }); // 텍스트 행
eq('add 2개 → count 2', store.count, 2);
eq('id 안정키(표)', store.items[0].id, selectionId(SECTION_KEY, 0));
eq('기본 label = blockLeaf(표)', store.items[0].label, '손익계산서');
eq('기본 mode = horizontalized', store.items[0].mode, 'horizontalized');
eq('기본 periods = all', store.items[0].periods, 'all');

// 중복 add 무시
store.add({ sectionKey: SECTION_KEY, indexInSection: 0, row: tableRow });
eq('중복 add 무시 → count 2', store.count, 2);

// toggle off → on
store.toggle({ sectionKey: SECTION_KEY, indexInSection: 0, row: tableRow });
eq('toggle 기존 → 제거 count 1', store.count, 1);
store.toggle({ sectionKey: SECTION_KEY, indexInSection: 0, row: tableRow });
eq('toggle 없음 → 추가 count 2', store.count, 2);

// idSet — PanelMatrix glow 매칭
const ids = store.idSet();
eq('idSet has 표', ids.has(selectionId(SECTION_KEY, 0)), true);
eq('idSet has 텍스트', ids.has(selectionId(SECTION_KEY, 1)), true);

// setLabel(31자 트림) + setMode
const longName = '아주아주아주아주아주아주아주아주아주아주아주긴시트이름입니다정말로'; // >31
store.setLabel(selectionId(SECTION_KEY, 0), longName);
eq('setLabel 31자 트림', [...store.items[0].label].length <= 31, true);
eq('trimLabel 헬퍼 31자', [...trimLabel(longName)].length, 31);
store.setMode(selectionId(SECTION_KEY, 0), 'asFiled');
eq('setMode asFiled', store.items.find((s) => s.id === selectionId(SECTION_KEY, 0))!.mode, 'asFiled');

// reorder — 표(0) 를 텍스트(1) 위치로
const orderedBefore = store.ordered().map((s) => s.id);
store.reorder(selectionId(SECTION_KEY, 0), selectionId(SECTION_KEY, 1));
const orderedAfter = store.ordered().map((s) => s.id);
eq('reorder 순서 뒤바뀜', JSON.stringify(orderedAfter), JSON.stringify([...orderedBefore].reverse()));

// ── (2) 파생 — selectionToSheet + deriveWorkbookInput ──
console.log('\n[2] selectionToSheet + deriveWorkbookInput');
// 표 행을 다시 horizontalized 로 되돌리고 순서 복원(표 먼저).
store.clear();
const s2 = createSelectionStore();
s2.add({ sectionKey: SECTION_KEY, indexInSection: 0, row: tableRow }); // 표(horizontalized 기본)
s2.add({ sectionKey: SECTION_KEY, indexInSection: 1, row: textRow }); // 텍스트(horizontalized)

// 표 행 horizontalized → as-filed 폴백 + 노트
const tableSheet = selectionToSheet(s2.items[0], bundle);
if (tableSheet && tableSheet.grid.length > 0 && (tableSheet.note ?? '').includes('수평화 미지원')) {
	ok(`표 horizontalized → as-filed 폴백 + 노트 (${tableSheet.grid.length}행)`);
} else {
	fail('표 horizontalized 폴백', `grid=${tableSheet?.grid.length} note=${JSON.stringify(tableSheet?.note)}`);
}
// 병합 보존 — small_merged 첫 행 colspan=2 → 같은 인스턴스 공유
if (tableSheet && tableSheet.grid[0]?.[0] && tableSheet.grid[0][0] === tableSheet.grid[0][1]) {
	ok('표 병합셀 인스턴스 공유 보존(grid[0][0]===grid[0][1])');
} else {
	fail('표 병합 보존', '첫 행 병합 인스턴스 불일치');
}

// 텍스트 행 horizontalized → 기간×내용 2열, 헤더 + 2 기간 행
const textSheet = selectionToSheet(s2.items[1], bundle);
if (textSheet && textSheet.grid.length === 3 && textSheet.grid[0][0].text === '기간') {
	ok(`텍스트 horizontalized → 헤더+2기간 (${textSheet.grid.length}행)`);
} else {
	fail('텍스트 horizontalized', `grid=${textSheet?.grid.length} head=${JSON.stringify(textSheet?.grid[0]?.[0]?.text)}`);
}
const sawText = textSheet?.grid.some((r) => r.some((c) => c.text.includes('당기 매출')));
eq('텍스트 본문 strip(태그 제거) 포함', sawText, true);

// deriveWorkbookInput — 2 시트 + 출처 시트
const sheets = deriveWorkbookInput(s2.ordered(), bundle, true);
eq('deriveWorkbookInput 시트 수 = 2 + 출처 1', sheets.length, 3);
eq('출처 시트 라벨', sheets[2].label, '출처');

// 출처 미포함
const noSource = deriveWorkbookInput(s2.ordered(), bundle, false);
eq('출처 미포함 → 2 시트', noSource.length, 2);

// ── (3) buildWorkbook → 진짜 .xlsx ──
console.log('\n[3] buildWorkbook → 진짜 .xlsx (EOCD/central dir/CRC32 STORE)');
const bytes = buildWorkbook(sheets);

const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
if (dv.getUint32(0, true) === 0x04034b50) ok('local file header signature (PK\\x03\\x04)');
else fail('local file header signature', `got 0x${dv.getUint32(0, true).toString(16)}`);

const eocdOff = bytes.length - 22;
if (dv.getUint32(eocdOff, true) === 0x06054b50) ok('EOCD signature (PK\\x05\\x06)');
else fail('EOCD signature', `expected at offset ${eocdOff}`);

const cdCount = dv.getUint16(eocdOff + 10, true);
const cdOff = dv.getUint32(eocdOff + 16, true);

const decoder = new TextDecoder('utf-8');
const partsRead: Record<string, Uint8Array> = {};
let p = cdOff;
let cdParsedOk = true;
for (let i = 0; i < cdCount; i += 1) {
	if (dv.getUint32(p, true) !== 0x02014b50) {
		fail('central dir signature', `entry ${i} at ${p}`);
		cdParsedOk = false;
		break;
	}
	const method = dv.getUint16(p + 10, true);
	const crcStored = dv.getUint32(p + 16, true);
	const compSize = dv.getUint32(p + 20, true);
	const uncompSize = dv.getUint32(p + 24, true);
	const nameLen = dv.getUint16(p + 28, true);
	const extraLen = dv.getUint16(p + 30, true);
	const commentLen = dv.getUint16(p + 32, true);
	const localOff = dv.getUint32(p + 42, true);
	const name = decoder.decode(bytes.subarray(p + 46, p + 46 + nameLen));
	if (method !== 0) {
		fail(`entry ${name} STORE`, `method=${method}`);
		cdParsedOk = false;
	}
	if (compSize !== uncompSize) {
		fail(`entry ${name} size`, `comp ${compSize} != uncomp ${uncompSize}`);
		cdParsedOk = false;
	}
	const lNameLen = dv.getUint16(localOff + 26, true);
	const lExtraLen = dv.getUint16(localOff + 28, true);
	const dataStart = localOff + 30 + lNameLen + lExtraLen;
	const data = bytes.subarray(dataStart, dataStart + compSize);
	if (crc32(data) !== crcStored) {
		fail(`entry ${name} CRC32`, `computed mismatch`);
		cdParsedOk = false;
	}
	partsRead[name] = data;
	p += 46 + nameLen + extraLen + commentLen;
}
if (cdParsedOk) ok(`central directory: ${cdCount} entries, STORE + CRC32 verified`);

// OOXML 필수 파트 — 3 시트.
const required = [
	'[Content_Types].xml',
	'_rels/.rels',
	'xl/workbook.xml',
	'xl/_rels/workbook.xml.rels',
	'xl/styles.xml',
	'xl/worksheets/sheet1.xml',
	'xl/worksheets/sheet2.xml',
	'xl/worksheets/sheet3.xml'
];
const missing = required.filter((r) => !(r in partsRead));
if (missing.length === 0) ok(`OOXML parts present: ${required.length}/${required.length} (3 시트)`);
else fail('OOXML parts', `missing ${missing.join(', ')}`);

const wbXml = decoder.decode(partsRead['xl/workbook.xml'] ?? new Uint8Array());
const names = [...wbXml.matchAll(/<sheet name="([^"]*)"/g)].map((m) => m[1]);
eq('워크북 시트 3개', names.length, 3);
if (names.includes('출처')) ok('출처 시트명 존재');
else fail('출처 시트명', `got ${JSON.stringify(names)}`);

// ── (4) honest — 데이터 없는 선택 자동 제외 ──
console.log('\n[4] honest — 데이터 없는 선택 자동 제외');
const s4 = createSelectionStore();
const emptyRow: PanelRow = { ...textRow, blockLeaf: '빈행', cells: {} }; // 셀 0
const bundle4: PanelBundle = {
	...bundle,
	gridBySection: new Map<string, PanelRow[]>([[SECTION_KEY, [emptyRow]]])
};
s4.add({ sectionKey: SECTION_KEY, indexInSection: 0, row: emptyRow });
const emptyDerived = deriveWorkbookInput(s4.ordered(), bundle4, true);
eq('빈 셀 선택 → 시트 0 (출처도 0, 크래시 0)', emptyDerived.length, 0);
eq('selectionToSheet(빈) → null', selectionToSheet(s4.items[0], bundle4), null);

// 존재하지 않는 indexInSection (stale 선택) → null, 크래시 0
const staleSel: SheetSelection = { ...s4.items[0], indexInSection: 99, id: selectionId(SECTION_KEY, 99) };
eq('stale 인덱스 선택 → null', selectionToSheet(staleSel, bundle4), null);

// 산출물 디스크 저장(수동 Excel/openpyxl 검수).
const outPath = join(tmpdir(), 'dartlab_table_export_selection.xlsx');
writeFileSync(outPath, bytes);
ok(`wrote ${bytes.length} bytes → ${outPath}`);

console.log(`\n${failures === 0 ? 'ALL PASS' : `${failures} FAILURE(S)`}\n`);
process.exit(failures === 0 ? 0 : 1);
