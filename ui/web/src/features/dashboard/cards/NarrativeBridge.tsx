// 6 막 인과 자연어 wide 카드 — Story view 의 결론. 24×4.
// 각 행: [from 막 → to 막] 한 줄 인과 문장. 마지막 행: 종합.

interface Transition {
	from: string;
	to: string;
	text: string;
}

interface Props {
	transitions: Transition[];
	summaryLine?: string;
}

export function NarrativeBridge({ transitions, summaryLine }: Props) {
	if (!transitions?.length && !summaryLine) {
		return (
			<div className="flex h-full items-center justify-center text-xs text-muted-foreground">
				서사 데이터 없음
			</div>
		);
	}
	return (
		<div className="flex h-full flex-col gap-1 overflow-auto px-3 py-2 text-sm">
			{transitions.map((t, i) => (
				<div key={i} className="flex items-center gap-2 leading-relaxed">
					<span className="inline-flex shrink-0 items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground">
						<span>{t.from}</span>
						<span className="text-foreground/60">→</span>
						<span>{t.to}</span>
					</span>
					<span className="min-w-0 flex-1 text-foreground/90">{t.text}</span>
				</div>
			))}
			{summaryLine && (
				<div className="mt-1 border-t pt-1 text-xs text-muted-foreground">{summaryLine}</div>
			)}
		</div>
	);
}
