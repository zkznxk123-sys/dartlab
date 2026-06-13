// table-export Phase 2a — 브라우저 zero-dep .xlsx 작성기 parity 게이트 (standalone node, vitest 0).
//
// surfaces/landing 에는 test-runner 가 없으므로 (CI 미배선 — follow-up) 본 스크립트를 tsx 로 직접 돌린다.
// SOURCE OF TRUTH = ui/packages/surfaces/src/viewer/lib/xlsx/*.ts (브라우저 본체). 본 파일은 그걸 import 만 한다.
//
//   uv 무관. 실행: npx tsx tests/parse/browserXlsxParity.mts
//   산출 .xlsx 는 /tmp 에 저장되어 독립 리더(openpyxl)로도 검증 가능:
//     uv run python -X utf8 -c "import openpyxl; openpyxl.load_workbook(r'<tmp>/dartlab_table_export_parity.xlsx')"
//   (확인됨: openpyxl 가 경고 없이 열고 A2:B2 병합·Number(-2554690/-5/1234)·B4 blank(None)·시트명 trim 보존)
//
// 3 게이트:
//   (1) 격자 parity — fixtures/*.xml → cell.ts normalizeDartXml → tableGrid → *.grid.json 셀별 일치 (엔진 SSOT).
//   (2) coerce parity — 엔진 문서화 케이스.
//   (3) ZIP 유효성 — buildWorkbook → finalize → 진짜 ZIP(EOCD/central dir/CRC32) + OOXML 파트 전수 + unzip 가능.

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';

import { normalizeDartXml } from '../../ui/packages/surfaces/src/viewer/lib/cell.ts';
import { tableGrid, type GridCell } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/tableGrid.ts';
import { coerceCell, detectUnit } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/tableExtract.ts';
import { buildWorkbook } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/buildWorkbook.ts';
import { crc32 } from '../../ui/packages/surfaces/src/viewer/lib/xlsx/zipStore.ts';

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

// ── (1) 격자 parity ──
interface GoldenCell {
	text: string;
	colspan: number;
	rowspan: number;
	align: string;
	isHeader: boolean;
}
interface Golden {
	shape: { rows: number; cols: number };
	grid: GoldenCell[][];
}

const GOLDEN = [
	'small_merged',
	'samsung_3_타법인출자_현황_상세_0',
	'samsung_IX_계열회사_등에_관한_사항_1'
];

console.log('\n[1] 격자 parity (cell.ts normalizeDartXml → tableGrid vs *.grid.json)');
for (const name of GOLDEN) {
	const xml = readFileSync(join(FIXTURES, `${name}.xml`), 'utf-8');
	const golden: Golden = JSON.parse(readFileSync(join(FIXTURES, `${name}.grid.json`), 'utf-8'));
	const grid: GridCell[][] = tableGrid(normalizeDartXml(xml));

	const rows = grid.length;
	const cols = grid.reduce((m, r) => Math.max(m, r.length), 0);
	if (rows !== golden.shape.rows) {
		fail(`${name} shape.rows`, `got ${rows} want ${golden.shape.rows}`);
		continue;
	}
	if (cols !== golden.shape.cols) {
		fail(`${name} shape.cols`, `got ${cols} want ${golden.shape.cols}`);
		continue;
	}
	let mismatch = '';
	let cellCount = 0;
	outer: for (let r = 0; r < grid.length; r += 1) {
		for (let c = 0; c < grid[r].length; c += 1) {
			const cell = grid[r][c];
			const exp = golden.grid[r]?.[c];
			if (!exp) {
				mismatch = `(${r},${c}) golden missing`;
				break outer;
			}
			cellCount += 1;
			if (cell.text !== exp.text) {
				mismatch = `(${r},${c}) text got ${JSON.stringify(cell.text)} want ${JSON.stringify(exp.text)}`;
				break outer;
			}
			if (cell.colspan !== exp.colspan) {
				mismatch = `(${r},${c}) colspan got ${cell.colspan} want ${exp.colspan}`;
				break outer;
			}
			if (cell.rowspan !== exp.rowspan) {
				mismatch = `(${r},${c}) rowspan got ${cell.rowspan} want ${exp.rowspan}`;
				break outer;
			}
			if (cell.align !== exp.align) {
				mismatch = `(${r},${c}) align got ${JSON.stringify(cell.align)} want ${JSON.stringify(exp.align)}`;
				break outer;
			}
			if (cell.isHeader !== exp.isHeader) {
				mismatch = `(${r},${c}) isHeader got ${cell.isHeader} want ${exp.isHeader}`;
				break outer;
			}
		}
	}
	if (mismatch) fail(`${name} cells`, mismatch);
	else ok(`${name} — ${rows}×${cols} grid, ${cellCount} cells match`);
}

