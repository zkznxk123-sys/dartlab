// Tableau 10 categorical palette — 데이터 시각화 표준 (Tableau Software 2016).
// dusty muted 10 hue. saturated 가 아니고 분석체 절제 톤. stack 6~8 series 도
// 인접 명확 구분. SSOT: Python `dartlab.viz.palette`.
//
// 의미 (INTENT) 매핑 — traffic-light:
//   primary  = chart-1 Blue   메인
//   positive = chart-5 Green  긍정
//   negative = chart-3 Red    부정
//   accent   = chart-2 Orange 강조
//   neutral  = chart-10 Grey  배경/참조

import type { RechartsSpec } from '../api/client';

export type Intent = 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';

const INTENT_TO_TOKEN: Record<Intent, string> = {
	primary: 'var(--chart-1)',
	positive: 'var(--chart-5)',
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
