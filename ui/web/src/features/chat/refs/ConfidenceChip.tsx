// 신뢰도 chip — 본문 안 [conf:high|mid|low|<숫자>] 마커 → 색상 chip.
// SSOT 매핑 (server core/confidence.py.label 과 1:1):
//   confidence < 40 → low (rose)
//   40 ≤ confidence ≤ 70 → mid (zinc)
//   confidence > 70 → high (emerald)

export type ConfLevel = 'low' | 'mid' | 'high';

export function labelFromScore(score: number): ConfLevel {
	if (score < 40) return 'low';
	if (score > 70) return 'high';
	return 'mid';
}

function styleFor(level: ConfLevel): string {
	if (level === 'high') return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
	if (level === 'low') return 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30';
	return 'bg-zinc-500/15 text-zinc-700 dark:text-zinc-400 border-zinc-500/30';
}

export function ConfidenceChip({ raw }: { raw: string }) {
	const trimmed = raw.trim().toLowerCase();
	let level: ConfLevel;
	let scoreText: string | null = null;
	if (trimmed === 'high' || trimmed === 'mid' || trimmed === 'low') {
		level = trimmed as ConfLevel;
	} else {
		const n = Number(trimmed);
		if (!Number.isFinite(n)) return null;
		level = labelFromScore(n);
		scoreText = String(Math.round(n));
	}
	const cls = styleFor(level);
	const display = scoreText ? `${level} ${scoreText}` : level;
	return (
		<span
			className={`mx-0.5 inline-flex items-center rounded border px-1 py-0 align-baseline text-[10px] font-mono ${cls}`}
			title={scoreText ? `신뢰도 ${scoreText}/100 (${level})` : `신뢰도 ${level}`}
		>
			{display}
		</span>
	);
}
