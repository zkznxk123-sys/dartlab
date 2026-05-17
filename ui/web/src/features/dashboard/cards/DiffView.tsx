// kind=diffView — 전년대비 / 분기대비 변화 KPI grid.
// 각 행: 현재값 · 직전값 · % 변화 · 화살표.

import { ArrowDown, ArrowRight, ArrowUp } from 'lucide-react';

import { cn } from '@/lib/utils';

export interface DiffItem {
	label: string;
	current: number | null;
	previous: number | null;
	unit?: string;
}

interface Props {
	items: DiffItem[];
	periodLabel?: string;       // e.g. "YoY" / "QoQ"
}

function fmt(v: number | null, unit?: string): string {
	if (v == null || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(1) + '%';
	if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0) + '억';
	if (Math.abs(v) >= 1000) return v.toLocaleString();
	return v.toFixed(2);
}

export function DiffView({ items, periodLabel = 'YoY' }: Props) {
	return (
		<div className="grid grid-cols-2 gap-2 px-2 sm:grid-cols-3">
			{items.map((it) => {
				const hasBoth = it.current != null && it.previous != null && it.previous !== 0;
				const pct = hasBoth ? ((it.current! - it.previous!) / Math.abs(it.previous!)) * 100 : null;
				const up = (pct ?? 0) > 0.5;
				const down = (pct ?? 0) < -0.5;
				const Icon = up ? ArrowUp : down ? ArrowDown : ArrowRight;
				const toneClass = up
					? 'text-[var(--chart-5)]'
					: down
						? 'text-[var(--chart-3)]'
						: 'text-muted-foreground';
				return (
					<div key={it.label} className="rounded-md border border-dashed p-2">
						<div className="text-xs text-muted-foreground">{it.label}</div>
						<div className="mt-1 flex items-baseline gap-2">
							<span className="text-sm font-semibold tabular-nums">{fmt(it.current, it.unit)}</span>
							{pct != null && (
								<span className={cn('flex items-center gap-0.5 text-xs', toneClass)}>
									<Icon className="size-3" />
									{pct > 0 ? '+' : ''}
									{pct.toFixed(1)}%
								</span>
							)}
						</div>
						{it.previous != null && (
							<div className="mt-0.5 text-[10px] text-muted-foreground">
								{periodLabel} {fmt(it.previous, it.unit)}
							</div>
						)}
					</div>
				);
			})}
		</div>
	);
}
