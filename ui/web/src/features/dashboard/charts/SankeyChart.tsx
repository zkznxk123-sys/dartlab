// kind=sankey — recharts Sankey 래퍼. 매출 → 비용 → 이익 흐름.
// nodes: [{name}], links: [{source, target, value}].

import { Sankey, Tooltip } from 'recharts';

import { ChartContainer, type ChartConfig } from '@/components/ui/chart';

interface SankeyNode {
	name: string;
}
interface SankeyLink {
	source: number;
	target: number;
	value: number;
}

interface Props {
	nodes: SankeyNode[];
	links: SankeyLink[];
	height?: number;
}

function fmtValue(v: number): string {
	if (!Number.isFinite(v)) return '–';
	if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0) + '억';
	if (Math.abs(v) >= 1000) return v.toLocaleString();
	return v.toFixed(0);
}

export function SankeyChart({ nodes, links, height = 280 }: Props) {
	if (!nodes.length || !links.length) {
		return (
			<div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
				Sankey 데이터 없음
			</div>
		);
	}
	const data = { nodes: nodes.map((n) => ({ name: n.name })), links };
	const config: ChartConfig = {};
	return (
		<ChartContainer config={config} className="!aspect-auto w-full" style={{ height }}>
			<Sankey
				data={data}
				nodePadding={12}
				node={{ fill: 'var(--chart-1)', stroke: 'var(--chart-1)' } as never}
				link={{ stroke: 'var(--chart-4)', strokeOpacity: 0.4 } as never}
				margin={{ left: 8, right: 8, top: 8, bottom: 8 }}
			>
				<Tooltip
					formatter={(v) => (typeof v === 'number' ? fmtValue(v) : String(v ?? '–'))}
					contentStyle={{
						backgroundColor: 'var(--popover)',
						border: '1px solid var(--border)',
						borderRadius: 6,
						fontSize: 12,
					}}
				/>
			</Sankey>
		</ChartContainer>
	);
}
