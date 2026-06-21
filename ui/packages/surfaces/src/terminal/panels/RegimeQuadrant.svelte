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
	// viewBox 200×120 — 좌우 완전 풀블리드(active rect x0→200)·높이 절제(밴드 10px). 멤버십 배치.
	const QPOS: Record<string, { cx: number; cy: number }> = {
		goldilocks: { cx: 50, cy: 35 }, // 성장↑·물가↓ (좌상)
		reflation: { cx: 150, cy: 35 }, // 성장↑·물가↑ (우상)
		deflation: { cx: 50, cy: 85 }, // 성장↓·물가↓ (좌하)
		stagflation: { cx: 150, cy: 85 } // 성장↓·물가↑ (우하)
	};
	const cellRect: Record<string, { x: number; y: number }> = {
		goldilocks: { x: 0, y: 10 }, reflation: { x: 100, y: 10 }, deflation: { x: 0, y: 60 }, stagflation: { x: 100, y: 60 }
	};
	const CELLS = [
		{ key: 'goldilocks', x: 6, y: 22, anchor: 'start' },
		{ key: 'reflation', x: 194, y: 22, anchor: 'end' },
		{ key: 'deflation', x: 6, y: 104, anchor: 'start' },
		{ key: 'stagflation', x: 194, y: 104, anchor: 'end' }
	] as const;
	const PHASE_EN: Record<string, string> = {
		expansion: 'Expansion', slowdown: 'Slowdown', contraction: 'Contraction', recovery: 'Recovery',
		stagflation: 'Stagflation', reflation: 'Reflation', deflation: 'Deflation', goldilocks: 'Goldilocks'
	};
	const phaseText = (m: RegimeMarketView) => (lang === 'en' ? (PHASE_EN[m.phase] ?? m.phase) : (m.phaseLabel || m.phase));
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
				const dx = ms.length > 1 ? (i - (ms.length - 1) / 2) * 34 : 0;
				out.push({ m, x: base.cx + dx, y: base.cy });
			});
		}
		return out;
	});
	const activeCells = $derived(new Set(placed.map((p) => p.m.cellKey)));
	const noQuadrant = $derived(view.markets.every((m) => !m.cellKey));
</script>

<section class="rp" aria-label={T('국면 평면', 'Regime plane')}>
	<svg class="rpPlane" viewBox="0 0 200 120" role="img"
		aria-label={T('성장×물가 국면 평면, KR·US 위치', 'growth×inflation regime plane with KR·US positions')}>
		{#each [...activeCells] as key}
			{#if key && cellRect[key]}
				<rect class="rpActive" x={cellRect[key].x} y={cellRect[key].y} width="100" height="50" />
			{/if}
		{/each}
		<line class="rpCross" x1="100" y1="10" x2="100" y2="110" />
		<line class="rpCross" x1="0" y1="60" x2="200" y2="60" />
		{#each CELLS as c}
			<text class={'rpQuadLbl' + (activeCells.has(c.key) ? ' on' : '')} x={c.x} y={c.y} text-anchor={c.anchor}>{quadName(c.key)}</text>
		{/each}
		<text class="rpAxisCue" x="100" y="8" text-anchor="middle">↑ {T('성장', 'growth')}</text>
		<text class="rpAxisCue" x="100" y="118" text-anchor="middle">{T('물가', 'inflation')} →</text>
		{#each placed as p (p.m.market)}
			<circle class="rpMark" cx={p.x} cy={p.y} r="5.5" />
			<text class="rpMarkLbl" x={p.x} y={p.y - 9} text-anchor="middle">{p.m.market}</text>
		{/each}
	</svg>

	<!-- 사이클(국면) + 전이 — 평면이 격자(위치)를 보여주므로 여긴 사이클 렌즈만(중복 제거). -->
	<div class="rpLens">
		{#each view.markets as m (m.market)}
			<div class="rpRow" title={m.description}>
				<b class="rpMkt">{m.market}</b>
				<span class="rpPhase">{T('사이클', 'cycle')} {phaseText(m)}</span>
				{#if m.transition}
					<i class="rpTrans" title={`${m.transition.triggered}/${m.transition.total} ${T('신호', 'signals')}`}
						>→ {T(m.transition.toKr, m.transition.toEn)}{#if m.transition.progressPct != null} {m.transition.progressPct}%{/if}</i>
				{/if}
			</div>
		{/each}
		{#if noQuadrant}
			<div class="rpNa">{T('국면 격자 미산출 — 사이클만', 'No regime grid — cycle only')}</div>
		{/if}
	</div>
</section>

<style>
	.rp { padding: 0 0 6px; display: flex; flex-direction: column; gap: 5px; min-width: 0; }
	/* 평면 — 좌우 완전 풀블리드: element 종횡비=viewBox(200:120)라 letterbox 0, 콘텐츠 x0→200 가 폭을 꽉 채움(왜곡 없음) */
	.rpPlane { display: block; width: 100%; aspect-ratio: 200 / 120; }
	.rpActive { fill: rgba(var(--amber-rgb),.08); }
	.rpCross { stroke: var(--bd); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 3; opacity: .85; }
	.rpQuadLbl { fill: var(--dim); font-size: 9px; font-weight: 700; opacity: .6; }
	.rpQuadLbl.on { fill: var(--amber); opacity: 1; }
	.rpAxisCue { fill: var(--dim); font-size: 7.5px; font-family: var(--mono); opacity: .8; }
	.rpMark { fill: var(--amber); stroke: var(--panel); stroke-width: 1.5; }
	.rpMarkLbl { fill: var(--fg); font-size: 9px; font-weight: 800; font-family: var(--mono); }

	.rpLens { display: grid; gap: 3px; padding: 0 8px; min-width: 0; }
	.rpRow { display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; gap: 6px; align-items: baseline; min-width: 0; }
	.rpRow b.rpMkt { color: var(--amber); font-family: var(--mono); font-size: 9px; font-weight: 800; }
	.rpPhase { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); font-size: 9.5px; }
	.rpTrans { font-style: normal; font-size: 8.5px; color: var(--dim); font-family: var(--mono); white-space: nowrap; border: 1px solid var(--bd); border-radius: 999px; padding: 0 5px; }
	.rpNa { color: var(--dim); font-size: 9px; }
</style>
