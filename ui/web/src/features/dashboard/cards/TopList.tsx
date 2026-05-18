// kind=topList — 상위/하위 N 항목 list + inline bar + 보조 설명.
// 예: 최대 비용 5 / 최악 비율 3 / 변동 큰 지표 top 6.

import { formatValue } from '@/lib/format';
import { cn } from '@/lib/utils';

export interface TopListItem {
	label: string;
	value: number;
	pct?: number;       // 전체 대비 % (0~100)
	unit?: string;      // 항목별 unit
	delta?: number;     // YoY % (음수면 negative tone)
	description?: string; // 한 줄 보조 설명
	tone?: 'positive' | 'negative' | 'neutral';
}

interface Props {
	items: TopListItem[];
	unit?: string;
}

export function TopList({ items, unit: defaultUnit }: Props) {
	const maxAbs = Math.max(...items.map((i) => Math.abs(i.value)), 1);
	return (
		<div className="flex h-full w-full flex-col justify-around gap-2 px-2 py-2">
			{items.map((it, idx) => {
				const w = Math.min(100, (Math.abs(it.value) / maxAbs) * 100);
				const deltaTone =
					it.delta != null
						? it.delta > 1 ? 'negative' : it.delta < -1 ? 'positive' : 'neutral'
						: it.tone ?? 'neutral';
				const barColor =
					deltaTone === 'positive' ? 'bg-[var(--chart-5)]'
					: deltaTone === 'negative' ? 'bg-[var(--chart-3)]'
					: 'bg-[var(--chart-1)]';
				const u = it.unit ?? defaultUnit ?? '';
				return (
					<div key={`${it.label}-${idx}`} className="flex items-start gap-2">
						<div className="w-5 shrink-0 pt-0.5 text-right font-mono text-[11px] text-muted-foreground">
							{idx + 1}
						</div>
						<div className="min-w-0 flex-1">
							<div className="flex items-baseline justify-between gap-2">
								<span className="truncate text-xs">{it.label}</span>
								<span className="shrink-0 font-mono text-xs tabular-nums">
									{formatValue(it.value, u)}
									{it.delta != null && (
										<span className={cn('ml-1.5 text-[10px]',
											deltaTone === 'positive' && 'text-[var(--chart-5)]',
											deltaTone === 'negative' && 'text-[var(--chart-3)]',
										)}>
											{it.delta > 0 ? '+' : ''}{it.delta.toFixed(1)}%
										</span>
									)}
								</span>
							</div>
							<div className="mt-1 h-1 overflow-hidden rounded-full bg-muted">
								<div className={cn('h-full', barColor)} style={{ width: `${w}%` }} />
							</div>
							{it.description && (
								<div className="mt-0.5 line-clamp-1 text-[10px] text-muted-foreground">
									{it.description}
								</div>
							)}
						</div>
					</div>
				);
			})}
		</div>
	);
}
