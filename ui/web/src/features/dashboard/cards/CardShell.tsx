// dashboard 카드 공통 쉘 — shadcn Card 기본. 음영·ring·hero 차등 강조 폐기 (운영자 명시).

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
	// Playwright `dashboardSnap.py` 정량 측정용 — `[data-cardkey]` selector.
	cardKey?: string;
}

export function CardShell({
	title,
	help,
	colSpan: _colSpan,
	rowSpan: _rowSpan,
	kind: _kind,
	children,
	footer,
	headerExtra,
	className,
	cardKey,
}: Props) {
	return (
		<Card
			data-cardkey={cardKey}
			className={cn(
				'flex h-full w-full flex-col gap-0 py-0 shadow-none overflow-hidden',
				className,
			)}
		>
			<CardHeader
				className="!grid-cols-none flex h-[32px] flex-row items-center justify-between gap-3 px-3 !pb-1.5 !pt-0 shrink-0 border-b"
			>
				<div className="flex min-w-0 items-baseline gap-1.5">
					<CardTitle className="truncate text-[12px] font-semibold leading-tight tracking-tight">
						{title}
					</CardTitle>
					{help && (
						<TooltipProvider delayDuration={150}>
							<Tooltip>
								<TooltipTrigger asChild>
									<button
										type="button"
										aria-label="해석 도움말"
										className="shrink-0 self-center text-muted-foreground/60 transition-colors hover:text-foreground"
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
				{headerExtra && (
					<div className="flex shrink-0 items-baseline gap-2 tabular-nums">{headerExtra}</div>
				)}
			</CardHeader>
			<CardContent className="min-h-0 flex-1 px-2 pb-2 pt-1.5">{children}</CardContent>
			{footer && (
				<div className="mt-1 border-t px-2.5 py-1.5 text-[10px] text-muted-foreground tabular-nums">
					{footer}
				</div>
			)}
		</Card>
	);
}
