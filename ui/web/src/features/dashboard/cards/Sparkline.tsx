// Sparkline — KpiTile 우측 mini line chart (recharts).
// 8 분기 또는 ≤20 point 라인. 단순 area 또는 line.

import { Area, AreaChart, ResponsiveContainer } from 'recharts';

interface Props {
	data: number[];
	color?: string;
	height?: number;
	width?: number | string;
}

export function Sparkline({ data, color = 'var(--chart-1)', height = 32, width = 70 }: Props) {
	if (!data || data.length < 2) return null;
	const chartData = data.map((v, i) => ({ x: i, v }));
	return (
		<div style={{ width, height }}>
			<ResponsiveContainer width="100%" height="100%">
				<AreaChart data={chartData} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
					<defs>
						<linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stopColor={color} stopOpacity={0.4} />
							<stop offset="100%" stopColor={color} stopOpacity={0} />
						</linearGradient>
					</defs>
					<Area
						type="monotone"
						dataKey="v"
						stroke={color}
						strokeWidth={1.5}
						fill="url(#sparkFill)"
						isAnimationActive={false}
					/>
				</AreaChart>
			</ResponsiveContainer>
		</div>
	);
}
