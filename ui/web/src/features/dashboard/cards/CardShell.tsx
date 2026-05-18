// dashboard 카드 공통 쉘 — shadcn Card 래퍼 + title + help tooltip.
// 12-col bento grid 기반 — colSpan/rowSpan 은 1~12 (gridstack 표준).

import type { ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface Props {
	title: string;
	help?: string;
	// 12-col gridstack 기준 (KPI=3, chart=4, hero=6, wide=12).
	colSpan?: number;
	rowSpan?: number;
	children: ReactNode;
	footer?: ReactNode;
	headerExtra?: ReactNode;
	className?: string;
}

export function CardShell({
	title,
	help,
	children,
	footer,
	headerExtra,
	className,
}: Props) {
	// gridColumn/gridRow span 은 BentoGrid 의 wrapper div 가 지정. CardShell 은
	// 외형/내용만. h-full 로 wrapper 영역 100% 점유 → 1:1 정사각 보장.
	return (
		<Card
			className={cn(
				'flex h-full w-full flex-col gap-1 py-2 shadow-none overflow-hidden',
				className,
			)}
		>
			<CardHeader className="flex flex-row items-center justify-between gap-1 px-2 pb-0">
				<div className="flex min-w-0 items-center gap-1">
					<CardTitle className="truncate text-xs font-medium">{title}</CardTitle>
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
				<div className="border-t px-2 py-1 text-[10px] text-muted-foreground">{footer}</div>
			)}
		</Card>
	);
}
