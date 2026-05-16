// dCR 신용등급 chip — 답변 헤더 노출 + click 시 7 축 점수 popover.
// 데이터 원천: EngineCall(Company.show) 결과 data.dcrBadge (server creditBadge.getDcrBadge).
import { ShieldCheck } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface DcrBadgeData {
	grade?: string | null;
	gradeRaw?: string | null;
	score?: number | null;
	healthScore?: number | null;
	pdEstimate?: number | null;
	outlook?: string | null;
	investmentGrade?: boolean | null;
	axes?: Array<{ name?: string; weight?: number | null; score?: number | null }> | null;
	confidence?: number | null;
}

function gradeColor(grade: string | null | undefined): string {
	if (!grade) return 'bg-muted text-muted-foreground';
	const g = grade.toUpperCase();
	if (g.startsWith('AAA') || g.startsWith('AA')) return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
	if (g.startsWith('A')) return 'bg-sky-500/15 text-sky-700 dark:text-sky-400 border-sky-500/30';
	if (g.startsWith('BBB')) return 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30';
	if (g.startsWith('BB') || g.startsWith('B')) return 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30';
	return 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30';
}

function outlookSymbol(outlook: string | null | undefined): string {
	if (outlook === '긍정적') return '▲';
	if (outlook === '부정적') return '▼';
	return '◆';
}

export function DcrPopover({ badge }: { badge: DcrBadgeData }) {
	const gradeRaw = badge.gradeRaw || (badge.grade ? badge.grade.replace(/^dCR-/, '') : null);
	if (!gradeRaw) return null;
	const color = gradeColor(gradeRaw);
	const outlook = outlookSymbol(badge.outlook);
	return (
		<Popover>
			<PopoverTrigger asChild>
				<button
					type="button"
					className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium hover:opacity-80 transition-opacity ${color}`}
					aria-label="dCR 신용등급 상세"
				>
					<ShieldCheck className="size-3" />
					<span className="font-mono">dCR: {gradeRaw}</span>
					<span className="text-[10px] opacity-70">{outlook}</span>
				</button>
			</PopoverTrigger>
			<PopoverContent className="w-80 p-3" align="start">
				<div className="space-y-2">
					<div className="flex items-baseline justify-between border-b border-border pb-1.5">
						<div className="text-sm font-semibold">dCR-{gradeRaw} <span className="text-[10px] font-normal text-muted-foreground">자체 등급</span></div>
						<div className="text-[10px] text-muted-foreground">
							신뢰도 {badge.confidence ?? '-'} / 100
						</div>
					</div>
					<div className="grid grid-cols-3 gap-2 text-[11px]">
						<div>
							<div className="text-muted-foreground text-[10px]">점수</div>
							<div className="font-mono">{badge.score?.toFixed?.(2) ?? '-'}</div>
						</div>
						<div>
							<div className="text-muted-foreground text-[10px]">PD (1y)</div>
							<div className="font-mono">{badge.pdEstimate != null ? `${badge.pdEstimate}%` : '-'}</div>
						</div>
						<div>
							<div className="text-muted-foreground text-[10px]">전망</div>
							<div>{badge.outlook ?? '-'}</div>
						</div>
					</div>
					{badge.axes && badge.axes.length > 0 && (
						<div className="space-y-1 pt-1">
							<div className="text-[10px] uppercase tracking-wider text-muted-foreground">7 축</div>
							{badge.axes.map((a, i) => (
								<div key={i} className="flex items-center justify-between text-[11px]">
									<span className="truncate">{a.name}</span>
									<span className="font-mono text-muted-foreground shrink-0">
										{a.score?.toFixed?.(1) ?? '-'}
										{a.weight != null && (
											<span className="ml-1 text-[9px] opacity-60">·{a.weight}%</span>
										)}
									</span>
								</div>
							))}
						</div>
					)}
					<div className="border-t border-border pt-1.5 text-[10px] text-muted-foreground leading-relaxed">
						S&P / Moody's 의존 없는 dartlab 자체 산출. 7 축 가중평균 + CHS / Notch 보정.
					</div>
				</div>
			</PopoverContent>
		</Popover>
	);
}

// 사용 안되는 export 막힘 회피 — Badge 자체도 export 해 둠 (테스트 import 용).
export { Badge as DcrBadgeBase };
