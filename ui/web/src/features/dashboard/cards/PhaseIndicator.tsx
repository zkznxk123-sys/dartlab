// kind=phaseIndicator — 다단계 indicator (생애주기 6 단계, 사이클 4 단계 등).
// 활성 단계 highlight + 신뢰도 표시.

import { cn } from '@/lib/utils';

interface Props {
	stages: string[];
	activeIndex: number;
	confidence?: number;   // 0~1
	label?: string;
	hint?: string;
}

export function PhaseIndicator({ stages, activeIndex, confidence, label, hint }: Props) {
	return (
		<div className="flex h-full flex-col gap-3 px-2 py-2">
			{label && <div className="text-sm font-medium text-muted-foreground">{label}</div>}
			<div className="grid grid-flow-col gap-1 auto-cols-fr">
				{stages.map((s, i) => {
					const isActive = i === activeIndex;
					const isPast = i < activeIndex;
					return (
						<div
							key={s}
							className={cn(
								'rounded-md border px-2 py-2 text-center text-xs transition-colors',
								isActive && 'border-foreground bg-foreground text-background font-semibold',
								isPast && 'border-muted-foreground/30 bg-muted text-muted-foreground',
								!isActive && !isPast && 'border-dashed text-muted-foreground',
							)}
						>
							<div className="mb-0.5 font-mono text-[10px] opacity-60">{i + 1}</div>
							<div>{s}</div>
						</div>
					);
				})}
			</div>
			{confidence != null && (
				<div className="flex items-center gap-2 text-xs text-muted-foreground">
					<span>신뢰도</span>
					<div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
						<div
							className="h-full bg-[var(--chart-1)]"
							style={{ width: `${Math.max(0, Math.min(100, confidence * 100))}%` }}
						/>
					</div>
					<span className="font-mono">{Math.round(confidence * 100)}%</span>
				</div>
			)}
			{hint && <div className="text-xs text-muted-foreground">{hint}</div>}
		</div>
	);
}
