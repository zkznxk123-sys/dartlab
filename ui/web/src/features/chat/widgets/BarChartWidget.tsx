// 막대 — 비교/분포.
// spec: { kind: 'bar', data, xKey?, yKeys? }
import {
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts';

const COLORS = ['#ea4647', '#fb923c', '#3b82f6', '#10b981', '#a855f7', '#facc15'];

interface Spec {
	data?: Array<Record<string, unknown>>;
	xKey?: string;
	yKeys?: string[];
}

function deriveKeys(data: Array<Record<string, unknown>>): { xKey: string; yKeys: string[] } {
	if (!data.length) return { xKey: 'x', yKeys: [] };
	const sample = data[0]!;
	const all = Object.keys(sample);
	const xCandidates = ['x', 'date', 'period', 'time', 'label', 'name', 'category'];
	const xKey = xCandidates.find((k) => k in sample) ?? all[0]!;
	const yKeys = all.filter((k) => k !== xKey && typeof sample[k] === 'number');
	return { xKey, yKeys };
}

export function BarChartWidget({ spec }: { spec: Spec }) {
	const data = Array.isArray(spec.data) ? spec.data : [];
	if (!data.length) return null;
	const { xKey, yKeys } =
		spec.xKey && Array.isArray(spec.yKeys)
			? { xKey: spec.xKey, yKeys: spec.yKeys }
			: deriveKeys(data);
	if (!yKeys.length) return null;

	return (
		<div className="h-[280px] w-full">
			<ResponsiveContainer width="100%" height="100%">
				<BarChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
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
					{yKeys.map((k, i) => (
						<Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} />
					))}
				</BarChart>
			</ResponsiveContainer>
		</div>
	);
}
