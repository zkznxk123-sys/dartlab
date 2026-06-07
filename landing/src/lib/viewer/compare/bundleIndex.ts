// Per-bundle disclosureKey index — 절번호 drift(회사마다 같은 공시가 다른 절번호)로 같은
// sectionKey 가 없는 회사를 disclosureKey 로 전역 조회해 비교 누락을 막는다.

import type { PanelBundle, PanelRow } from '../types';

interface BundleIndex {
	byDisclosureKey: Map<string, PanelRow[]>; // dk → all rows across sections
}

const cache = new WeakMap<PanelBundle, BundleIndex>();

function buildIndex(b: PanelBundle): BundleIndex {
	const byDisclosureKey = new Map<string, PanelRow[]>();
	for (const rows of b.gridBySection.values()) {
		for (const r of rows) {
			if (!r.disclosureKey) continue;
			let d = byDisclosureKey.get(r.disclosureKey);
			if (!d) byDisclosureKey.set(r.disclosureKey, (d = []));
			d.push(r);
		}
	}
	return { byDisclosureKey };
}

export function bundleIndex(b: PanelBundle): BundleIndex {
	let idx = cache.get(b);
	if (!idx) cache.set(b, (idx = buildIndex(b)));
	return idx;
}

// 주어진 statement(disclosureKey) 집합에 속하는 전 섹션 행 — finance 셀 렌더(financeCells)가
// 회사의 BS/IS/CF 를 절번호 무관 수집할 때 사용.
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
