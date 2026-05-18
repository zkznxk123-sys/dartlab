// kind=matrix → heatmap. 다기간 × 다지표 격자.
// 자체 div grid + bg color (recharts 없음).

import { cn } from '@/lib/utils';

interface MatrixCell {
	row: string;       // 행 label (지표)
	col: string;       // 열 label (기간)
	value: number | null;
	unit?: string;
}

interface Props {
	cells: MatrixCell[];
	rowOrder?: string[];
	colOrder?: string[];
	tone?: 'sequential' | 'diverging';   // 색 스케일
	minValue?: number;
	maxValue?: number;
	height?: number;
}

function fmt(v: number | null, unit?: string): string {
	if (v == null || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(1);
	if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0);
	if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
	return v.toFixed(1);
}

function tonePct(v: number | null, min: number, max: number): number {
	if (v == null || !Number.isFinite(v)) return 0;
	return Math.max(0, Math.min(1, (v - min) / (max - min || 1)));
}

export function HeatmapChart({ cells, rowOrder, colOrder, tone = 'sequential', minValue, maxValue, height }: Props) {
	const rows = rowOrder ?? [...new Set(cells.map((c) => c.row))];
	const cols = colOrder ?? [...new Set(cells.map((c) => c.col))];
	const values = cells.map((c) => c.value).filter((v): v is number => v != null && Number.isFinite(v));
	const lo = minValue ?? (values.length ? Math.min(...values) : 0);
	const hi = maxValue ?? (values.length ? Math.max(...values) : 1);
	const lookup = new Map<string, MatrixCell>();
	for (const c of cells) lookup.set(`${c.row}|${c.col}`, c);
	return (
		<div
			className="flex h-full w-full items-center justify-center overflow-auto px-2"
			style={height ? { height } : undefined}
		>
			<table className="h-full w-full border-separate" style={{ borderSpacing: 2 }}>
				<thead>
					<tr>
						<th className="text-left text-xs font-normal text-muted-foreground" />
						{cols.map((c) => (
							<th key={c} className="px-1 text-center text-xs font-normal text-muted-foreground">{c}</th>
						))}
					</tr>
				</thead>
				<tbody>
					{rows.map((r) => (
						<tr key={r}>
							<td className="whitespace-nowrap pr-2 text-right text-xs text-muted-foreground">{r}</td>
							{cols.map((c) => {
								const cell = lookup.get(`${r}|${c}`);
								const pct = tonePct(cell?.value ?? null, lo, hi);
								const bg = tone === 'sequential'
									? `color-mix(in oklch, var(--chart-1) ${Math.round(pct * 80)}%, var(--card))`
									: `color-mix(in oklch, ${pct > 0.5 ? 'var(--chart-5)' : 'var(--chart-3)'} ${Math.round(Math.abs(pct - 0.5) * 160)}%, var(--card))`;
								return (
									<td
										key={c}
										className={cn('rounded text-center font-mono text-xs tabular-nums')}
										style={{ background: bg, minWidth: 40, padding: '4px 6px' }}
										title={cell ? `${r} · ${c}: ${cell.value} ${cell.unit ?? ''}` : ''}
									>
										{fmt(cell?.value ?? null, cell?.unit)}
									</td>
								);
							})}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
