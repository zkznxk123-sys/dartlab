<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { MomentumPoint } from '../lib/macroBoard';

	// 국면 모멘텀 궤적 — 성장(세로↑)×물가(가로→) z-모멘텀 평면에 KR·US 최근 12개월 경로.
	// 점=월, 큰 점=현재, 꼬리=과거. 사분면 배경은 *참조 라벨*(자산 추천 0). 데이터는 부모(MacroBoard)가 계산.
	interface Props {
		krTrail: MomentumPoint[];
		usTrail: MomentumPoint[];
		lang: Lang;
	}
	let { krTrail, usTrail, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	const W = 320, H = 240, cx = 160, cy = 116, scale = 34, R = 92; // z*scale px, clamp 반경
	const clamp = (px: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, px));
	const plotX = (i: number) => clamp(cx + i * scale, cx - R, cx + R);
	const plotY = (g: number) => clamp(cy - g * scale, cy - R, cy + R); // 성장↑ = 위(y 감소)

	const QUAD = [
		{ kr: '골디락스', en: 'Goldilocks', x: 16, y: 26, anchor: 'start' as const },
		{ kr: '리플레이션', en: 'Reflation', x: 304, y: 26, anchor: 'end' as const },
		{ kr: '디플레이션', en: 'Deflation', x: 16, y: 214, anchor: 'start' as const },
		{ kr: '스태그플레이션', en: 'Stagflation', x: 304, y: 214, anchor: 'end' as const }
	];

	const pathOf = (trail: MomentumPoint[]) => trail.map((p, k) => `${k ? 'L' : 'M'}${plotX(p.i).toFixed(1)} ${plotY(p.g).toFixed(1)}`).join(' ');
	const markets = $derived([
		{ key: 'KR', trail: krTrail },
		{ key: 'US', trail: usTrail }
	].filter((m) => m.trail.length));
</script>

<section class="gt" aria-label={T('국면 모멘텀 궤적', 'Regime momentum trail')}>
	<div class="gtHead">
		<span class="gtK">REGIME TRAIL</span>
		<b>{T('국면 모멘텀 — 성장 × 물가 (최근 12개월 궤적)', 'Regime momentum — growth × inflation (12-month trail)')}</b>
	</div>
	<div class="gtBody">
		<svg class="gtPlane" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={T('성장 물가 모멘텀 평면', 'growth inflation momentum plane')}>
			<!-- 사분면 배경 + 십자축(0=역사 평균) -->
			<line class="gtCross" x1={cx} y1="16" x2={cx} y2={H - 16} />
			<line class="gtCross" x1="12" y1={cy} x2={W - 12} y2={cy} />
			{#each QUAD as q (q.kr)}<text class="gtQuad" x={q.x} y={q.y} text-anchor={q.anchor}>{T(q.kr, q.en)}</text>{/each}
			<text class="gtAxis" x={cx} y="12" text-anchor="middle">↑ {T('성장', 'growth')}</text>
			<text class="gtAxis" x={W - 14} y={cy - 5} text-anchor="end">{T('물가', 'inflation')} →</text>
			<!-- 궤적 -->
			{#each markets as m (m.key)}
				<path class="gtTrail" d={pathOf(m.trail)} />
				{#each m.trail.slice(0, -1) as p, k (p.ym)}
					<circle class="gtDot" cx={plotX(p.i)} cy={plotY(p.g)} r="2" style={`opacity:${0.2 + 0.5 * (k / Math.max(1, m.trail.length - 1))}`} />
				{/each}
				{#if m.trail.length}
					{@const now = m.trail[m.trail.length - 1]}
					<circle class="gtNow" cx={plotX(now.i)} cy={plotY(now.g)} r="9" />
					<text class="gtNowLbl" x={plotX(now.i)} y={plotY(now.g) + 3.5} text-anchor="middle">{m.key}</text>
				{/if}
			{/each}
		</svg>
		{#if !markets.length}
			<div class="gtNa">{T('모멘텀 궤적 미산출 — 표본 부족', 'No momentum trail — insufficient sample')}</div>
		{/if}
	</div>
	<div class="gtFoot">{T('성장·물가 모멘텀 z-score 궤적(역사 평균=중심) · 추천 아님', 'Growth/inflation momentum z-score trail (history mean = center) · not advice')}</div>
</section>

<style>
	.gt { border: 1px solid var(--bd); border-radius: 8px; background: var(--panel); padding: 9px 12px 8px; }
	.gtHead { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
	.gtK { font-family: var(--mono); color: var(--amber); font-weight: 800; font-size: 9px; letter-spacing: 0.06em; flex: 0 0 auto; }
	.gtHead b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 700; color: var(--txt); }
	.gtBody { position: relative; margin-top: 6px; }
	/* 히어로는 컴팩트하게 — 평면이 첫 화면을 독점해 카테고리 보드를 가리지 않도록 폭 캡(≈285px 높이). */
	.gtPlane { display: block; width: min(100%, 380px); margin: 0 auto; aspect-ratio: 320 / 240; }
	.gtCross { stroke: var(--bd); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 3; opacity: 0.8; }
	.gtQuad { fill: var(--dim); font-size: 10px; font-weight: 700; opacity: 0.5; }
	.gtAxis { fill: var(--dimmer); font-size: 8px; font-family: var(--mono); opacity: 0.85; }
	.gtTrail { fill: none; stroke: var(--dim); stroke-width: 1.4; vector-effect: non-scaling-stroke; opacity: 0.55; stroke-linejoin: round; }
	.gtDot { fill: var(--dim); }
	.gtNow { fill: var(--amber); stroke: var(--panel); stroke-width: 2; }
	.gtNowLbl { fill: var(--bg); font-size: 8.5px; font-weight: 800; font-family: var(--mono); }
	.gtNa { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--dimmer); font-size: 10px; }
	.gtFoot { margin-top: 6px; color: var(--dimmer); font-size: 9px; line-height: 1.3; }
</style>
