// kind=kpiTile — 큰 숫자 + 보조 sparkline + 전기 대비 delta.
// 단일 메트릭 강조 카드.

import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

import { cn } from '@/lib/utils';

interface KpiTileProps {
	value: number | string | null | undefined;
	unit?: string;
	label?: string;
	deltaPct?: number | null;        // 전기 대비 % 변화 (선택)
	deltaAbs?: number | null;        // 전기 대비 절대 변화
	subtitle?: string;
	tone?: 'positive' | 'negative' | 'neutral';
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

export function KpiTile({ value, unit, label, deltaPct, deltaAbs, subtitle, tone = 'neutral' }: KpiTileProps) {
	const displayValue = typeof value === 'number' ? formatBigNumber(value) : (value ?? '–');
	const positive = (deltaPct ?? 0) > 0;
	const negative = (deltaPct ?? 0) < 0;
	const toneClass =
		tone === 'positive'
			? 'text-[var(--chart-5)]'
			: tone === 'negative'
				? 'text-[var(--chart-3)]'
				: 'text-foreground';
	return (
		<div className="flex h-full w-full flex-col justify-center gap-1.5 px-4">
			{label && <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>}
			<div className={cn('flex items-baseline gap-1.5 tabular-nums', toneClass)}>
				<span className="text-4xl font-semibold leading-none">{displayValue}</span>
				{unit && (
					<span className="text-lg font-normal text-muted-foreground">{unit}</span>
				)}
			</div>
			{(deltaPct != null || deltaAbs != null) && (
				<div className="flex items-center gap-1.5 text-sm text-muted-foreground">
					{positive ? (
						<TrendingUp className="size-3.5 text-[var(--chart-5)]" />
					) : negative ? (
						<TrendingDown className="size-3.5 text-[var(--chart-3)]" />
					) : (
						<Minus className="size-3.5" />
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
	);
}
