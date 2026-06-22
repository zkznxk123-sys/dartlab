<script lang="ts">
	import type { MacroPoint, MacroSeriesDef } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';
	import { applyTransform, ymdToMs, NBER_RECESSIONS, type MacroTransform } from '../lib/macroBoard';

	// 재사용 시계열 차트 — mini(보드 행)·full(확대) 양용. 무판정: 단일 중립선 + 침체음영 + 기준선.
	// 색은 방향/상태 아님(녹/적 valence 0). brush = 공유 날짜 커서(부모가 brushMs 전파 → 전 차트 연결).
	interface Props {
		points: MacroPoint[];
		def: MacroSeriesDef;
		transform: MacroTransform;
		windowYears: number; // 0 = 전체
		lang: Lang;
		compact?: boolean; // true=미니(축 없음), false=확대(축·readout)
		shading?: boolean; // 침체 음영(US 시리즈만 적용)
		refLine?: number | null; // 기준선(예: 물가 2%, 스프레드/z 0)
		brushMs?: number | null; // 공유 커서 위치(ms). null=없음
		onBrush?: (ms: number | null) => void;
	}
	let { points, def, transform, windowYears, lang, compact = false, shading = false, refLine = null, brushMs = null, onBrush }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	const W = $derived(compact ? 200 : 760);
	const H = $derived(compact ? 40 : 300);
	const padL = $derived(compact ? 1 : 44);
	const padR = $derived(compact ? 1 : 12);
	const padT = $derived(compact ? 3 : 12);
	const padB = $derived(compact ? 3 : 22);

	const data = $derived(applyTransform(points, transform, def, windowYears));
	const displayUnit = $derived(transform === 'z' ? 'σ' : transform === 'yoy' && !def.yoy ? '%' : def.unit);
	const digits = $derived(transform === 'z' ? 2 : def.digits ?? 1);

	const xmin = $derived(data.length ? ymdToMs(data[0].d) : 0);
	const xmax = $derived(data.length ? ymdToMs(data[data.length - 1].d) : 1);
	const yRange = $derived.by(() => {
		if (!data.length) return { lo: 0, hi: 1 };
		let lo = data[0].v, hi = data[0].v;
		for (const p of data) { if (p.v < lo) lo = p.v; if (p.v > hi) hi = p.v; }
		if (refLine != null) { lo = Math.min(lo, refLine); hi = Math.max(hi, refLine); }
		if (lo === hi) { lo -= 1; hi += 1; }
		const pad = (hi - lo) * 0.08;
		return { lo: lo - pad, hi: hi + pad };
	});
	const xOf = (ms: number) => padL + ((ms - xmin) / Math.max(1, xmax - xmin)) * (W - padL - padR);
	const yOf = (v: number) => H - padB - ((v - yRange.lo) / (yRange.hi - yRange.lo)) * (H - padT - padB);

	const path = $derived(data.length ? data.map((p, k) => `${k ? 'L' : 'M'}${xOf(ymdToMs(p.d)).toFixed(1)} ${yOf(p.v).toFixed(1)}`).join(' ') : '');
	const areaPath = $derived(data.length ? `${path} L${xOf(xmax).toFixed(1)} ${(H - padB).toFixed(1)} L${xOf(xmin).toFixed(1)} ${(H - padB).toFixed(1)} Z` : '');

	// 침체 음영 — US(fred) 시리즈 + shading prop. 가시 범위와 겹치는 NBER 구간만 사각형.
	const shadeRects = $derived.by(() => {
		if (!shading || def.src !== 'fred' || !data.length) return [];
		const out: { x: number; w: number }[] = [];
		for (const [s, e] of NBER_RECESSIONS) {
			const sm = Math.max(ymdToMs(s), xmin);
			const em = Math.min(ymdToMs(e), xmax);
			if (em > sm) out.push({ x: xOf(sm), w: xOf(em) - xOf(sm) });
		}
		return out;
	});

	// brush 커서 — brushMs 에 가장 가까운 점.
	const cursor = $derived.by(() => {
		if (brushMs == null || !data.length) return null;
		let best = data[0], bd = Math.abs(ymdToMs(data[0].d) - brushMs);
		for (const p of data) { const d = Math.abs(ymdToMs(p.d) - brushMs); if (d < bd) { bd = d; best = p; } }
		return { x: xOf(ymdToMs(best.d)), y: yOf(best.v), v: best.v, d: best.d };
	});
	const last = $derived(data.length ? data[data.length - 1] : null);

	// y축 눈금(full) — lo/mid/hi 3개.
	const yTicks = $derived(compact ? [] : [yRange.lo + (yRange.hi - yRange.lo) * 0.08, (yRange.lo + yRange.hi) / 2, yRange.hi - (yRange.hi - yRange.lo) * 0.08]);
	// x축 연도 라벨(full).
	const xYears = $derived.by(() => {
		if (compact || !data.length) return [] as { x: number; label: string }[];
		const out: { x: number; label: string }[] = [];
		let prevY = '';
		for (const p of data) {
			const y = p.d.slice(0, 4);
			if (y !== prevY) { out.push({ x: xOf(ymdToMs(p.d)), label: y }); prevY = y; }
		}
		// 너무 빽빽하면 솎음(최대 8개).
		const step = Math.ceil(out.length / 8);
		return out.filter((_, k) => k % step === 0);
	});

	const fmt = (v: number) => v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

	let svgEl = $state<SVGSVGElement | null>(null);
	function handleMove(e: PointerEvent) {
		if (!onBrush || !svgEl || !data.length) return;
		const rect = svgEl.getBoundingClientRect();
		const px = ((e.clientX - rect.left) / rect.width) * W; // viewBox x
		const frac = (px - padL) / Math.max(1, W - padL - padR);
		const ms = xmin + Math.max(0, Math.min(1, frac)) * (xmax - xmin);
		onBrush(ms);
	}
