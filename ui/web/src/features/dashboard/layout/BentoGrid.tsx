// 12-col bento 2026 grid (v3-r7) — backend planTabLayout(colCount=12) 좌표.
// cellSize ≈ 113px (viewport 1700 sidebar 240 기준, gap 16 padding 24).
// 핵심: cellHeight === cellWidth 동기화 → w === h 면 자동 1:1 정사각.
// gridstack.js 미도입 (정적 grid, 드래그 X). CSS grid 만으로 동일 효과 + bundle 추가 0.

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

import type { PackedCard } from '@/features/dashboard/api/client';

interface Props {
	placed: PackedCard[];
	renderCard: (p: PackedCard, cellSize: number) => ReactNode;
}

// SSOT — TabDashboard / financial.$code.tsx 픽셀 산출식이 동일 상수 사용.
// bento 2026 §4 기본 gap/padding 16/24 에서 정보 밀도 우선으로 10/12 로 축소.
// 카드 사이 6px·좌우 12px 절약 → cellSize 동기 증가, 한 viewport 정보량 ↑.
export const BENTO_GAP_PX = 10;
export const BENTO_PAD_PX = 12;
export const BENTO_COL_COUNT = 12;
export const BENTO_MIN_CELL_PX = 80;
// CardShell chrome — CardHeader h-[26px] + border 1, CardContent pt 4 + pb 4.
export const BENTO_CARD_HEADER_PX = 27;
export const BENTO_CARD_PAD_PX = 8;

const GAP_PX = BENTO_GAP_PX;
const PAD_PX = BENTO_PAD_PX;
const COL_COUNT = BENTO_COL_COUNT;
const MIN_CELL_PX = BENTO_MIN_CELL_PX;

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
			{placed.map((p) => {
				// content-visibility: auto — 화면 밖 cell 의 layout/style/paint 자체 skip.
				// 8~12 Recharts SVG 동시 mount 가 main thread 점유하던 비용 차단. `auto`
				// prefix 의 containIntrinsicSize 는 카드가 한 번 표시된 뒤엔 실측 size 를
				// 기억해 스크롤 점프 차단. 첫 진입 전 placeholder size 는 셀 계산식 그대로.
				const cellOuterH = p.h * cellSize + (p.h - 1) * GAP_PX;
				return (
					<div
						key={p.cardKey}
						className="min-w-0"
						style={{
							gridColumn: `span ${p.w} / span ${p.w}`,
							gridRow: `span ${p.h} / span ${p.h}`,
							contentVisibility: 'auto',
							containIntrinsicSize: `auto ${cellOuterH}px`,
						}}
					>
						{renderCard(p, cellSize)}
					</div>
				);
			})}
		</div>
	);
}
