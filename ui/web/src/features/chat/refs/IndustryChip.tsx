// 산업 컨텍스트 chip — 답변 헤더 노출 + click 시 peers/stage popover.
// 데이터 원천: EngineCall(Company.show) 결과 data.industryBadge (server industryContext.getIndustryBadge).
import { Factory } from 'lucide-react';

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface IndustryBadgeData {
	industryId?: string | null;
	industryName?: string | null;
	stage?: string | null;
	stageName?: string | null;
	role?: string | null;
	stream?: string | null;
	phase?: string | null;
	peers?: Array<{ stockCode?: string; corpName?: string }> | null;
	confidence?: number | null;
}

function phaseColor(phase: string | null | undefined): string {
	switch (phase) {
		case '도입':
			return 'bg-violet-500/15 text-violet-700 dark:text-violet-400 border-violet-500/30';
		case '성장':
			return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
		case '성숙':
			return 'bg-sky-500/15 text-sky-700 dark:text-sky-400 border-sky-500/30';
		case '재도약':
			return 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30';
		case '쇠퇴':
			return 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30';
		default:
			return 'bg-zinc-500/15 text-zinc-700 dark:text-zinc-400 border-zinc-500/30';
	}
}

export function IndustryChip({ badge }: { badge: IndustryBadgeData }) {
	if (!badge.industryName) return null;
	const color = phaseColor(badge.phase);
	const phaseLabel = badge.phase && badge.phase !== 'unknown' ? badge.phase : null;
	const head = badge.stageName ? `${badge.industryName} · ${badge.stageName}` : badge.industryName;
	return (
		<Popover>
			<PopoverTrigger asChild>
				<button
					type="button"
					className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium hover:opacity-80 transition-opacity ${color}`}
					aria-label="산업 컨텍스트 상세"
				>
					<Factory className="size-3" />
					<span className="truncate max-w-[180px]">{head}</span>
					{phaseLabel && <span className="text-[10px] opacity-80">· {phaseLabel}</span>}
				</button>
			</PopoverTrigger>
			<PopoverContent className="w-72 p-3" align="start">
				<div className="space-y-2 text-xs">
					<div className="flex items-baseline justify-between border-b border-border pb-1.5">
						<div className="text-sm font-semibold">{badge.industryName}</div>
						<div className="text-[10px] text-muted-foreground">
							신뢰도 {badge.confidence ?? '-'}/100
						</div>
					</div>
					<div className="grid grid-cols-3 gap-2 text-[11px]">
						{badge.stageName && (
							<div>
								<div className="text-muted-foreground text-[10px]">단계</div>
								<div>{badge.stageName}</div>
							</div>
						)}
						{badge.role && (
							<div>
								<div className="text-muted-foreground text-[10px]">역할</div>
								<div>{badge.role}</div>
							</div>
						)}
						{phaseLabel && (
							<div>
								<div className="text-muted-foreground text-[10px]">phase</div>
								<div>{phaseLabel}</div>
							</div>
						)}
					</div>
					{badge.peers && badge.peers.length > 0 && (
						<div className="space-y-0.5 pt-1">
							<div className="text-[10px] uppercase tracking-wider text-muted-foreground">peers</div>
							{badge.peers.map((p, i) => (
								<div key={i} className="flex items-center justify-between text-[11px]">
									<span className="truncate">{p.corpName || '-'}</span>
									<span className="font-mono text-[10px] text-muted-foreground">{p.stockCode}</span>
								</div>
							))}
						</div>
					)}
					<div className="border-t border-border pt-1.5 text-[10px] text-muted-foreground leading-relaxed">
						5 phase: 도입 · 성장 · 성숙 · 재도약 · 쇠퇴. 시계열 쇠퇴 후 성장 전환 시 재도약.
					</div>
				</div>
			</PopoverContent>
		</Popover>
	);
}
