// 카드 헤더용 mini sparkline — 경량 SVG path (recharts 의존 0).
// Koyfin 패턴 — last/value 옆 trend 한 줄.

interface Props {
	data: (number | null)[];
	width?: number;
	height?: number;
	color?: string;
	strokeWidth?: number;
}

export function Sparkline({
	data,
	width = 56,
	height = 16,
	color = 'currentColor',
	strokeWidth = 1.25,
}: Props) {
	const valid = data
		.map((v, i) => (v != null && Number.isFinite(v) ? { i, v } : null))
		.filter((x): x is { i: number; v: number } => x !== null);
	if (valid.length < 2) {
		return <svg width={width} height={height} aria-hidden />;
	}
	const xs = valid.map((p) => p.i);
	const ys = valid.map((p) => p.v);
	const xMin = Math.min(...xs);
	const xMax = Math.max(...xs);
	const yMin = Math.min(...ys);
	const yMax = Math.max(...ys);
	const xRange = xMax - xMin || 1;
	const yRange = yMax - yMin || 1;
	const pad = 1;
	const points = valid.map((p) => {
		const x = pad + ((p.i - xMin) / xRange) * (width - pad * 2);
		// SVG y flip (큰 값이 위로).
		const y = pad + (1 - (p.v - yMin) / yRange) * (height - pad * 2);
		return `${x.toFixed(1)},${y.toFixed(1)}`;
	});
	const path = `M ${points.join(' L ')}`;
	// last point dot.
	const last = points[points.length - 1].split(',');
	return (
		<svg
			width={width}
			height={height}
			viewBox={`0 0 ${width} ${height}`}
			style={{ color, display: 'block' }}
			aria-hidden
		>
			<path d={path} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" opacity={0.85} />
			<circle cx={last[0]} cy={last[1]} r={1.5} fill="currentColor" />
		</svg>
	);
}
