// Per-bundle global disclosure-key index — lets compare align by disclosureKey across
// companies regardless of TOC section number (삼성 "7.유형자산" ↔ SK "11.유형자산"),
// mirroring Python compare's (disclosureKey, scope, leafType) whole-panel alignment.
//
// Without this, fetching other companies' rows by the base company's drift-prone
// sectionKey (`${chapter}␟${sectionLeaf}`, sectionLeaf carries the 절번호) returned the
// wrong/empty section — the "TOC 클릭 시 이상한 비교" bug. The base company drives WHICH
// rows show (same TOC); other companies' cells come from this global lookup.

import type { PanelBundle, PanelRow } from '../types';
import { COMPARE_SEP } from './types';

export function rowLeafType(r: PanelRow): string {
	return r.leafType || r.blockType || '';
}

// Python compare.py keyed identity: (disclosureKey, scope, leafType).
export function alignKeyOf(r: PanelRow): string {
	return `${r.disclosureKey}${COMPARE_SEP}${r.scope ?? ''}${COMPARE_SEP}${rowLeafType(r)}`;
}

interface BundleIndex {
	byAlignKey: Map<string, PanelRow>; // dk␟scope␟leafType → first row (row-mode global align)
	byDisclosureKey: Map<string, PanelRow[]>; // dk → all rows (finance statement gather)
}

const cache = new WeakMap<PanelBundle, BundleIndex>();

function buildIndex(b: PanelBundle): BundleIndex {
	const byAlignKey = new Map<string, PanelRow>();
	const byDisclosureKey = new Map<string, PanelRow[]>();
	for (const rows of b.gridBySection.values()) {
		for (const r of rows) {
			if (!r.disclosureKey) continue; // narrative 행은 키 정렬 불가
			const ak = alignKeyOf(r);
			if (!byAlignKey.has(ak)) byAlignKey.set(ak, r); // 첫 등장 = 최신 filing (상류 dedup)
			let arr = byDisclosureKey.get(r.disclosureKey);
			if (!arr) byDisclosureKey.set(r.disclosureKey, (arr = []));
			arr.push(r);
		}
	}
	return { byAlignKey, byDisclosureKey };
}

export function bundleIndex(b: PanelBundle): BundleIndex {
	let idx = cache.get(b);
	if (!idx) cache.set(b, (idx = buildIndex(b)));
	return idx;
}

// All rows across sections whose disclosureKey is one of the given statements — finance
// compare gathers a company's whole BS/IS/CF regardless of section number.
export function rowsForStatements(b: PanelBundle, statements: Set<string>): PanelRow[] {
	if (!statements.size) return [];
	const idx = bundleIndex(b);
	const out: PanelRow[] = [];
	for (const dk of statements) {
		const arr = idx.byDisclosureKey.get(dk);
		if (arr) out.push(...arr);
	}
	return out;
}
