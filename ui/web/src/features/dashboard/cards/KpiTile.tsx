// kind=kpiTile — 큰 숫자 + 보조 sparkline + 전기 대비 delta.
// 단일 메트릭 강조 카드. P-DASH-V1 D11: 우측 sparkline + 하단 range bar.

import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

import { Sparkline } from '@/features/dashboard/cards/Sparkline';
import { cn } from '@/lib/utils';

interface KpiTileProps {
	value: number | string | null | undefined;
	unit?: string;
	label?: string;
	deltaPct?: number | null;
	deltaAbs?: number | null;
	subtitle?: string;
	tone?: 'positive' | 'negative' | 'neutral';
	sparkline?: number[];
	rangeMin?: number | null;
	rangeMax?: number | null;
}

function formatBigNumber(v: unknown): string {
	if (v == null || typeof v !== 'number' || !Number.isFinite(v)) return '–';
	const abs = Math.abs(v);
	if (abs >= 1e12) {
		const t = v / 1e12;
		return (Math.abs(t) >= 10 ? Math.round(t).toLocaleString() : t.toFixed(1)) + '조';
	}
	if (abs >= 1e8) {
		const e = v / 1e8;
		return (Math.abs(e) >= 100 ? Math.round(e).toLocaleString() : e.toFixed(1)) + '억';
	}
	if (abs >= 1000) return v.toLocaleString();
	if (Number.isInteger(v)) return v.toString();
	return v.toFixed(2);
}

export function KpiTile({
	value,
	unit,
	label,
	deltaPct,
	deltaAbs,
	subtitle,
	tone = 'neutral',
	sparkline,
	rangeMin,
	rangeMax,
}: KpiTileProps) {
	const displayValue = typeof value === 'number' ? formatBigNumber(value) : (value ?? '–');
	const positive = (deltaPct ?? 0) > 0;
	const negative = (deltaPct ?? 0) < 0;
	const toneClass =
		tone === 'positive'
			? 'text-[var(--chart-5)]'
			: tone === 'negative'
				? 'text-[var(--chart-3)]'
				: 'text-foreground';
	const sparkColor =
		tone === 'positive'
			? 'var(--chart-5)'
			: tone === 'negative'
				? 'var(--chart-3)'
				: 'var(--chart-1)';

	// range bar dot position (0~1).
	const numericValue = typeof value === 'number' ? value : null;
	const rangePos =
		numericValue != null && rangeMin != null && rangeMax != null && rangeMax > rangeMin
			? Math.max(0, Math.min(1, (numericValue - rangeMin) / (rangeMax - rangeMin)))
			: null;

	return (
		<div className="flex h-full w-full flex-col justify-between gap-1 px-4 py-3">
			{/* row 1: label + sparkline */}
			<div className="flex items-start justify-between gap-2">
				{label && (
					<div className="text-xs uppercase tracking-wide text-muted-foreground truncate">
						{label}
					</div>
				)}
				{sparkline && sparkline.length >= 2 && (
					<Sparkline data={sparkline} color={sparkColor} height={28} width={70} />
				)}
			</div>

			{/* row 2: value + delta */}
			<div className="flex flex-col gap-0.5">
				<div className={cn('flex items-baseline gap-1.5 tabular-nums', toneClass)}>
					<span className="text-3xl font-semibold leading-none">{displayValue}</span>
					{unit && <span className="text-base font-normal text-muted-foreground">{unit}</span>}
				</div>
				{(deltaPct != null || deltaAbs != null) && (
					<div className="flex items-center gap-1 text-xs text-muted-foreground">
						{positive ? (
							<TrendingUp className="size-3 text-[var(--chart-5)]" />
						) : negative ? (
							<TrendingDown className="size-3 text-[var(--chart-3)]" />
						) : (
							<Minus className="size-3" />
						)}
						{deltaPct != null && (
							<span
								className={cn(
									'font-medium',
									positive && 'text-[var(--chart-5)]',
									negative && 'text-[var(--chart-3)]',
								)}
							>
								{deltaPct > 0 ? '+' : ''}
								{deltaPct.toFixed(1)}%
							</span>
						)}
						{deltaAbs != null && (
							<span className="text-xs text-muted-foreground">
								({deltaAbs > 0 ? '+' : ''}
								{formatBigNumber(deltaAbs)})
							</span>
						)}
					</div>
				)}
				{subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
			</div>

			{/* row 3: percentile range bar */}
			{rangePos != null && (
				<div className="flex flex-col gap-0.5">
					<div className="relative h-1 w-full overflow-hidden rounded-full bg-muted">
						<div
							className="absolute top-0 h-full w-1.5 -translate-x-1/2 rounded-full"
							style={{ left: `${rangePos * 100}%`, background: sparkColor }}
						/>
					</div>
					<div className="flex justify-between text-[11px] text-muted-foreground tabular-nums leading-tight">
						<span>5y 최저</span>
						<span>5y 최고</span>
					</div>
				</div>
			)}
		</div>
	);
}
