// Row-mode company compare — browser mirror of Python `panel.compare` row identity.
// Keyed rows align by (disclosureKey, scope, leafType); narrative rows are company-row local.

import type { PanelBundle, PanelRow } from '../types';
import { COMPARE_SEP, type AlignedRow, type CompareDiagnostics } from './types';

function shareClass(cells: (string | null)[]): 'shared' | 'partial' | 'solo' {
	const present = cells.filter((c) => c != null).length;
	return present >= cells.length ? 'shared' : present > 1 ? 'partial' : 'solo';
}

function rowLeafType(r: PanelRow): string {
	return r.leafType || r.blockType || '';
}

// Python compare.py: keyed=(disclosureKey, scope, leafType); narrative=NARR␟{code}␟{rowIndex}.
function alignKeyOf(bundle: PanelBundle, r: PanelRow, narrOrd: number): string {
	if (r.disclosureKey) return `${r.disclosureKey}${COMPARE_SEP}${r.scope ?? ''}${COMPARE_SEP}${rowLeafType(r)}`;
	return `NARR${COMPARE_SEP}${bundle.stockCode}${COMPARE_SEP}${narrOrd}`;
}

export interface RowCompareResult {
	rows: AlignedRow[];
	diagnostics: CompareDiagnostics;
}

// N bundle section at one period. Content-bearing rows only; null cells mean honest-gap.
export function alignBundles(bundles: PanelBundle[], sectionKey: string, period: string): AlignedRow[] {
	return compareRows(bundles, sectionKey, period).rows;
}

export function compareRows(bundles: PanelBundle[], sectionKey: string, period: string): RowCompareResult {
	const n = bundles.length;
	const groups = new Map<string, AlignedRow>();
	const order: string[] = [];
	bundles.forEach((b, ci) => {
		const rows = b.gridBySection.get(sectionKey) ?? [];
		let narrOrd = 0;
		rows.forEach((r) => {
			const cell = r.cells?.[period];
			if (typeof cell !== 'string' || cell.trim() === '') return;
			const key = alignKeyOf(b, r, narrOrd);
			if (!r.disclosureKey) narrOrd++;
			let g = groups.get(key);
			if (!g) {
				g = {
					alignKey: key,
					label: r.blockLeaf || r.sectionLeaf || r.disclosureKey || '',
					disclosureKey: r.disclosureKey,
					scope: r.scope,
					leafType: rowLeafType(r),
					blockType: r.blockType,
					cells: new Array(n).fill(null),
					shareClass: 'solo'
				};
				groups.set(key, g);
				order.push(key);
			}
			g.cells[ci] = cell;
		});
	});
	const rows = order.map((k) => {
		const g = groups.get(k)!;
		g.shareClass = shareClass(g.cells);
		return g;
	});
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

// Section presence bits for TOC dots/gray-out.
export function sectionPresence(bundles: PanelBundle[], sectionKey: string): boolean[] {
	return bundles.map((b) => (b.gridBySection.get(sectionKey)?.length ?? 0) > 0);
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
