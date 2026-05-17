// 단일 KPI 카드 — 메인 값 + 변화량/단위.
// spec: { kind: 'kpi', label, value, delta?, unit?, asOf? }
interface Spec {
	label?: string;
	value?: number | string;
	delta?: number;
	unit?: string;
	asOf?: string;
}

function fmt(v: number | string | undefined): string {
	if (v == null) return '—';
	if (typeof v === 'number') {
		if (Math.abs(v) >= 1_000_000_000) return (v / 1_000_000_000).toFixed(1) + 'B';
		if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M';
		if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(1) + 'K';
		return v.toFixed(2);
	}
	return v;
}

export function KpiWidget({ spec }: { spec: Spec }) {
	const isUp = typeof spec.delta === 'number' && spec.delta > 0;
	const isDown = typeof spec.delta === 'number' && spec.delta < 0;
	return (
		<div className="rounded-md border border-border p-4">
			{spec.label && (
				<div className="text-xs text-muted-foreground">{spec.label}</div>
			)}
			<div className="mt-1 flex items-baseline gap-2">
				<span className="text-2xl font-semibold">{fmt(spec.value)}</span>
				{spec.unit && <span className="text-xs text-muted-foreground">{spec.unit}</span>}
				{typeof spec.delta === 'number' && (
					<span
						className={
							'text-xs font-mono ' +
							(isUp
								? 'text-[#ea4647]'
								: isDown
									? 'text-blue-500'
									: 'text-muted-foreground')
						}
					>
						{isUp ? '▲' : isDown ? '▼' : ''} {Math.abs(spec.delta).toFixed(2)}
					</span>
				)}
			</div>
			{spec.asOf && (
				<div className="mt-1 text-[10px] font-mono text-muted-foreground">
					as of {spec.asOf}
				</div>
			)}
		</div>
	);
}
