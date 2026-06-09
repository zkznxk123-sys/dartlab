<script lang="ts">
	// 밀집 재무 미니차트 — small multiple. 막대+선·이중축·signed·stacked·refLine.
	// 높이 ~92px 플롯 + 헤더(타이틀·색점·최신값). 큰 차트 대신 정보밀도 우선.
	import type { FinCard, Num } from '../data/terminalFinance';

	interface Props {
		card: FinCard;
		periods: string[];
	}
	let { card, periods }: Props = $props();

	const W = 300;
	const H = 92;
	const PADT = 5;
	const PADB = 11;
	const plotH = H - PADT - PADB;

	const fin = (v: Num): v is number => typeof v === 'number' && Number.isFinite(v);
	const n = $derived(periods.length);

	// 축 분리
	const leftSeries = $derived(card.series.filter((s) => s.axis !== 'r'));
	const rightSeries = $derived(card.series.filter((s) => s.axis === 'r'));
	const barSeries = $derived(leftSeries.filter((s) => s.type === 'bar'));
	const leftLineSeries = $derived(leftSeries.filter((s) => s.type === 'line'));

	function extent(vals: number[], incl0: boolean): [number, number] {
		const arr = incl0 ? [...vals, 0] : vals;
		if (!arr.length) return [0, 1];
		let lo = Math.min(...arr);
		let hi = Math.max(...arr);
		if (lo === hi) { hi = lo + Math.abs(lo || 1); lo = Math.min(lo, 0); }
		const pad = (hi - lo) * 0.08;
		return [lo - (lo < 0 ? pad : 0), hi + pad];
	}

	// 좌축 범위: 막대(스택 고려) + 좌선
	const leftExt = $derived.by<[number, number]>(() => {
		const vals: number[] = [];
		if (card.stacked) {
			for (let i = 0; i < n; i++) {
				let s = 0;
				for (const b of barSeries) { const v = b.data[i]; if (fin(v)) s += v; }
				vals.push(s);
			}
		} else {
			for (const b of barSeries) for (const v of b.data) if (fin(v)) vals.push(v);
		}
		for (const l of leftLineSeries) for (const v of l.data) if (fin(v)) vals.push(v);
		return extent(vals, true);
	});
	const rightExt = $derived.by<[number, number]>(() => {
		const vals: number[] = [];
		for (const s of rightSeries) for (const v of s.data) if (fin(v)) vals.push(v);
		return extent(vals, true);
	});

	const x = (i: number) => (n <= 1 ? W / 2 : 4 + (i / (n - 1)) * (W - 8));
	const yOf = (v: number, [lo, hi]: [number, number]) => PADT + plotH - ((v - lo) / (hi - lo || 1)) * plotH;
	const yL = (v: number) => yOf(v, leftExt);
	const yR = (v: number) => yOf(v, rightExt);

	// 막대 폭
	const slotW = $derived(n > 0 ? (W - 8) / n : W);
	const groupW = $derived(slotW * 0.74);
	const barW = $derived(card.stacked || barSeries.length <= 1 ? groupW : groupW / barSeries.length);

	function linePath(data: Num[], yfn: (v: number) => number): string {
		let d = '';
		let pen = false;
		data.forEach((v, i) => {
			if (!fin(v)) { pen = false; return; }
			d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${yfn(v).toFixed(1)} `;
			pen = true;
		});
		return d.trim();
	}

	// 헤더 최신값 (primary = 첫 시리즈) — 최신 non-null + 직전 대비
	const primary = $derived(card.series[0]);
	const latest = $derived.by(() => {
		const d = primary?.data ?? [];
		for (let i = d.length - 1; i >= 0; i--) if (fin(d[i])) {
			let prev: number | null = null;
			for (let j = i - 1; j >= 0; j--) if (fin(d[j])) { prev = d[j] as number; break; }
			return { v: d[i] as number, prev };
		}
		return null;
	});
	const fmtVal = (v: number) => {
		if (card.unit === '조') return v.toFixed(2);
		if (card.unit === '배') return v.toFixed(2);
		return v.toFixed(1);
	};
	const zeroY = $derived(leftExt[0] < 0 && leftExt[1] > 0 ? yL(0) : null);
</script>

<div class="mfc">
	<div class="mfcHead">
		<span class="mfcTitle">{card.title}</span>
		<span class="mfcDots">
			{#each card.series as s (s.name)}<i style={`background:${s.color}`} title={s.name}></i>{/each}
		</span>
		{#if latest}
			<b class="mfcVal mono">{fmtVal(latest.v)}<span class="mfcUnit">{card.unit}</span></b>
		{/if}
	</div>
	<svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={card.title}>
		<!-- refLines -->
		{#each card.refLines ?? [] as rl (rl)}
			{#if rl >= leftExt[0] && rl <= leftExt[1]}
				<line x1="0" x2={W} y1={yL(rl)} y2={yL(rl)} stroke="#475569" stroke-width="0.6" stroke-dasharray="3 3" />
			{/if}
		{/each}
		<!-- zero baseline (signed) -->
		{#if zeroY != null}<line x1="0" x2={W} y1={zeroY} y2={zeroY} stroke="#3a4660" stroke-width="0.7" />{/if}
		<!-- bars -->
		{#each periods as _p, i (i)}
			{#if card.stacked}
				{@const baseY = yL(Math.max(0, leftExt[0]))}
				{#each barSeries as b, bi (b.name)}
					{@const stackBelow = barSeries.slice(0, bi).reduce((a, s) => a + (fin(s.data[i]) ? (s.data[i] as number) : 0), 0)}
					{@const v = b.data[i]}
					{#if fin(v) && v > 0}
						{@const y0 = yL(stackBelow)}
						{@const y1 = yL(stackBelow + v)}
						<rect x={x(i) - barW / 2} y={Math.min(y0, y1)} width={barW} height={Math.max(0.5, Math.abs(y1 - y0))} fill={b.color} fill-opacity="0.9" />
					{/if}
				{/each}
			{:else}
				{#each barSeries as b, bi (b.name)}
					{@const v = b.data[i]}
					{#if fin(v)}
						{@const base = zeroY != null ? zeroY : yL(leftExt[0])}
						{@const yv = yL(v)}
						{@const gx = x(i) - groupW / 2 + bi * barW + barW / 2}
						<rect x={gx - barW / 2} y={Math.min(base, yv)} width={Math.max(0.6, barW - 0.6)} height={Math.max(0.5, Math.abs(yv - base))} fill={b.color} fill-opacity="0.88" />
					{/if}
				{/each}
			{/if}
		{/each}
		<!-- left lines -->
		{#each leftLineSeries as l (l.name)}
			<path d={linePath(l.data, yL)} fill="none" stroke={l.color} stroke-width="1.5" />
		{/each}
		<!-- right axis lines -->
		{#each rightSeries as r (r.name)}
			<path d={linePath(r.data, yR)} fill="none" stroke={r.color} stroke-width="1.5" stroke-dasharray={r.type === 'line' ? '0' : '0'} />
		{/each}
	</svg>
	<div class="mfcAxis mono"><span>{periods[0] ?? ''}</span><span>{periods[periods.length - 1] ?? ''}</span></div>
</div>
