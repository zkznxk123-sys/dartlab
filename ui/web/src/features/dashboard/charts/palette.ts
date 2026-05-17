// shadcn 8 토큰 distinct hue 팔레트.
// globals.css 의 `--chart-1~8` 가 muted oklch (low-chroma, 재무 분석체 톤).
// 룰: stack 보유 시리즈는 stack 등장 순으로 chart-N 누적 할당. 같은 stack 내 시리즈는
// 위 인덱스가 chart-1, 그다음 chart-2... (ramp 옅음 폐기 → 색 자체로 구분).
// stack 없는 시리즈는 intent 기반 (primary/positive/negative/neutral/accent).
//
// SSOT: Python `dartlab.viz.palette` 의 INTENT_MAP 미러.

import type { RechartsSpec } from '../api/client';

export type Intent = 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';

// traffic-light 의미 매핑 (Tableau 10 hue 순서):
//   primary = chart-1 (blue, 핵심)
//   positive = chart-5 (green, 좋은 신호)
//   negative = chart-3 (red, 부정 신호)
//   neutral = chart-4 (teal, 절제 배경)
//   accent = chart-2 (orange, 강조)
const INTENT_TO_TOKEN: Record<Intent, string> = {
	primary: 'var(--chart-1)',
	positive: 'var(--chart-5)',
	negative: 'var(--chart-3)',
	neutral: 'var(--chart-4)',
	accent: 'var(--chart-2)',
};

const CHART_TOKENS = [
	'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)',
	'var(--chart-5)', 'var(--chart-6)', 'var(--chart-7)', 'var(--chart-8)',
];

// 시리즈 배열 → 토큰 색 배정.
//   - stacked 시리즈: 전역 인덱스 (시리즈 등장 순) 로 chart-N 순환.
//   - 비-stacked + intent: INTENT_TO_TOKEN.
//   - fallback: chart-(idx % 8).
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