</script>

<svg
	bind:this={svgEl}
	class={'msc' + (compact ? ' compact' : '')}
	viewBox={`0 0 ${W} ${H}`}
	preserveAspectRatio="none"
	role="img"
	aria-label={`${T(def.kr, def.en)} ${transform}`}
	onpointermove={onBrush ? handleMove : undefined}
	onpointerleave={onBrush ? () => onBrush?.(null) : undefined}
>
	{#if data.length}
		{#each shadeRects as r (r.x)}<rect class="mscShade" x={r.x} y={padT} width={Math.max(0.5, r.w)} height={H - padT - padB} />{/each}
		{#if !compact}
			{#each yTicks as t (t)}<line class="mscGrid" x1={padL} y1={yOf(t)} x2={W - padR} y2={yOf(t)} /><text class="mscYLbl" x={padL - 5} y={yOf(t) + 3} text-anchor="end">{fmt(t)}</text>{/each}
			{#each xYears as xy (xy.label)}<text class="mscXLbl" x={xy.x} y={H - 6} text-anchor="middle">{xy.label}</text>{/each}
		{/if}
		{#if refLine != null && refLine >= yRange.lo && refLine <= yRange.hi}
			<line class="mscRef" x1={padL} y1={yOf(refLine)} x2={W - padR} y2={yOf(refLine)} />
			{#if !compact}<text class="mscRefLbl" x={W - padR} y={yOf(refLine) - 3} text-anchor="end">{fmt(refLine)}{displayUnit}</text>{/if}
		{/if}
		<path class="mscArea" d={areaPath} />
		<path class="mscLine" d={path} />
		{#if last}<circle class="mscNow" cx={xOf(xmax)} cy={yOf(last.v)} r={compact ? 2 : 3} />{/if}
		{#if cursor}
			<line class="mscCursor" x1={cursor.x} y1={padT} x2={cursor.x} y2={H - padB} />
			<circle class="mscCursorDot" cx={cursor.x} cy={cursor.y} r={compact ? 2.5 : 3.5} />
			{#if !compact}
				<text class="mscCursorLbl" x={Math.min(cursor.x + 6, W - padR - 60)} y={padT + 12}>{cursor.d.slice(0, 4)}-{cursor.d.slice(4, 6)} · {fmt(cursor.v)}{displayUnit}</text>
			{/if}
		{/if}
	{:else}
		<text class="mscEmpty" x={W / 2} y={H / 2} text-anchor="middle">{T('데이터 없음', 'no data')}</text>
	{/if}
</svg>

<style>
	.msc { display: block; width: 100%; height: 100%; overflow: visible; touch-action: none; }
	.msc.compact { height: 40px; }
	.mscShade { fill: rgba(255, 255, 255, 0.05); }
	.mscGrid { stroke: var(--bd); stroke-width: 1; vector-effect: non-scaling-stroke; opacity: 0.5; }
	.mscRef { stroke: var(--dim); stroke-width: 1; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; opacity: 0.7; }
	.mscRefLbl { fill: var(--dim); font-size: 9px; font-family: var(--mono); }
	.mscArea { fill: var(--good); opacity: 0.06; }
	.mscLine { fill: none; stroke: var(--good); stroke-width: 1.4; vector-effect: non-scaling-stroke; stroke-linejoin: round; }
	.mscNow { fill: var(--good); }
	.mscYLbl, .mscXLbl { fill: var(--dimmer); font-size: 9px; font-family: var(--mono); }
	.mscCursor { stroke: var(--amber); stroke-width: 1; vector-effect: non-scaling-stroke; opacity: 0.7; }
	.mscCursorDot { fill: var(--amber); }
	.mscCursorLbl { fill: var(--txt); font-size: 10px; font-family: var(--mono); }
	.mscEmpty { fill: var(--dimmer); font-size: 10px; }
</style>
