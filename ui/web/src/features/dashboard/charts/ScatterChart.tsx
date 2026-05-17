// kind=scatter — 사분면 산점. ROE × 부채비율 quadrant 등.
// series 별 (x, y) 페어. 회사 본인은 별표 표시 (selfKey).

import {
	CartesianGrid,
	ReferenceLine,
	Scatter,
	ScatterChart as RechartsScatter,
	XAxis,
	YAxis,
	Tooltip,
} from 'recharts';

import { ChartContainer, type ChartConfig } from '@/components/ui/chart';

export interface ScatterPoint {
	x: number;
	y: number;
	label: string;
	self?: boolean;     // 회사 본인 표식
}

interface Props {
	points: ScatterPoint[];
	xLabel?: string;
	yLabel?: string;
	xUnit?: string;
	yUnit?: string;
	xRef?: number;      // 수직 참조선 (예: 산업 평균 ROE)
	yRef?: number;      // 수평 참조선
	height?: number;
}

function fmt(v: unknown, unit?: string): string {
	if (typeof v !== 'number' || !Number.isFinite(v)) return '–';
	if (unit === '%') return v.toFixed(1) + '%';
	if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + '조';
	if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(0) + '억';
	return v.toFixed(2);
}

export function ScatterChart({ points, xLabel, yLabel, xUnit, yUnit, xRef, yRef, height = 280 }: Props) {
	const selfPoints = points.filter((p) => p.self);
	const peerPoints = points.filter((p) => !p.self);
	const config: ChartConfig = {
		peers: { label: '동종', color: 'var(--chart-4)' },
		self: { label: '회사', color: 'var(--chart-1)' },
	};
	return (
		<ChartContainer config={config} className="!aspect-auto w-full" style={{ height }}>
			<RechartsScatter margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
				<CartesianGrid strokeDasharray="3 3" />
				<XAxis
					type="number"
					dataKey="x"
					name={xLabel}
					tickFormatter={(v) => fmt(v, xUnit)}
					tickLine={false}
					axisLine={false}
					fontSize={10}
				/>
				<YAxis
					type="number"
					dataKey="y"
					name={yLabel}
					tickFormatter={(v) => fmt(v, yUnit)}
					tickLine={false}
					axisLine={false}
					fontSize={10}
					width={48}
				/>
				{xRef != null && <ReferenceLine x={xRef} stroke="var(--muted-foreground)" strokeDasharray="4 4" />}
				{yRef != null && <ReferenceLine y={yRef} stroke="var(--muted-foreground)" strokeDasharray="4 4" />}
				<Tooltip
					cursor={{ strokeDasharray: '3 3' }}
					contentStyle={{
						backgroundColor: 'var(--popover)',
						border: '1px solid var(--border)',
						borderRadius: 6,
						fontSize: 12,
					}}
					formatter={(v, _name, props) => {
						const label = (props?.payload as ScatterPoint | undefined)?.label || '';
						return [fmt(v as number), label];
					}}
				/>
				<Scatter name="동종" data={peerPoints} fill="var(--chart-4)" />
				<Scatter name="회사" data={selfPoints} fill="var(--chart-1)" shape="star" />
			</RechartsScatter>
		</ChartContainer>
	);
}
