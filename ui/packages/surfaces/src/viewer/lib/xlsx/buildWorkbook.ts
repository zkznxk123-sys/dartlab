// buildWorkbook — 격자 시트들 → 진짜 .xlsx 바이트. 엔진 `viz/export/excel.py::_writeGridSheet` +
// `_mergeRanges` 의 브라우저 대응. 병합셀은 앵커(top-left)에만 값 1회 + <mergeCell> 범위, coerceCell 로
// Number/text, unit/note 는 상단 라벨 행, 결손 빈셀은 blank(0 금지 — honest-gap).
//
// 시트명 규칙: 31자 유니코드 trim · 금지문자(: \ / ? * [ ])→공백 · 충돌→"_2" · 빈/숫자시작→"시트N".

import type { GridCell } from './tableGrid';
import { coerceCell } from './tableExtract';
import {
	STYLE,
	cellRef,
	emitOoxmlParts,
	type SheetCell,
	type SheetPart
} from './workbook';
import { ZipStore } from './zipStore';

export interface SheetInput {
	label: string;
	grid: GridCell[][];
	unit?: string;
	note?: string;
}

const FORBIDDEN_RE = /[:\\/?*[\]]/g;

/** 시트명 정규화 — 금지문자→공백, 31자 trim, 빈/숫자시작 폴백, 충돌 dedup. */
export function sheetName(raw: string, used: Set<string>, index: number): string {
	let name = (raw || '').replace(FORBIDDEN_RE, ' ').trim().slice(0, 31).trim();
	// 빈 이름 또는 숫자로 시작(Excel 이 시트명 숫자시작 싫어함) → "시트N".
	if (!name || /^[0-9]/.test(name)) name = `시트${index + 1}`;
	// 충돌 → "_2"(31자 한도 유지).
	if (used.has(name)) {
		let candidate = `${name.slice(0, 28)}_2`;
		let n = 2;
		while (used.has(candidate)) {
			n += 1;
			candidate = `${name.slice(0, 28)}_${n}`;
		}
		name = candidate.slice(0, 31);
	}
	used.add(name);
	return name;
}

// 격자 병합 범위 추출 — 같은 GridCell 인스턴스가 여러 좌표면 그 extent 가 병합 범위.
// 엔진 `_mergeRanges` 대응 (id() 대신 인스턴스 참조 Map). 극단 rowspan 도 단일 범위 1개.
interface Extent {
	minR: number;
	minC: number;
	maxR: number;
	maxC: number;
}
function mergeRanges(grid: GridCell[][]): Map<GridCell, Extent> {
	const coords = new Map<GridCell, Array<[number, number]>>();
	for (let r = 0; r < grid.length; r += 1) {
		const row = grid[r];
		for (let c = 0; c < row.length; c += 1) {
			const cell = row[c];
			const arr = coords.get(cell);
			if (arr) arr.push([r, c]);
			else coords.set(cell, [[r, c]]);
		}
	}
	const ext = new Map<GridCell, Extent>();
	for (const [cell, cl] of coords) {
		let minR = Infinity;
		let minC = Infinity;
		let maxR = -Infinity;
		let maxC = -Infinity;
		for (const [r, c] of cl) {
			if (r < minR) minR = r;
			if (r > maxR) maxR = r;
			if (c < minC) minC = c;
			if (c > maxC) maxC = c;
		}
		ext.set(cell, { minR, minC, maxR, maxC });
	}
	return ext;
}

// 한 격자 → SheetPart (셀 + 병합). 엔진 `_writeGridSheet` 대응.
function gridToSheet(name: string, input: SheetInput): SheetPart {
	const cells: SheetCell[] = [];
	const merges: string[] = [];
	let startRow = 0; // 0-base

	// 단위·노트 머리 행 (값 환산 없음 — 라벨만).
	if (input.unit) {
		cells.push({ row: startRow, col: 0, value: `(단위: ${input.unit})`, styleId: STYLE.NOTE });
		startRow += 1;
	}
	if (input.note) {
		cells.push({ row: startRow, col: 0, value: input.note, styleId: STYLE.NOTE });
		startRow += 1;
	}

	const grid = input.grid;
	const ext = mergeRanges(grid);
	const written = new Set<GridCell>();
	let nCols = 0;
	for (const row of grid) if (row.length > nCols) nCols = row.length;

	for (let r = 0; r < grid.length; r += 1) {
		const row = grid[r];
		for (let cIdx = 0; cIdx < nCols; cIdx += 1) {
			const cell = cIdx < row.length ? row[cIdx] : undefined;
			if (!cell) continue;
			if (written.has(cell)) continue; // 병합셀 — 앵커에만 1회 쓰기
			written.add(cell);
			const e = ext.get(cell)!;
			const value = coerceCell(cell.text);
			const xlRow = startRow + e.minR;
			const xlCol = e.minC;

			// honest-gap: 결손(null)은 셀 자체를 안 쓴다(blank, 0 금지). 단 병합 범위는 그대로 emit.
			if (value !== null) {
				let styleId: number;
				if (typeof value === 'number') {
					styleId = STYLE.NUMBER_NEG;
				} else {
					// 텍스트 — align + wrapText 반영.
					const wrap = cell.text.indexOf('\n') >= 0;
					if (wrap) styleId = STYLE.TEXT_WRAP;
					else if (cell.align === 'right') styleId = STYLE.TEXT_RIGHT;
					else if (cell.align === 'center') styleId = STYLE.TEXT_CENTER;
					else if (cell.isHeader) styleId = STYLE.HEADER;
					else styleId = STYLE.TEXT;
				}
				cells.push({ row: xlRow, col: xlCol, value, styleId });
			}

			// 극단 rowspan 포함 — 단일 merge 범위 1개.
			if (e.maxR > e.minR || e.maxC > e.minC) {
				merges.push(
					`${cellRef(startRow + e.minR, e.minC)}:${cellRef(startRow + e.maxR, e.maxC)}`
				);
			}
		}
	}

	return { name, cells, merges };
}

/**
 * 시트 입력들 → 진짜 .xlsx 바이트 (zero-dep OOXML + STORE ZIP).
 *
 * @param sheets 시트별 { label, grid, unit?, note? }.
 * @returns 완성된 .xlsx 의 Uint8Array (다운로드 가능).
 *
 * @example
 * const bytes = buildWorkbook([{ label: '개요표', grid, unit: '백만원' }]);
 */
export function buildWorkbook(sheets: SheetInput[]): Uint8Array {
	const used = new Set<string>();
	const parts: SheetPart[] = sheets.map((s, i) => gridToSheet(sheetName(s.label, used, i), s));

	const ooxml = emitOoxmlParts(parts);
	const zip = new ZipStore();
	const te = new TextEncoder();
	// [Content_Types].xml 을 먼저 두는 게 관례(필수는 아님).
	const order = Object.keys(ooxml).sort((a, b) =>
		a === '[Content_Types].xml' ? -1 : b === '[Content_Types].xml' ? 1 : a.localeCompare(b)
	);
	for (const path of order) {
		zip.addEntry(path, te.encode(ooxml[path]));
	}
	return zip.finalize();
}
