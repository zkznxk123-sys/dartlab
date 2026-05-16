// 시계열 line chart — recharts ResponsiveContainer.
// spec: { kind: 'line'|'area', data: [{x|date, y|value, ...}], xKey?, yKeys? }
import {
	Area,
	AreaChart,
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts';

const COLORS = ['#ea4647', '#fb923c', '#3b82f6', '#10b981', '#a855f7', '#facc15'];

interface Spec {
	kind?: string;
	data?: Array<Record<string, unknown>>;
	xKey?: string;
	yKeys?: string[];
}

function deriveKeys(data: Array<Record<string, unknown>>): { xKey: string; yKeys: string[] } {
	if (!data.length) return { xKey: 'x', yKeys: [] };
	const sample = data[0]!;
	const all = Object.keys(sample);
	// 후보 xKey
	const xCandidates = ['x', 'date', 'period', 'time', 'label', 'name'];
	const xKey = xCandidates.find((k) => k in sample) ?? all[0]!;
	// 나머지 numeric
	const yKeys = all.filter((k) => k !== xKey && typeof sample[k] === 'number');
	return { xKey, yKeys };
}

export function LineChartWidget({ spec }: { spec: Spec }) {
	const data = Array.isArray(spec.data) ? spec.data : [];
	if (!data.length) return null;
	const { xKey, yKeys } = (() => {
		if (spec.xKey && Array.isArray(spec.yKeys)) return { xKey: spec.xKey, yKeys: spec.yKeys };
		return deriveKeys(data);
	})();
	if (!yKeys.length) return null;

	const isArea = spec.kind === 'area';
	const Chart = isArea ? AreaChart : LineChart;

	return (
		<div className="h-[280px] w-full">
			<ResponsiveContainer width="100%" height="100%">
				<Chart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
					<CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
					<XAxis dataKey={xKey} fontSize={11} stroke="var(--muted-foreground)" />
					<YAxis fontSize={11} stroke="var(--muted-foreground)" />
					<Tooltip
						contentStyle={{
							background: 'var(--background)',
							border: '1px solid var(--border)',
							fontSize: '11px',
						}}
					/>
					{yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '11px' }} />}
					{yKeys.map((k, i) =>
						isArea ? (
							<Area
								key={k}
								type="monotone"
								dataKey={k}
								stroke={COLORS[i % COLORS.length]}
								fill={COLORS[i % COLORS.length]}
								fillOpacity={0.2}
								strokeWidth={2}
							/>
						) : (
							<Line
								key={k}
								type="monotone"
								dataKey={k}
								stroke={COLORS[i % COLORS.length]}
								strokeWidth={2}
								dot={data.length <= 16}
							/>
						),
					)}
				</Chart>
			</ResponsiveContainer>
		</div>
	);
}
