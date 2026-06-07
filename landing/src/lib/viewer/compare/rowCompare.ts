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

// Base (bundles[0]) section defines the rows in TOC order. Keyed rows (disclosureKey) align
// across companies by (disclosureKey, scope, leafType) — 절번호 무관 전역 조회. Narrative rows
// (no key) are NOT row-aligned across companies: 회사마다 서술 구조가 달라(삼성 '법적명칭' vs
// SK '종속회사개황') 위치 정렬은 거짓 비교가 된다(실데이터 확인). 대신 각 회사의 섹션 서술을
// 자기 열에 통으로 모아 한 행으로 — 나란히 읽되 거짓 1:1 주장 없음.
export function compareRows(bundles: PanelBundle[], sectionKey: string, period: string): RowCompareResult {
	const base = bundles[0];
	const baseRows = base?.gridBySection.get(sectionKey) ?? [];
	const indexes = bundles.map(bundleIndex);
	// 각 회사의 이 섹션 narrative(키 없음) 셀을 통합 — 회사=열, 한 셀에 그 회사 서술 전체.
	const narrCells = bundles.map((b) => {
		const joined = (b.gridBySection.get(sectionKey) ?? [])
			.filter((r) => !r.disclosureKey)
			.map((r) => r.cells?.[period])
			.filter((c): c is string => typeof c === 'string' && c.trim() !== '')
			.join('\n');
		return joined !== '' ? joined : null;
	});
	const hasNarr = narrCells.some((c) => c != null);
	const rows: AlignedRow[] = [];
	let narrPlaced = false;
	const placeNarr = (label: string) => {
		if (narrPlaced || !hasNarr) return;
		narrPlaced = true;
		rows.push({ alignKey: `NARR${COMPARE_SEP}${sectionKey}`, label, disclosureKey: null, scope: null, leafType: 'text', blockType: 'text', cells: narrCells, shareClass: shareClass(narrCells) });
	};
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
			// 첫 서술 위치에 통합 서술 행 1회(기준 TOC 순서 보존 — 보통 서술이 표보다 앞).
			placeNarr(r.sectionLeaf || '');
		}
	}
	placeNarr(''); // baseRows 에 서술 없어도 비기준 회사 서술 있으면 보존
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