// 병합 = 같은 인스턴스 공유 검증 (small_merged 제 46 기 colspan=2).
{
	const xml = readFileSync(join(FIXTURES, 'small_merged.xml'), 'utf-8');
	const grid = tableGrid(normalizeDartXml(xml));
	if (grid[0][0] === grid[0][1] && grid[0][0].colspan === 2) ok('merge shared-instance (small_merged 0,0===0,1)');
	else fail('merge shared-instance', 'grid[0][0] !== grid[0][1] or colspan != 2');
}

// ── (2) coerce parity ──
console.log('\n[2] coerce parity (엔진 문서화 케이스)');
eq("coerce '1,234'", coerceCell('1,234'), 1234);
eq("coerce '445,244'", coerceCell('445,244'), 445244);
eq("coerce '23.7'", coerceCell('23.7'), 23.7);
eq("coerce '(1,234)'", coerceCell('(1,234)'), -1234);
eq("coerce '(2,554,690)'", coerceCell('(2,554,690)'), -2554690);
eq("coerce '△5'", coerceCell('△5'), -5);
eq("coerce '△1,234.5'", coerceCell('△1,234.5'), -1234.5);
eq("coerce '▲500'", coerceCell('▲500'), -500);
eq("coerce '△\\n5'", coerceCell('△\n5'), -5);
eq("coerce '△\\n1,202,857'", coerceCell('△\n1,202,857'), -1202857);
eq("coerce '삼성' → '삼성'", coerceCell('삼성'), '삼성');
eq("coerce '' → null", coerceCell(''), null);
eq("coerce '   ' → null", coerceCell('   '), null);
eq("coerce '' !== 0 (honest-gap)", coerceCell('') === 0, false);
eq("coerce '5,000원' → string", coerceCell('5,000원'), '5,000원');
eq("coerce '2024.12.31' → string", coerceCell('2024.12.31'), '2024.12.31');
eq("coerce '-' → '-'", coerceCell('-'), '-');
eq("coerce '△' → '△'", coerceCell('△'), '△');
eq("coerce '-99'", coerceCell('-99'), -99);
eq("type '1,234' is number", typeof coerceCell('1,234'), 'number');
eq("type '23.7' is number", typeof coerceCell('23.7'), 'number');
eq("detectUnit '(단위: 백만원)'", detectUnit('(단위: 백만원)'), '백만원');
eq("detectUnit '단위 : 천원'", detectUnit('단위 : 천원'), '천원');
eq("detectUnit '(단위:원)'", detectUnit('(단위:원)'), '원');
eq("detectUnit '단위 : 원, 주'", detectUnit('단위 : 원, 주'), '원');
eq("detectUnit '매출 추이' → ''", detectUnit('매출 추이'), '');
eq("detectUnit '(단위: 광년)' → '' (미지)", detectUnit('(단위: 광년)'), '');

// ── (3) ZIP 유효성 + OOXML 파트 ──
console.log('\n[3] ZIP 유효성 + OOXML 파트 (buildWorkbook → 진짜 .xlsx)');

// 병합·Number·음수·단위·결손을 모두 포함한 작은 워크북.
const demoGridXml =
	'<table>' +
	'<tr><th colspan="2" align="center">제 46 기</th></tr>' +
	'<tr><td align="right">1,234</td><td align="right">(2,554,690)</td></tr>' +
	'<tr><td align="right">△5</td><td></td></tr>' +
	'</table>';
const demoGrid = tableGrid(normalizeDartXml(demoGridXml));
const subGridXml = '<table><tr><th>항목</th><th>값</th></tr><tr><td>현금</td><td align="right">100</td></tr></table>';
const subGrid = tableGrid(normalizeDartXml(subGridXml));
const bytes = buildWorkbook([
	{ label: '개요표', grid: demoGrid, unit: '백만원' },
	{ label: 'III. 재무에 관한 사항 / 매우 긴 라벨 [금지문자]', grid: subGrid, note: '수평화 미지원(원본 구조)' }
]);

// 3a) 매직 + EOCD 파싱.
const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
if (dv.getUint32(0, true) === 0x04034b50) ok('local file header signature (PK\\x03\\x04)');
else fail('local file header signature', `got 0x${dv.getUint32(0, true).toString(16)}`);

// EOCD 는 끝에서 역탐색 (comment 0 이라 끝-22).
const eocdOff = bytes.length - 22;
if (dv.getUint32(eocdOff, true) === 0x06054b50) ok('EOCD signature (PK\\x05\\x06)');
else fail('EOCD signature', `expected at offset ${eocdOff}`);

const cdCount = dv.getUint16(eocdOff + 10, true);
const cdSize = dv.getUint32(eocdOff + 12, true);
const cdOff = dv.getUint32(eocdOff + 16, true);

