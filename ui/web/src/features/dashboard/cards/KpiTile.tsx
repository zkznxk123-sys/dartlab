// kind=kpiTile — size 별 layout dispatch.
//
// 카탈로그 size (colSpan × rowSpan) 가 화면 비율과 일치하지 않으면 dead
// space 폭발 (옛 1×1 카드를 rowSpan=2 로 렌더해 justify-between 이 콘텐츠를
// 카드 위·중·아래로 찢었던 회귀). size prop 받아 분기:
//
// - 1×1: 값 + 미니 spark 옆 배치 + delta 한 줄. range bar 없음.
// - 1×2: 값 위, 큰 spark 아래 (카드 폭 전체), range bar 하단.
// - 2×2+: spark 배경 본체 (반투명), 값 + delta 는 좌하단 오버레이.

import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

import { Sparkline } from '@/features/dashboard/cards/Sparkline';
import { cn } from '@/lib/utils';

interface KpiTileProps {
	value: number | string | null | undefined;
	unit?: string;
	label?: string;
	deltaPct?: number | null;
	subtitle?: string;
	tone?: 'positive' | 'negative' | 'neutral';
	sparkline?: number[];
	rangeMin?: number | null;
	rangeMax?: number | null;
	size?: { w: number; h: number };
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
	subtitle,
	tone = 'neutral',
	sparkline,
	rangeMin,
	rangeMax,
	size,
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

	const numericValue = typeof value === 'number' ? value : null;
	const rangePos =
		numericValue != null && rangeMin != null && rangeMax != null && rangeMax > rangeMin
			? Math.max(0, Math.min(1, (numericValue - rangeMin) / (rangeMax - rangeMin)))
			: null;

	const w = size?.w ?? 1;
	const h = size?.h ?? 1;
	const hasSparkline = !!(sparkline && sparkline.length >= 2);
	const deltaIcon = positive ? (
		<TrendingUp className="size-3 text-[var(--chart-5)]" />
	) : negative ? (
		<TrendingDown className="size-3 text-[var(--chart-3)]" />
	) : (
		<Minus className="size-3" />
	);
	const deltaText = deltaPct != null ? `${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%` : null;

	// 24-col 기준 분기 (v3):
	//   가로 와이드 (h <= 2)   : 5×2 본질 — 헤더(label+delta) + 본문(값 좌 / spark 우)
	//   세로 길쭉 (h >= 3)     : 5×3+ — 값 위 hero + spark 큰 + range bar 아래
	//   hero (w >= 12 && h >= 12): radar 자리 (KpiTile 거의 안 옴)

	if (w >= 12 && h >= 12) {
		return (
			<div className="relative flex h-full w-full flex-col px-3 pt-2">
				{label && (
					<div className="text-[10px] uppercase tracking-wide text-muted-foreground truncate">
						{label}
					</div>
				)}
				{hasSparkline && (
					<div className="absolute inset-x-2 bottom-2 top-7 opacity-90 [&_svg]:!h-full [&_svg]:!w-full">
						<Sparkline data={sparkline!} color={sparkColor} height={120} width={400} />
					</div>
				)}
				<div className="relative z-10 mt-auto flex items-baseline gap-1.5 pb-1 tabular-nums">
					<span className={cn('text-3xl font-semibold leading-none', toneClass)}>{displayValue}</span>
					{unit && <span className="text-base text-muted-foreground">{unit}</span>}
				</div>
				{(deltaText || subtitle) && (
					<div className="relative z-10 flex items-center gap-1 pb-2 text-xs text-muted-foreground">
						{deltaIcon}
						{deltaText && (
							<span className={cn('font-medium', positive && 'text-[var(--chart-5)]', negative && 'text-[var(--chart-3)]')}>
								{deltaText}
							</span>
						)}
						{subtitle && <span className="ml-2">{subtitle}</span>}
					</div>
				)}
			</div>
		);
	}

	// 세로 길쭉 (5×3+ = h>=3) — 값 위, 큰 spark + range bar 아래.
	if (h >= 3) {
		return (
			<div className="flex h-full w-full flex-col gap-1 px-2 py-1.5">
				<div className="flex items-start justify-between gap-1">
					{label && (
						<div className="text-[10px] uppercase tracking-wide text-muted-foreground truncate leading-tight">
							{label}
						</div>
					)}
					{deltaText && (
						<div className="flex shrink-0 items-center gap-0.5 text-[10px] leading-tight">
							{deltaIcon}
							<span className={cn('font-medium tabular-nums', positive && 'text-[var(--chart-5)]', negative && 'text-[var(--chart-3)]', !positive && !negative && 'text-muted-foreground')}>
								{deltaText}
							</span>
						</div>
					)}
				</div>
				<div className="flex items-baseline gap-1 tabular-nums">
					<span className={cn('text-3xl font-bold leading-none whitespace-nowrap', toneClass)}>{displayValue}</span>
					{unit && <span className="text-xs text-muted-foreground">{unit}</span>}
				</div>
				{hasSparkline && (
					<div className="flex-1 min-h-0 [&_svg]:!h-full [&_svg]:!w-full">
						<Sparkline data={sparkline!} color={sparkColor} height={80} width={240} />
					</div>
				)}
				{rangePos != null && (
					<div className="flex flex-col gap-0.5">
						<div className="relative h-1 w-full overflow-hidden rounded-full bg-muted">
							<div
								className="absolute top-0 h-full w-1.5 -translate-x-1/2 rounded-full"
								style={{ left: `${rangePos * 100}%`, background: sparkColor }}
							/>
						</div>
						<div className="flex justify-between text-[10px] text-muted-foreground tabular-nums leading-tight">
							<span>5y 최저</span>
							<span>5y 최고</span>
						</div>
					</div>
				)}
			</div>
		);
	}

	// 가로 와이드 (5×2 본질, h <= 2) — KPI 단일 metric 정답 layout:
	// 헤더 (label 좌 + delta 우) + 본문 (값 좌 hero / spark 우 fill)
	// padding 최소 (px-2 py-1.5), 카드 95% 점유, dead 0
	return (
		<div className="grid h-full w-full grid-rows-[auto_1fr] gap-1 px-2 py-1.5">
			<div className="grid grid-cols-[1fr_auto] items-start gap-1">
				{label && (
					<div className="min-w-0 truncate text-[10px] uppercase tracking-wide text-muted-foreground leading-tight">
						{label}
					</div>
				)}
				{deltaText && (
					<div className="flex shrink-0 items-center gap-0.5 text-[10px] leading-tight">
						{deltaIcon}
						<span className={cn('font-medium tabular-nums', positive && 'text-[var(--chart-5)]', negative && 'text-[var(--chart-3)]', !positive && !negative && 'text-muted-foreground')}>
							{deltaText}
						</span>
					</div>
				)}
			</div>
			<div className="grid min-h-0 grid-cols-[1fr_1fr] items-center gap-2">
				<span className={cn('whitespace-nowrap text-2xl font-bold leading-none tabular-nums', toneClass)}>
					{displayValue}
					{unit && <span className="ml-0.5 text-[11px] font-normal text-muted-foreground">{unit}</span>}
				</span>
				{hasSparkline && (
					<div className="h-full min-w-0 [&_svg]:!h-full [&_svg]:!w-full">
						<Sparkline data={sparkline!} color={sparkColor} height={60} width={140} />
					</div>
				)}
			</div>
		</div>
	);
}
