// 회사 간 정렬 — Python `panel.compare` 의 join 로직 브라우저 미러 (파생 artifact 0).
// 한 섹션의 PanelRow[] 를 N 개 회사에 걸쳐 정렬키로 outer-align.
//
// 정렬키: keyed = disclosureKey␟scope␟blockType (era-stable, 보고서-로컬 라벨/번호 drift 자동 해소).
//   narrative(disclosureKey null) = 회사·행 고유(절대 병합 안 됨 — 행단위 강제정렬은 거짓 1:1 = 금지).
// scope 가 정렬키에 포함돼야 별도-BS ↔ 연결-BS 혼선을 막는다. 한쪽만 있는 행 = honest-gap(null).

import type { PanelBundle, PanelRow } from './types';

const SEP = '␟';

export interface AlignedRow {
	alignKey: string;
	label: string; // 좌측 거터 라벨 = blockLeaf || sectionLeaf || disclosureKey
	disclosureKey: string | null;
	scope: string | null;
	blockType: 'text' | 'table';
	cells: (string | null)[]; // 회사 index → 그 시점 셀 본문 (null = 해당 공시 없음 = honest-gap)
	shareClass: 'shared' | 'partial' | 'solo';
}

// 정렬키 — keyed = disclosureKey␟scope␟blockType (회사 간 era-stable). narrative(키 부재) = 섹션 내
// content-bearing 위치 ordinal — 한 회사의 k 번째 서술 행이 다른 회사의 k 번째와 한 행에 정렬(항목=행).
// (단일 뷰어의 기간축 정렬이 회사축으로 바뀐 것 — 사용자 멘탈모델. 서술은 위치 best-effort, keyed 는 exact.)
function alignKeyOf(r: PanelRow, narrOrd: number): string {
	if (r.disclosureKey) return `${r.disclosureKey}${SEP}${r.scope ?? ''}${SEP}${r.blockType}`;
	return `NARR${SEP}${narrOrd}`;
}

// N 개 bundle 의 한 섹션을 시점(period) 기준으로 정렬. content-bearing(비빈 셀)만, union 행수.
export function alignBundles(bundles: PanelBundle[], sectionKey: string, period: string): AlignedRow[] {
	const n = bundles.length;
	const groups = new Map<string, AlignedRow>();
	const order: string[] = [];
	bundles.forEach((b, ci) => {
		const rows = b.gridBySection.get(sectionKey) ?? [];
		let narrOrd = 0; // 이 회사 섹션 내 content-bearing 서술 행 순번
		rows.forEach((r) => {
			const cell = r.cells?.[period];
			if (typeof cell !== 'string' || cell.trim() === '') return; // 빈 셀 제외 (착시 차단)
			const key = alignKeyOf(r, narrOrd);
			if (!r.disclosureKey) narrOrd++;
			let g = groups.get(key);
			if (!g) {
				g = {
					alignKey: key,
					label: r.blockLeaf || r.sectionLeaf || r.disclosureKey || '',
					disclosureKey: r.disclosureKey,
					scope: r.scope,
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
	for (const g of groups.values()) {
		const present = g.cells.filter((c) => c != null).length;
		g.shareClass = present >= n ? 'shared' : present > 1 ? 'partial' : 'solo';
	}
	return order.map((k) => groups.get(k)!);
}

// 섹션별 회사 존재 비트 (TOC 존재 도트·gray-out). bundles[ci] 가 그 sectionKey 본문을 갖는가.
export function sectionPresence(bundles: PanelBundle[], sectionKey: string): boolean[] {
	return bundles.map((b) => (b.gridBySection.get(sectionKey)?.length ?? 0) > 0);
}

// N 개 회사 공통 기간 (최신순). 시점 비교의 기본 후보 — 교집합, 없으면 union.
export function commonPeriods(bundles: PanelBundle[]): string[] {
	if (!bundles.length) return [];
	const sets = bundles.map((b) => new Set(b.periods));
	const inter = bundles[0].periods.filter((p) => sets.every((s) => s.has(p)));
	if (inter.length) return inter; // 이미 최신순(periods SSOT)
	const union = new Set<string>();
	for (const b of bundles) for (const p of b.periods) union.add(p);
	return [...union].sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));
}