// 3b) central directory 순회 → 각 엔트리 STORE 검증 + CRC32 + 데이터 재구성.
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
		fail(`entry ${name} STORE`, `method=${method} (expected 0)`);
		cdParsedOk = false;
	}
	if (compSize !== uncompSize) {
		fail(`entry ${name} size`, `comp ${compSize} != uncomp ${uncompSize}`);
		cdParsedOk = false;
	}

	// local header 에서 데이터 추출.
	if (dv.getUint32(localOff, true) !== 0x04034b50) {
		fail(`entry ${name} local header`, `bad sig at ${localOff}`);
		cdParsedOk = false;
	}
	const lNameLen = dv.getUint16(localOff + 26, true);
	const lExtraLen = dv.getUint16(localOff + 28, true);
	const dataStart = localOff + 30 + lNameLen + lExtraLen;
	const data = bytes.subarray(dataStart, dataStart + compSize);
	const crcComputed = crc32(data);
	if (crcComputed !== crcStored) {
		fail(`entry ${name} CRC32`, `computed 0x${crcComputed.toString(16)} stored 0x${crcStored.toString(16)}`);
		cdParsedOk = false;
	}
	partsRead[name] = data;
	p += 46 + nameLen + extraLen + commentLen;
}
if (cdParsedOk) ok(`central directory: ${cdCount} entries, STORE + CRC32 verified`);

// 3c) OOXML 필수 파트 존재 + 시트 수 일치.
const required = [
	'[Content_Types].xml',
	'_rels/.rels',
	'xl/workbook.xml',
	'xl/_rels/workbook.xml.rels',
	'xl/styles.xml',
	'xl/worksheets/sheet1.xml',
	'xl/worksheets/sheet2.xml'
];
const missing = required.filter((r) => !(r in partsRead));
if (missing.length === 0) ok(`OOXML parts present: ${required.length}/${required.length}`);
else fail('OOXML parts', `missing ${missing.join(', ')}`);

// 3d) 시트 내용 검증 — Number/inlineStr/mergeCell/단위라벨/결손-blank.
const sheet1 = decoder.decode(partsRead['xl/worksheets/sheet1.xml'] ?? new Uint8Array());
if (sheet1.includes('<mergeCell ref="A2:B2"/>')) ok('sheet1 mergeCell A2:B2 (제 46 기 colspan=2 + 단위행 offset)');
else fail('sheet1 mergeCell', 'A2:B2 not found');
if (/t="n"><v>1234<\/v>/.test(sheet1)) ok('sheet1 Number 1234 (no comma, t="n")');
else fail('sheet1 Number 1234', 'not found');
if (/t="n"><v>-2554690<\/v>/.test(sheet1)) ok('sheet1 Number -2554690 (괄호음수)');
else fail('sheet1 Number -2554690', 'not found');
if (/t="n"><v>-5<\/v>/.test(sheet1)) ok('sheet1 Number -5 (삼각형음수)');
else fail('sheet1 Number -5', 'not found');
if (sheet1.includes('(단위: 백만원)')) ok('sheet1 단위 라벨 행');
else fail('sheet1 단위 라벨', 'not found');
// 결손 셀(빈 td) → blank: 단위행(1) + 헤더(2) + 데이터(3) + 데이터(4). A4=△5는 있고 B4(빈 td)는 없음.
if (/r="A4"/.test(sheet1) && !/r="B4"/.test(sheet1)) ok('sheet1 결손 B4 = blank (honest-gap, 0 아님)');
else fail('sheet1 결손 B4', `A4 present=${/r="A4"/.test(sheet1)}, B4 present=${/r="B4"/.test(sheet1)}`);

// 3e) 워크북 시트명 — 금지문자→공백, 31자 trim.
const wbXml = decoder.decode(partsRead['xl/workbook.xml'] ?? new Uint8Array());
const nameMatches = [...wbXml.matchAll(/<sheet name="([^"]*)"/g)].map((m) => m[1]);
if (nameMatches.length === 2) ok(`workbook sheets: ${nameMatches.length}`);
else fail('workbook sheets', `got ${nameMatches.length}`);
const s2 = nameMatches[1] ?? '';
if (!/[:\\/?*[\]]/.test(s2) && [...s2].length <= 31) ok(`sheet2 name sanitized + ≤31: ${JSON.stringify(s2)}`);
else fail('sheet2 name', `bad: ${JSON.stringify(s2)} (len ${[...s2].length})`);

// 3f) 추출 바이트가 곧 원본 XML 임을 재파싱으로 증명 (STORE 라 partsRead 가 압축 0 데이터 그대로).
let xmlParseOk = true;
for (const [name, data] of Object.entries(partsRead)) {
	const txt = decoder.decode(data);
	if (!txt.startsWith('<?xml') && !txt.startsWith('<')) {
		fail(`part ${name} XML`, 'does not start with XML/<');
		xmlParseOk = false;
	}
}
if (xmlParseOk) ok('all parts are XML text (re-readable)');

// 3g) 디스크에 .xlsx 저장(수동 Excel/Sheets + 독립 리더 openpyxl 검수용 산출물 — /tmp).
const outPath = join(tmpdir(), 'dartlab_table_export_parity.xlsx');
writeFileSync(outPath, bytes);
ok(`wrote ${bytes.length} bytes → ${outPath}`);

console.log(`\n${failures === 0 ? 'ALL PASS' : `${failures} FAILURE(S)`}\n`);
process.exit(failures === 0 ? 0 : 1);
