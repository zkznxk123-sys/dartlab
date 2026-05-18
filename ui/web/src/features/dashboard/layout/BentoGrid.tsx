// Bento packed grid — backend Layout Engine 이 산출한 (x, y, w, h) 좌표대로 렌더.
// 시각 정사각 강제: grid-auto-rows = column width. cs=rs 면 시각 정사각.
// 4 col xl + 2 col md + 1 col sm — Tailwind breakpoint 와 동기.

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

import type { PackedCard } from '@/features/dashboard/api/client';

interface Props {
	placed: PackedCard[];
	renderCard: (p: PackedCard, cellSize: number) => ReactNode;
}

const GAP_PX = 8;
const PAD_PX = 12;
// cellSize cap — column width 가 너무 크면 카드 dead space 폭발 (KPI 1×1 이
// 465×465 px). Stripe/Linear/Vercel bento 패턴은 ~130~180px 정사각. 1920px
// 4col 도 카드 정사각 비율 유지하되 크기 cap.
const CELL_CAP_PX = 180;

function columnsFor(viewportWidth: number): number {
	if (viewportWidth >= 1280) return 4;
	if (viewportWidth >= 768) return 2;
	return 1;
}

export function BentoGrid({ placed, renderCard }: Props) {
	const gridRef = useRef<HTMLDivElement>(null);
	const [cellSize, setCellSize] = useState<number>(200);

	useLayoutEffect(() => {
		const el = gridRef.current;
		if (!el) return;

		const measure = () => {
			const cols = columnsFor(window.innerWidth);
			const inner = el.clientWidth - PAD_PX * 2;
			const totalGap = GAP_PX * Math.max(0, cols - 1);
			const raw = Math.floor((inner - totalGap) / cols);
			const cell = Math.max(80, Math.min(CELL_CAP_PX, raw));
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
			className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4"
			style={{
				gap: `${GAP_PX}px`,
				padding: `${PAD_PX}px`,
				gridAutoRows: `${cellSize}px`,
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
