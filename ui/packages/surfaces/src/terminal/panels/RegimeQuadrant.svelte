<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { RegimeMarketView, RegimeQuadrantView } from '../lib/macroLens';

	interface Props {
		view: RegimeQuadrantView;
		lang: Lang;
	}
	let { view, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	// 사분면 기하 — 성장(세로 ↑=rising)×물가(가로 →=rising). 멤버십 배치(연속좌표 금지, 07-visual-research).
	// viewBox 200×100 (가로형) — element 가 패널 body 를 채움(height:100%)·viewBox 가 box 보다 넓은 종횡비라
	// 좌우 여백 0(폭 꽉 채움)·세로만 미세 센터링. 문구는 그래프 안 오버레이(아래 두지 않음).
	const QPOS: Record<string, { cx: number; cy: number }> = {
		goldilocks: { cx: 52, cy: 33 }, reflation: { cx: 148, cy: 33 },
		deflation: { cx: 52, cy: 72 }, stagflation: { cx: 148, cy: 72 }
	};
	const cellRect: Record<string, { x: number; y: number }> = {
		goldilocks: { x: 0, y: 12 }, reflation: { x: 100, y: 12 }, deflation: { x: 0, y: 52 }, stagflation: { x: 100, y: 52 }
	};
	const CELLS = [
		{ key: 'goldilocks', x: 5, y: 24, anchor: 'start' },
		{ key: 'reflation', x: 195, y: 24, anchor: 'end' },
		{ key: 'deflation', x: 5, y: 88, anchor: 'start' },
		{ key: 'stagflation', x: 195, y: 88, anchor: 'end' }
	] as const;
	const PHASE_EN: Record<string, string> = {
		expansion: 'Expansion', slowdown: 'Slowdown', contraction: 'Contraction', recovery: 'Recovery',
		stagflation: 'Stagflation', reflation: 'Reflation', deflation: 'Deflation', goldilocks: 'Goldilocks'
	};
	const phaseTxt = (m: RegimeMarketView) => (lang === 'en' ? (PHASE_EN[m.phase] ?? m.phase) : (m.phaseLabel || m.phase));
	const quadName = (key: string | null) => {
		if (!key) return T('미산출', 'n/a');
		const c = view.cells.find((x) => x.key === key);
		return c ? T(c.labelKr, c.labelEn) : key;
	};

	// 마커 배치 — 같은 사분면의 KR/US 는 가로로 분산(겹침 방지).
	const placed = $derived.by(() => {
		const byCell = new Map<string, RegimeMarketView[]>();
		for (const m of view.markets) {
			if (!m.cellKey) continue;
			const arr = byCell.get(m.cellKey) ?? [];
			arr.push(m);
			byCell.set(m.cellKey, arr);
		}
		const out: { m: RegimeMarketView; x: number; y: number }[] = [];
		for (const [key, ms] of byCell) {
			const base = QPOS[key];
			if (!base) continue;
			ms.forEach((m, i) => {
				const dx = ms.length > 1 ? (i - (ms.length - 1) / 2) * 28 : 0;
				out.push({ m, x: base.cx + dx, y: base.cy });
			});
		}
		return out;
	});
	const activeCells = $derived(new Set(placed.map((p) => p.m.cellKey)));
	const noQuadrant = $derived(view.markets.every((m) => !m.cellKey));
	const legendMarkets = $derived(view.markets.filter((m) => m.cellKey));
</script>

<section class="rp" aria-label={T('국면 평면', 'Regime plane')}>
	<div class="rpWrap">
		<svg class="rpPlane" viewBox="0 0 200 100" role="img"
			aria-label={T('성장×물가 국면 평면, KR·US 위치', 'growth×inflation regime plane with KR·US positions')}>
			{#each [...activeCells] as key}
				{#if key && cellRect[key]}
					<rect class="rpActive" x={cellRect[key].x} y={cellRect[key].y} width="100" height="40" />
				{/if}
			{/each}
			<line class="rpCross" x1="100" y1="12" x2="100" y2="92" />
			<line class="rpCross" x1="0" y1="52" x2="200" y2="52" />
			{#each CELLS as c}
				<text class={'rpQuadLbl' + (activeCells.has(c.key) ? ' on' : '')} x={c.x} y={c.y} text-anchor={c.anchor}>{quadName(c.key)}</text>
			{/each}
			<text class="rpAxisCue" x="100" y="9" text-anchor="middle">↑ {T('성장', 'growth')}</text>
			{#each placed as p (p.m.market)}
				<circle class="rpMark" cx={p.x} cy={p.y} r="8" />
				<text class="rpMarkLbl" x={p.x} y={p.y + 2.8} text-anchor="middle">{p.m.market}</text>
			{/each}
		</svg>

		<!-- 사이클 legend — 그래프 안 하단 오버레이(문구를 그래프 밖에 두지 않음·중앙·backdrop 로 가독). -->
		<div class="rpLegend">
			{#if noQuadrant}
				<span class="rpNa">{T('국면 격자 미산출 — 사이클만', 'No regime grid — cycle only')}</span>
			{:else}
				{#each legendMarkets as m (m.market)}
					<span class="rpLeg" title={m.description}>
						<b>{m.market}</b>
						<i>{phaseTxt(m)}</i>
						{#if m.transition}<em>→{T(m.transition.toKr, m.transition.toEn)}{#if m.transition.progressPct != null} {m.transition.progressPct}%{/if}</em>{/if}
					</span>
				{/each}
			{/if}
		</div>
	</div>
</section>

<style>
	.rp { padding: 0; min-width: 0; height: 100%; }
	.rpWrap { position: relative; height: 100%; }
	/* 평면 — 패널 body 를 꽉 채움(height:100%). viewBox(200:100) 가 box 보다 넓은 종횡비라 폭 풀블리드(좌우 여백 0)·세로 미세 센터링·왜곡 0. */
	.rpPlane { display: block; width: 100%; height: 100%; }
	.rpActive { fill: rgba(var(--amber-rgb),.08); }
	.rpCross { stroke: var(--bd); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 3; opacity: .85; }
	.rpQuadLbl { fill: var(--dim); font-size: 9px; font-weight: 700; opacity: .58; }
	.rpQuadLbl.on { fill: var(--amber); opacity: 1; }
	.rpAxisCue { fill: var(--dim); font-size: 7.5px; font-family: var(--mono); opacity: .8; }
	.rpMark { fill: var(--amber); stroke: var(--panel); stroke-width: 1.5; }
	.rpMarkLbl { fill: var(--dl-bg-base, #0f0f10); font-size: 8px; font-weight: 800; font-family: var(--mono); }
	/* 그래프 안 하단 legend 오버레이 — 중앙 chip(backdrop)·markers 와 z-축 분리. 그래프 밖 텍스트 0. */
	.rpLegend { position: absolute; left: 4px; right: 4px; bottom: 2px; display: flex; flex-wrap: wrap; justify-content: center; gap: 3px 8px; pointer-events: none; }
	.rpLeg { display: inline-flex; align-items: baseline; gap: 4px; border: 1px solid var(--bd); border-radius: 999px; padding: 0 6px; background: color-mix(in srgb, var(--panel) 82%, transparent); }
	.rpLeg b { color: var(--amber); font-family: var(--mono); font-size: 8.5px; font-weight: 800; }
	.rpLeg i { font-style: normal; color: var(--fg); font-size: 9px; }
	.rpLeg em { font-style: normal; color: var(--dim); font-size: 8px; font-family: var(--mono); }
	.rpNa { color: var(--dim); font-size: 9px; background: color-mix(in srgb, var(--panel) 82%, transparent); padding: 0 6px; border-radius: 999px; }
</style>
