// 차트 카드 하단 mini-table — 시리즈별 마지막 4 기간 값.
// 차트의 axis 단위 + 범례 색 + period 라벨 모두 일치하도록 동일 헬퍼 사용.

import { formatValue } from '@/lib/format';
import { applyShadcnPalette } from '../charts/palette';
import { makePeriodFormatter } from '../charts/period';
import type { RechartsSpec } from '../api/client';

interface Props {
	spec: RechartsSpec;
	maxPeriods?: number;
}

export function ChartMiniTable({ spec: rawSpec, maxPeriods = 4 }: Props) {
	if (rawSpec.kind !== 'trend' || !rawSpec.categories?.length || !rawSpec.series?.length) return null;
	// 차트와 동일한 색·단위 보장 — palette 적용 후 사용.
	const spec = applyShadcnPalette(rawSpec);
	const fmtPeriod = makePeriodFormatter(spec.categories);
	const allPeriods = spec.categories;
	const periods = allPeriods.slice(-maxPeriods);
	const startIdx = allPeriods.length - periods.length;

	return (
		<div className="overflow-x-auto">
			<table className="w-full text-[11px] tabular-nums">
				<thead>
					<tr className="text-muted-foreground">
						<th className="py-0.5 pr-2 text-left font-normal">지표</th>
						{periods.map((p) => (
							<th key={p} className="py-0.5 px-1 text-right font-normal">
								{fmtPeriod(p)}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{spec.series.map((s) => (
						<tr key={s.key} className="border-t border-border/40">
							<td className="py-0.5 pr-2 text-left">
								<span
									className="inline-block size-2 rounded-sm align-middle"
									style={{ background: s.color }}
								/>
								<span className="ml-1.5 align-middle">{s.label}</span>
							</td>
							{periods.map((_, i) => {
								const v = s.data[startIdx + i] ?? null;
								return (
									<td key={i} className="py-0.5 px-1 text-right text-foreground">
										{formatValue(v, s.unit)}
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
