// 아직 카드가 채워지지 않은 분석 탭의 placeholder.
// 본 PR commit C6 ~ C12 에서 각 탭이 채워질 예정.

import { Construction } from 'lucide-react';

interface Props {
	title: string;
	description: string;
	plannedCards: string[];
}

export function TabPlaceholder({ title, description, plannedCards }: Props) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-4 p-12 text-center">
			<Construction className="size-10 text-muted-foreground" />
			<h2 className="text-lg font-semibold">{title}</h2>
			<p className="max-w-md text-sm text-muted-foreground">{description}</p>
			<div className="flex flex-wrap justify-center gap-2 pt-2">
				{plannedCards.map((c) => (
					<span
						key={c}
						className="rounded-full border border-dashed px-3 py-1 text-xs text-muted-foreground"
					>
						{c}
					</span>
				))}
			</div>
		</div>
	);
}
