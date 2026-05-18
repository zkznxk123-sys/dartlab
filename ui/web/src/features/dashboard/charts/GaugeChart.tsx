// kind=gauge — SVG 반원 게이지. 단일 점수 + 색띠 (safe/warn/danger).
// 예: Altman Z, distress score, governance grade.

import { cn } from '@/lib/utils';

interface Band {
	from: number;
	to: number;
	tone: 'positive' | 'neutral' | 'accent' | 'negative';
	label?: string;
}

interface Props {
	value: number | null | undefined;
	min: number;
	max: number;
	bands?: Band[];
	label?: string;
	unit?: string;
	hint?: string;
	height?: number;
}

const TONE_VAR: Record<NonNullable<Band['tone']>, string> = {
	positive: 'var(--chart-5)',
	neutral: 'var(--chart-4)',
	accent: 'var(--chart-2)',
	negative: 'var(--chart-3)',
};

function clamp(v: number, lo: number, hi: number): number {
	return Math.max(lo, Math.min(hi, v));
}

function pctToAngle(pct: number): number {
	// 반원 (정통 gauge): -180° (왼쪽 9시) → -90° (위 12시) → 0° (오른쪽 3시).
	// SVG sin 부호 반대 (y 아래 양수) 라 음수 angle 에서 sin 음수 → cy 위쪽으로.
	// 이전 코드 -90 + pct·180 는 오른쪽 반원 (위→아래) 만 그려 왼쪽 절반 누락 회귀
	// (운영자 명시 2026-05-19, distressEnsemble gauge).
	return -180 + pct * 180;
}

export function GaugeChart({ value, min, max, bands = [], label, unit, hint, height = 160 }: Props) {
	const width = height * 1.6;
	const cx = width / 2;
	const cy = height * 0.85;
	const r = height * 0.7;
	const stroke = 14;

	const valid = value != null && Number.isFinite(value);
	const pct = valid ? clamp((value - min) / (max - min), 0, 1) : 0;
	const angle = pctToAngle(pct);
	const ptX = cx + r * Math.cos((angle * Math.PI) / 180);
	const ptY = cy + r * Math.sin((angle * Math.PI) / 180);

	// 띠 호 path 계산
	function arc(fromPct: number, toPct: number): string {
		const a1 = (pctToAngle(fromPct) * Math.PI) / 180;
		const a2 = (pctToAngle(toPct) * Math.PI) / 180;
		const x1 = cx + r * Math.cos(a1);
		const y1 = cy + r * Math.sin(a1);
		const x2 = cx + r * Math.cos(a2);
		const y2 = cy + r * Math.sin(a2);
		const largeArc = toPct - fromPct > 0.5 ? 1 : 0;
		return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
	}

	return (
		<div className="flex h-full w-full flex-col items-center justify-center gap-1 px-2">
			{label && <div className="text-xs text-muted-foreground">{label}</div>}
			<svg
				width="100%"
				height="auto"
				viewBox={`0 0 ${width} ${height + 10}`}
				preserveAspectRatio="xMidYMid meet"
				style={{ maxWidth: `${width}px`, maxHeight: `${height + 10}px` }}
			>
				{/* 배경 호 */}
				<path
					d={arc(0, 1)}
					fill="none"
					stroke="var(--muted)"
					strokeWidth={stroke}
					strokeLinecap="round"
				/>
				{/* 색띠 */}
				{bands.map((b, i) => {
					const fromPct = (b.from - min) / (max - min);
					const toPct = (b.to - min) / (max - min);
					return (
						<path
							key={i}
							d={arc(clamp(fromPct, 0, 1), clamp(toPct, 0, 1))}
							fill="none"
							stroke={TONE_VAR[b.tone]}
							strokeWidth={stroke}
							strokeLinecap="butt"
							opacity={0.5}
						/>
					);
				})}
				{/* 바늘 */}
				{valid && (
					<>
						<line x1={cx} y1={cy} x2={ptX} y2={ptY} stroke="var(--foreground)" strokeWidth={2} strokeLinecap="round" />
						<circle cx={cx} cy={cy} r={4} fill="var(--foreground)" />
					</>
				)}
			</svg>
			<div className={cn('text-2xl font-semibold tabular-nums', valid ? '' : 'text-muted-foreground')}>
				{valid ? value.toFixed(2) : '–'}
				{unit && <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>}
			</div>
			{hint && <div className="text-center text-xs text-muted-foreground">{hint}</div>}
		</div>
	);
}
