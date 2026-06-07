// Row-mode company compare — browser mirror of Python `panel.compare` row identity.
// Keyed rows align by (disclosureKey, scope, leafType) across companies regardless of
// section number; narrative rows (no key) stay base-company local. The base company
// (bundles[0]) section drives WHICH rows show (same TOC); other companies' values come
// from a global disclosureKey lookup so 절번호 drift no longer mis-aligns
// (삼성 "7.유형자산" ↔ SK "11.유형자산" 한 행).

import type { PanelBundle } from '../types';
import { COMPARE_SEP, type AlignedRow, type CompareDiagnostics } from './types';
import { alignKeyOf, bundleIndex, rowLeafType } from './bundleIndex';

function shareClass(cells: (string | null)[]): 'shared' | 'partial' | 'solo' {
	const present = cells.filter((c) => c != null).length;
	return present >= cells.length ? 'shared' : present > 1 ? 'partial' : 'solo';
}

export interface RowCompareResult {
	rows: AlignedRow[];
	diagnostics: CompareDiagnostics;
}

// N bundle section at one period. Content-bearing rows only; null cells mean honest-gap.
export function alignBundles(bundles: PanelBundle[], sectionKey: string, period: string): AlignedRow[] {
	return compareRows(bundles, sectionKey, period).rows;
}

// Base (bundles[0]) section defines the rows in TOC order; each company's cell is resolved
// by disclosureKey across its whole panel (not by the drift-prone sectionKey).
export function compareRows(bundles: PanelBundle[], sectionKey: string, period: string): RowCompareResult {
	const n = bundles.length;
	const base = bundles[0];
	const baseRows = base?.gridBySection.get(sectionKey) ?? [];
	const indexes = bundles.map(bundleIndex);
	const rows: AlignedRow[] = [];
	let narrOrd = 0;
	for (const r of baseRows) {
		if (r.disclosureKey) {
			// keyed = 회사 간 정렬. 각 회사의 같은 disclosureKey 행을 절번호 무관 전역 조회.
			const key = alignKeyOf(r);
			const cells = indexes.map((idx) => {
				const cell = idx.byAlignKey.get(key)?.cells?.[period];
				return typeof cell === 'string' && cell.trim() !== '' ? cell : null;
			});
			if (cells.every((c) => c == null)) continue; // 이 시점엔 어느 회사도 값 없음
			rows.push({
				alignKey: key,
				label: r.blockLeaf || r.sectionLeaf || r.disclosureKey || '',
				disclosureKey: r.disclosureKey,
				scope: r.scope,
				leafType: rowLeafType(r),
				blockType: r.blockType,
				cells,
				shareClass: shareClass(cells)
			});
		} else {
			// narrative = 키 없음 → 회사 간 정렬 불가, 기준 회사 열만(나머지 honest-gap).
			const baseCell = r.cells?.[period];
			if (typeof baseCell !== 'string' || baseCell.trim() === '') continue;
			const cells = new Array<string | null>(n).fill(null);
			cells[0] = baseCell;
			rows.push({
				alignKey: `NARR${COMPARE_SEP}${base.stockCode}${COMPARE_SEP}${narrOrd++}`,
				label: r.blockLeaf || r.sectionLeaf || '',
				disclosureKey: null,
				scope: r.scope,
				leafType: rowLeafType(r),
				blockType: r.blockType,
				cells,
				shareClass: shareClass(cells)
			});
		}
	}
	const sharedRows = rows.filter((r) => r.shareClass === 'shared').length;
	const partialRows = rows.filter((r) => r.shareClass === 'partial').length;
	return {
		rows,
		diagnostics: {
			mode: 'row',
			period,
			rowCount: rows.length,
			sharedRows,
			partialRows,
			soloRows: rows.length - sharedRows - partialRows,
			narrativePolicy: 'company-row'
		}
	};
}

// Section presence bits for TOC dots/gray-out — a company "has" the base section if it
// carries any of the section's disclosureKeys anywhere (절번호 무관). Narrative-only
// section → base company only.
export function sectionPresence(bundles: PanelBundle[], sectionKey: string): boolean[] {
	const base = bundles[0];
	const baseRows = base?.gridBySection.get(sectionKey) ?? [];
	const keys = new Set(baseRows.filter((r) => r.disclosureKey).map(alignKeyOf));
	if (!keys.size) return bundles.map((b) => b === base);
	return bundles.map((b) => {
		const idx = bundleIndex(b);
		for (const k of keys) if (idx.byAlignKey.has(k)) return true;
		return false;
	});
}

// Common periods, latest first. Uses intersection first, then union fallback.
export function commonPeriods(bundles: PanelBundle[]): string[] {
	if (!bundles.length) return [];
	const sets = bundles.map((b) => new Set(b.periods));
	const inter = bundles[0].periods.filter((p) => sets.every((s) => s.has(p)));
	if (inter.length) return inter;
	const union = new Set<string>();
	for (const b of bundles) for (const p of b.periods) union.add(p);
	return [...union].sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));
}
