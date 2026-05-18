// 12-col gridstack 식 bento grid — 백엔드 Layout Engine 의 (x,y,w,h) 좌표 + 12 col 고정.
// 핵심: cellHeight === cellWidth 동기화 → w === h 면 자동 1:1 정사각.
// gridstack.js 미도입 (정적 grid, 드래그 X). CSS grid 만으로 동일 효과 + bundle 추가 0.

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

import type { PackedCard } from '@/features/dashboard/api/client';

interface Props {
	placed: PackedCard[];
	renderCard: (p: PackedCard, cellSize: number) => ReactNode;
}

const GAP_PX = 8;
const PAD_PX = 8;
const COL_COUNT = 12;
const MIN_CELL_PX = 56;

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

	return (
		<div
			ref={gridRef}
			className="grid"
			style={{
				gap: `${GAP_PX}px`,
				padding: `${PAD_PX}px`,
				gridTemplateColumns: `repeat(${COL_COUNT}, ${cellSize}px)`,
				gridAutoRows: `${cellSize}px`,
				justifyContent: 'start',
			}}
		>
			{placed.map((p) => (
				<div
					key={p.cardKey}
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
