// 셀 diff / 행 식별 순수 헬퍼 — ui/web `analysis.$code.viewer.tsx` 1:1 포팅.
// diff/timeline 은 프론트 인접셀 비교 (백엔드 계산 0).

import type { PanelRow } from './types';

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
