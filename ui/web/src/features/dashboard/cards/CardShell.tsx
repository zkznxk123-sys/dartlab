// dashboard 카드 공통 쉘 — shadcn Card 래퍼 + title + help tooltip.

import type { ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface Props {
	title: string;
	help?: string;
	xlSpan?: 1 | 2 | 3;
	colSpan?: 1 | 2 | 3 | 4;
	rowSpan?: 1 | 2 | 3 | 4 | 5 | 6;
	children: ReactNode;
	footer?: ReactNode;
	headerExtra?: ReactNode;
	className?: string;
}

// 4 col bento grid. xl breakpoint 부터 4 column. layout.colSpan 우선.
const COL_SPAN_CLASS: Record<number, string> = {
	1: '',
	2: 'xl:col-span-2',
	3: 'xl:col-span-3',
	4: 'xl:col-span-4',
};

// row 1~6 — Tailwind row-span-N 정적 클래스 (JIT 가 인식 가능한 형태).
const ROW_SPAN_CLASS: Record<number, string> = {
	1: 'row-span-1',
	2: 'row-span-2',
	3: 'row-span-3',
	4: 'row-span-4',
	5: 'row-span-5',
	6: 'row-span-6',
};

export function CardShell({
	title,
	help,
	xlSpan,
	colSpan,
	rowSpan = 2,
	children,
	footer,
	headerExtra,
	className,
}: Props) {
	const effectiveColSpan = colSpan ?? (xlSpan as 1 | 2 | 3 | undefined) ?? 1;
	return (
		<Card
			className={cn(
				'flex flex-col gap-2 py-3 shadow-none overflow-hidden',
				COL_SPAN_CLASS[effectiveColSpan] || '',
				ROW_SPAN_CLASS[rowSpan] || 'row-span-2',
				className,
			)}
		>
			<CardHeader className="flex flex-row items-center justify-between gap-2 px-4">
				<div className="flex items-center gap-1.5">
					<CardTitle className="text-sm font-medium">{title}</CardTitle>
					{help && (
						<TooltipProvider delayDuration={150}>
							<Tooltip>
								<TooltipTrigger asChild>
									<button
										type="button"
										aria-label="해석 도움말"
										className="text-muted-foreground transition-colors hover:text-foreground"
									>
										<HelpCircle className="size-3.5" />
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
			<CardContent className="flex-1 px-2 pb-1 pt-0">{children}</CardContent>
			{footer && (
				<div className="border-t px-4 py-2 text-xs text-muted-foreground">{footer}</div>
			)}
		</Card>
	);
}
