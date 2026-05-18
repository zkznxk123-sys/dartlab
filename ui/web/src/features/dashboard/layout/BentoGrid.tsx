// 24-col fine grid (v3) — 백엔드 Layout Engine 의 (x,y,w,h) 좌표 + 24 col 고정.
// cellSize ≈ 56px (viewport 1700 sidebar 240 기준).
// 핵심: cellHeight === cellWidth 동기화 → w === h 면 자동 1:1 정사각.
// gridstack.js 미도입 (정적 grid, 드래그 X). CSS grid 만으로 동일 효과 + bundle 추가 0.

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

import type { PackedCard } from '@/features/dashboard/api/client';

interface Props {
	placed: PackedCard[];
	renderCard: (p: PackedCard, cellSize: number) => ReactNode;
}

const GAP_PX = 4;
const PAD_PX = 8;
const COL_COUNT = 24;
const MIN_CELL_PX = 40;

export function BentoGrid({ placed, renderCard }: Props) {
	const gridRef = useRef<HTMLDivElement>(null);
	const [cellSize, setCellSize] = useState<number>(80);

	useLayoutEffect(() => {
		const el = gridRef.current;
		if (!el) return;

		const measure = () => {
			const inner = el.clientWidth - PAD_PX * 2;
			const totalGap = GAP_PX * (COL_COUNT - 1);
			const raw = Math.floor((inner - totalGap) / COL_COUNT);
			const cell = Math.max(MIN_CELL_PX, raw);
			setCellSize((prev) => (prev === cell ? prev : cell));
		};

		measure();
		const raf = requestAnimationFrame(measure);
		const ro = new ResizeObserver(measure);
		ro.observe(el);
		window.addEventListener('resize', measure);
		return () => {
			cancelAnimationFrame(raf);
			ro.disconnect();
			window.removeEventListener('resize', measure);
		};
	}, []);

	// columns 은 minmax(0, 1fr) 유연 분배 — 컨테이너 폭 넘어 수평스크롤 절대 X.
	// rows 만 실측한 cellSize 로 동기 → cs===rs 이면 자동 1:1 정사각.
	return (
		<div
			ref={gridRef}
			className="grid w-full max-w-full"
			style={{
				gap: `${GAP_PX}px`,
				padding: `${PAD_PX}px`,
				gridTemplateColumns: `repeat(${COL_COUNT}, minmax(0, 1fr))`,
				gridAutoRows: `${cellSize}px`,
			}}
		>
			{placed.map((p) => (
				<div
					key={p.cardKey}
					className="min-w-0"
					style={{
						gridColumn: `span ${p.w} / span ${p.w}`,
						gridRow: `span ${p.h} / span ${p.h}`,
					}}
				>
					{renderCard(p, cellSize)}
				</div>
			))}
		</div>
	);
}
