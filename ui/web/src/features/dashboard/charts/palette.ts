// Anthropic warm earth palette — 공식 brand-guidelines (github.com/anthropics/skills)
// 의 brand 7색 SSOT 를 categorical 10 색으로 확장. warm terracotta + sage + slate
// blue 톤 unified. SSOT: Python `dartlab.viz.palette`.
//
// 의미 (INTENT) 매핑:
//   primary  = chart-1 Orange (Anthropic 메인)
//   accent   = chart-2 Blue   (Anthropic 강조)
//   negative = chart-3 Clay   (dark terracotta — 부정)
//   positive = chart-4 Green  (Anthropic sage)
//   neutral  = chart-10 MidGray (배경/참조)

import type { RechartsSpec } from '../api/client';

export type Intent = 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';

const INTENT_TO_TOKEN: Record<Intent, string> = {
	primary: 'var(--chart-1)',
	positive: 'var(--chart-4)',
	negative: 'var(--chart-3)',
	accent: 'var(--chart-2)',
	neutral: 'var(--chart-10)',
};

const CHART_TOKENS = [
	'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)',
	'var(--chart-6)', 'var(--chart-7)', 'var(--chart-8)', 'var(--chart-9)', 'var(--chart-10)',
];

// 시리즈 배열 → 토큰 색 배정.
//   - stacked: 등장 순 chart-N 순환
//   - intent: INTENT_TO_TOKEN 매핑
//   - fallback: chart-(idx % 10)
export function applyShadcnPalette(spec: RechartsSpec): RechartsSpec {
	let chartIdx = 0;
	return {
		...spec,
		series: spec.series.map((s) => {
			if (s.stack) {
				const color = CHART_TOKENS[chartIdx % CHART_TOKENS.length];
				chartIdx += 1;
				return { ...s, color };
			}
			if (s.intent && s.intent in INTENT_TO_TOKEN) {
				return { ...s, color: INTENT_TO_TOKEN[s.intent as Intent] };
			}
			const fallback = CHART_TOKENS[chartIdx % CHART_TOKENS.length];
			chartIdx += 1;
			return { ...s, color: fallback };
		}),
	};
}
