// dashboard 카드 공통 쉘 — shadcn Card 래퍼 + title + help tooltip.
// 24-col bento (v3-r5) — colSpan/rowSpan 1~24, kind-driven chrome 위계.

import type { ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface Props {
	title: string;
	help?: string;
	// 24-col gridstack 기준 (KPI=4, chart=8, hero=12, wide=24).
	colSpan?: number;
	rowSpan?: number;
	// kind-driven chrome — v3-r5 §8.3. KPI/diffView/gauge/topList = weak,
	// trend/breakdown/scatter/matrix/waterfall/comparisonTable = mid,
	// radar/scoreBadge/narrativeBridge/gauge(wide)/phaseIndicator(wide) = strong.
	kind?: string;
	children: ReactNode;
	footer?: ReactNode;
	headerExtra?: ReactNode;
	className?: string;
}

const TIER_CLASSNAMES = {
	weak: 'bg-muted/30 border-border/40 shadow-none',
	mid: 'bg-card border-border/60 shadow-none',
	strong: 'bg-card border-border shadow-sm',
} as const;

const KIND_TIER: Record<string, keyof typeof TIER_CLASSNAMES> = {
	kpiTile: 'weak',
	diffView: 'weak',
	gauge: 'weak',
	topList: 'weak',
	trend: 'mid',
	breakdown: 'mid',
	scatter: 'mid',
	matrix: 'mid',
	waterfall: 'mid',
	comparisonTable: 'mid',
	radar: 'strong',
	scoreBadge: 'strong',
	narrativeBridge: 'strong',
	phaseIndicator: 'weak',
};

function resolveTier(kind: string | undefined, colSpan: number | undefined): keyof typeof TIER_CLASSNAMES {
	if (!kind) return 'mid';
	// wide hero — gauge / phaseIndicator 가 24 col 이면 강제 strong.
	if (colSpan != null && colSpan >= 24 && (kind === 'gauge' || kind === 'phaseIndicator')) return 'strong';
	return KIND_TIER[kind] ?? 'mid';
}

export function CardShell({
	title,
	help,
	colSpan,
	rowSpan: _rowSpan,
	kind,
	children,
	footer,
	headerExtra,
	className,
}: Props) {
	const tier = resolveTier(kind, colSpan);
	return (
		<Card
			className={cn(
				'flex h-full w-full flex-col gap-1 py-1 overflow-hidden border',
				TIER_CLASSNAMES[tier],
				className,
			)}
		>
			<CardHeader className="flex flex-row items-center justify-between gap-1 px-2 pt-1 pb-0 h-[24px] shrink-0">
				<div className="flex min-w-0 items-center gap-1">
					<CardTitle className="truncate text-xs font-medium leading-tight">{title}</CardTitle>
					{help && (
						<TooltipProvider delayDuration={150}>
							<Tooltip>
								<TooltipTrigger asChild>
									<button
										type="button"
										aria-label="해석 도움말"
										className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
									>
										<HelpCircle className="size-3" />
									</button>
								</TooltipTrigger>
								<TooltipContent side="bottom" align="start" className="max-w-xs whitespace-pre-line text-xs leading-relaxed">
									{help}
								</TooltipContent>
							</Tooltip>
						</TooltipProvider>
					)}
				</div>
				{headerExtra}
			</CardHeader>
			<CardContent className="min-h-0 flex-1 px-1.5 pb-0 pt-0">{children}</CardContent>
			{footer && (
				<div className="border-t border-border bg-muted/20 px-2 py-1 text-[10px] text-muted-foreground">
					{footer}
				</div>
			)}
		</Card>
	);
}
