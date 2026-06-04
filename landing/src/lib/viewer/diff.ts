// 셀 diff / 행 식별 순수 헬퍼 — ui/web `analysis.$code.viewer.tsx` 1:1 포팅.
// diff/timeline 은 프론트 인접셀 비교 (백엔드 계산 0).

import type { PanelRow } from './types';

export const SECTION_KEY_SEP = '␟';

// 인접 period 셀 비교 → 같음/변경/신규. allPeriods 는 fetch window(+1) 로 직전 period 조회.
export function cellStatus(row: PanelRow, period: string, allPeriods: string[]): 'new' | 'changed' | 'same' {
	const cur = (row.cells[period] ?? '').trim();
	if (!cur) return 'same';
	const idx = allPeriods.indexOf(period);
	const prevP = idx >= 0 ? allPeriods[idx + 1] : undefined;
	const prev = prevP ? (row.cells[prevP] ?? '').trim() : '';
	if (!prev) return 'new';
	return cur !== prev ? 'changed' : 'same';
}

// 행 유니크 키 — disclosureKey(구조화) 또는 NARR:: 식별(서술). Python rowIdentity 와 동일 식별축.
export function rowKey(r: PanelRow): string {
	const id = r.disclosureKey ?? `NARR::${r.chapter}${SECTION_KEY_SEP}${r.sectionLeaf}${SECTION_KEY_SEP}${r.blockLeaf}`;
	return `${id}|${r.scope ?? ''}`;
}

// 레일 라벨 = 사용자가 탐색하는 항목 축 = blockLeaf (TOC chip 과 동일).
export function rowLabel(r: PanelRow): string {
	return r.blockLeaf || '';
}

// row 가 visible window 안에 본문이 하나라도 있을 때만 렌더 (옛 기간 ghost row 차단).
export function hasVisibleContent(row: PanelRow, windowPeriods: string[]): boolean {
	for (const p of windowPeriods) {
		const v = row.cells?.[p];
		if (typeof v === 'string' && v.trim().length > 0) return true;
	}
	return false;
}
