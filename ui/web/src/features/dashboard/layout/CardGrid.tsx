// 4 열 bento grid — xl 에서 카드별 colSpan + rowSpan 으로 밀도 packing.
// row 높이 150px 기준 (rowSpan 1 = KPI, 2 = 트렌드, 3 = 차트+표 또는 list).
// gap-3 (12px) — 카드 간격 컴팩트.

import type { ReactNode } from 'react';

export function CardGrid({ children }: { children: ReactNode }) {
	return (
		<div
			className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2 xl:grid-cols-4"
			style={{ gridAutoRows: '150px' }}
		>
			{children}
		</div>
	);
}
