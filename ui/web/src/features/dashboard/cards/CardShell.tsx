// dashboard 카드 공통 쉘 — broadsheet 톤. 모든 카드 동일 surface, 위계는 colSpan 기반 ring.
// hero (12col): 강한 ring + shadow. mid (4~6col): 표준. small (3col): 표준 동일.

import type { ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface Props {
	title: string;
	help?: string;
	colSpan?: number;
	rowSpan?: number;
	kind?: string;
	children: ReactNode;
	footer?: ReactNode;
	headerExtra?: ReactNode;
	className?: string;
}

function surfaceClass(colSpan: number | undefined): string {
	// hero (12col) — ring + 더 진한 border + soft shadow. broadsheet headline 톤.
	if (colSpan != null && colSpan >= 12) {
		return 'bg-card border-border/80 shadow-[0_1px_0_0_oklch(0_0_0/0.04),0_8px_24px_-12px_oklch(0_0_0/0.18)]';
	}
	return 'bg-card border-border/60 shadow-[0_1px_0_0_oklch(0_0_0/0.04)]';
}

export function CardShell({
	title,
	help,
	colSpan,
	rowSpan: _rowSpan,
	kind: _kind,
	children,
	footer,
	headerExtra,
	className,
}: Props) {
	const isHero = colSpan != null && colSpan >= 12;
	return (
		<Card
			className={cn(
				'flex h-full w-full flex-col gap-0 py-0 overflow-hidden rounded-md border',
				surfaceClass(colSpan),
				className,
			)}
		>
			<CardHeader
				className={cn(
					'flex flex-row items-center justify-between gap-2 px-2.5 pt-1.5 pb-1 shrink-0 border-b border-border/40',
					isHero ? 'h-[32px]' : 'h-[26px]',
				)}
			>
				<div className="flex min-w-0 items-center gap-1.5">
					<CardTitle
						className={cn(
							'truncate font-medium leading-tight tracking-tight text-foreground/90',
							isHero ? 'text-[13px]' : 'text-[11.5px]',
						)}
					>
						{title}
					</CardTitle>
					{help && (
						<TooltipProvider delayDuration={150}>
							<Tooltip>
								<TooltipTrigger asChild>
									<button
										type="button"
										aria-label="해석 도움말"
										className="shrink-0 text-muted-foreground/70 transition-colors hover:text-foreground"
									>
										<HelpCircle className="size-3" />
									</button>
								</TooltipTrigger>
								<TooltipContent
									side="bottom"
									align="start"
									className="max-w-xs whitespace-pre-line text-xs leading-relaxed"
								>
									{help}
								</TooltipContent>
							</Tooltip>
						</TooltipProvider>
					)}
				</div>
				{headerExtra}
			</CardHeader>
			<CardContent className="min-h-0 flex-1 px-2 pb-1 pt-1.5">{children}</CardContent>
			{footer && (
				<div className="border-t border-border/40 bg-muted/30 px-2.5 py-1 text-[10px] text-muted-foreground tabular-nums">
					{footer}
				</div>
			)}
		</Card>
	);
}
