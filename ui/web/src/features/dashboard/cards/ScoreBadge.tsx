// Snowflake 5 차원 종합 평점 wide 카드 — 24×3.
// 좌측: 큰 grade + overall score. 우측: 5 차원 점수 inline.

interface Dimension {
	key: string;
	label: string;
	score: number;
}

interface Props {
	grade?: string;
	overallScore?: number | null;
	dimensions?: Dimension[];
	summaryLine?: string;
}

function gradeColor(grade?: string): string {
	if (!grade) return 'text-foreground';
	const letter = grade[0];
	if (letter === 'A') return 'text-[var(--chart-3)]';
	if (letter === 'B') return 'text-[var(--chart-1)]';
	if (letter === 'C') return 'text-[var(--chart-4)]';
	return 'text-[var(--chart-2)]';
}

export function ScoreBadge({ grade, overallScore, dimensions, summaryLine }: Props) {
	if (!grade && overallScore == null) {
		return (
			<div className="flex h-full items-center justify-center text-xs text-muted-foreground">
				종합 점수 없음
			</div>
		);
	}
	return (
		<div className="flex h-full items-center gap-4 px-4 py-3">
			<div className="flex shrink-0 flex-col items-center gap-0.5 rounded-md border bg-muted/40 px-4 py-2">
				<div className={`text-4xl font-bold leading-none ${gradeColor(grade)}`}>{grade ?? '?'}</div>
				{overallScore != null && (
					<div className="text-xs tabular-nums text-muted-foreground">{overallScore.toFixed(0)}점</div>
				)}
			</div>
			<div className="flex min-w-0 flex-1 flex-col gap-1">
				<div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
					{(dimensions ?? []).map((d) => (
						<span key={d.key} className="inline-flex items-center gap-1">
							<span className="text-muted-foreground">{d.label}</span>
							<span className="font-medium tabular-nums">{d.score.toFixed(1)}</span>
							<span className="text-muted-foreground">/5</span>
						</span>
					))}
				</div>
				{summaryLine && (
					<div className="line-clamp-2 text-xs text-muted-foreground">{summaryLine}</div>
				)}
			</div>
		</div>
	);
}
