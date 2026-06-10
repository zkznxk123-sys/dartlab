<script lang="ts">
	// 재무 분석 차트 — 막대+선·이중축·signed·stacked·refLine.
	// 계정명 범례 + Y축 숫자(좌/우) + X축 기간 + 호버 툴팁 → 해석 가능. 크게.
	import type { FinCard, Num } from '../data/terminalFinance';

	interface Props {
		card: FinCard;
		periods: string[];
		h?: number; // 우측 레일 등 밀도 컨텍스트용 compact 높이 (기본 152)
	}
	let { card, periods, h = 152 }: Props = $props();

	const W = 300;
	const H = $derived(h);
	const M = { t: 6, r: 30, b: 15, l: 34 };
	const plotW = W - M.l - M.r;
	const plotH = $derived(H - M.t - M.b);

	const fin = (v: Num): v is number => typeof v === 'number' && Number.isFinite(v);

	// ── 워터폴 (kind='waterfall') — steps 기반, series/periods 미사용 ──
	const isWf = $derived(card.kind === 'waterfall');
	const wfSteps = $derived(isWf ? ((card.steps ?? []).filter((s) => s.value != null) as { name: string; value: number; total?: boolean }[]) : []);
	// 누적 floating: flow = 이전 레벨에서 ±, total = 0 부터 자기 값 (소계 막대)
	const wfBars = $derived.by(() => {
		let lvl = 0;
		return wfSteps.map((s) => {
			const from = s.total ? 0 : lvl;
			const to = s.total ? s.value : lvl + s.value;
			lvl = to;
			return { name: s.name, value: s.value, from, to, total: !!s.total };
		});
	});

	const n = $derived(isWf ? wfSteps.length : periods.length);

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
		const pad = (hi - lo) * 0.1;
		return [lo - (lo < 0 ? pad : 0), hi + pad];
	}
	const leftExt = $derived.by<[number, number]>(() => {
		const vals: number[] = [];
		if (isWf) {
			for (const b of wfBars) vals.push(b.from, b.to);
			return extent(vals, true);
		}
		if (card.stacked && card.signed) {
			// signed 스택 — 양수합·음수합이 각각 위/아래 경계
			for (let i = 0; i < n; i++) {
				let pos = 0;
				let neg = 0;
				for (const b of barSeries) { const v = b.data[i]; if (fin(v)) { if (v > 0) pos += v; else neg += v; } }
				vals.push(pos, neg);
			}
		} else if (card.stacked) {
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

	// 조 단위 카드 자동 강등 — 좌축 최대 |값| < 0.5조면 억으로 표시 (중소형사 0.0조 범벅 방지).
	// 데이터·스케일 불변, 라벨 환산만. 우축(%) 시리즈는 무관.
	const unitScale = $derived.by<{ k: number; unit: string }>(() => {
		if (card.unit !== '조') return { k: 1, unit: card.unit };
		let m = 0;
		if (isWf) {
			for (const b of wfBars) m = Math.max(m, Math.abs(b.from), Math.abs(b.to));
		} else {
			for (const s of leftSeries) for (const v of s.data) if (fin(v)) m = Math.max(m, Math.abs(v));
		}
		return m > 0 && m < 0.5 ? { k: 1e4, unit: '억' } : { k: 1, unit: '조' };
	});

	const x = (i: number) => (n <= 1 ? M.l + plotW / 2 : M.l + (i / (n - 1)) * plotW);
	// 워터폴 전용 — 슬롯 중앙 배치 (양끝 클리핑 없음, step name 라벨 공간)
	const xw = (i: number) => M.l + ((i + 0.5) / Math.max(1, n)) * plotW;
	const yOf = (v: number, [lo, hi]: [number, number]) => M.t + plotH - ((v - lo) / (hi - lo || 1)) * plotH;
	const yL = (v: number) => yOf(v, leftExt);
	const yR = (v: number) => yOf(v, rightExt);

	// 바 폭 상한 22px — 기간 수가 적어도(연 5개) 빽빽한 밀도 유지 (뚱뚱한 바 금지)
	const slotW = $derived(n > 0 ? plotW / n : plotW);
	const groupW = $derived(Math.min(slotW * 0.72, (card.stacked || barSeries.length <= 1 ? 1 : barSeries.length) * 22));
	const barW = $derived(card.stacked || barSeries.length <= 1 ? groupW : groupW / barSeries.length);
	const wfBarW = $derived(Math.min(slotW * 0.62, 26));
	const wfColor = (b: { value: number; total: boolean }) => (b.total ? '#5b9bf0' : b.value >= 0 ? '#34d399' : '#f0616f');

	// Y 눈금 (상·중·하)
	function ticks([lo, hi]: [number, number]): number[] {
		if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo === hi) return [];
		const mid = (lo + hi) / 2;
		return [hi, mid, lo];
	}
	const leftTicks = $derived(ticks(leftExt));
	const rightTicks = $derived(rightSeries.length ? ticks(rightExt) : []);
	const fmtTick = (v: number) => {
		const a = Math.abs(v);
		if (a >= 1000) return Math.round(v).toLocaleString();
		if (a >= 10) return v.toFixed(0);
		if (a >= 1) return v.toFixed(1);
		return v.toFixed(2);
	};
	// X 라벨 (~5) — 워터폴은 step name 전부를 별도 렌더
	const xLabels = $derived.by(() => {
		if (n === 0 || isWf) return [] as number[];
		const out: number[] = [];
		const step = Math.max(1, Math.ceil(n / 4));
		for (let i = 0; i < n; i += step) out.push(i);
		if (out[out.length - 1] !== n - 1) out.push(n - 1);
		return out;
	});

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

	const primary = $derived(card.series[0]);
	const latestI = $derived.by(() => { if (isWf) return wfBars.length - 1; const d = primary?.data ?? []; for (let i = d.length - 1; i >= 0; i--) if (fin(d[i])) return i; return -1; });
	const fmtVal = (v0: number) => {
		const v = v0 * unitScale.k;
		const a = Math.abs(v);
		if (unitScale.unit === '억') return a >= 1000 ? Math.round(v).toLocaleString() : a >= 100 ? v.toFixed(0) : v.toFixed(1);
		if (card.unit === '조' || card.unit === '배') return a >= 100 ? v.toFixed(1) : v.toFixed(2);
		return a >= 100 ? v.toFixed(0) : v.toFixed(1);
	};
	// scaled = 좌축(조→억 환산 대상) 값 여부 — 우축(%·배율)은 원값 그대로
	const fmtTip = (v0: number, scaled = true) => {
		const v = scaled ? v0 * unitScale.k : v0;
		const a = Math.abs(v);
		if (a >= 1000) return Math.round(v).toLocaleString();
		return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
	};
	const zeroY = $derived(leftExt[0] < 0 && leftExt[1] > 0 ? yL(0) : null);

	// 호버
	let svgEl = $state<SVGSVGElement | null>(null);
	let hoverI = $state(-1);
	function onMove(e: MouseEvent) {
		if (!svgEl || n === 0) return;
		const r = svgEl.getBoundingClientRect();
		const plotL = r.left + (M.l / W) * r.width;
		const plotR = r.left + ((W - M.r) / W) * r.width;
		const frac = (e.clientX - plotL) / (plotR - plotL || 1);
		hoverI = Math.max(0, Math.min(n - 1, Math.round(frac * (n - 1))));
	}
	function onLeave() { hoverI = -1; }
	const headI = $derived(hoverI >= 0 ? hoverI : latestI);
	const headVal = $derived.by(() => {
		if (headI < 0) return null;
		if (isWf) return wfBars[headI]?.value ?? null;
		return primary && fin(primary.data[headI]) ? (primary.data[headI] as number) : null;
	});
	const headSuffix = $derived(hoverI >= 0 ? ' · ' + (isWf ? (wfBars[hoverI]?.name ?? '') : periods[hoverI]) : '');
</script>

<div class="mfc">
	<div class="mfcHead">
		<span class="mfcTitle">{card.title}</span>
		{#if headVal != null}
			<b class="mfcVal mono">{fmtVal(headVal)}<span class="mfcUnit">{unitScale.unit}{headSuffix}</span></b>
		{/if}
	</div>
	<div class="mfcLegend">
		{#if isWf}
			<span class="mfcLg"><i style="background:#34d399"></i>증가</span>
			<span class="mfcLg"><i style="background:#f0616f"></i>감소</span>
			<span class="mfcLg"><i style="background:#5b9bf0"></i>소계</span>
		{:else}
			{#each card.series as s (s.name)}
				<span class="mfcLg"><i style={`background:${s.color}`}></i>{s.name}{s.axis === 'r' ? '↗' : ''}</span>
			{/each}
		{/if}
	</div>
	<div class="mfcPlot">
		<svg bind:this={svgEl} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={card.title} onmousemove={onMove} onmouseleave={onLeave}>
			<!-- Y grid + 좌 눈금 숫자 -->
			{#each leftTicks as t (t)}
				<line x1={M.l} x2={W - M.r} y1={yL(t)} y2={yL(t)} stroke="#222a3a" stroke-width="0.6" />
				<text x={M.l - 3} y={yL(t) + 2.5} text-anchor="end" class="mfcAx">{fmtTick(t * unitScale.k)}</text>
			{/each}
			<!-- 우 눈금 숫자 -->
			{#each rightTicks as t (t)}
				<text x={W - M.r + 3} y={yR(t) + 2.5} text-anchor="start" class="mfcAx mfcAxR">{fmtTick(t)}</text>
			{/each}
			<!-- refLines -->
			{#each card.refLines ?? [] as rl (rl)}
				{#if rl >= leftExt[0] && rl <= leftExt[1]}<line x1={M.l} x2={W - M.r} y1={yL(rl)} y2={yL(rl)} stroke="#5b6b86" stroke-width="0.7" stroke-dasharray="3 2" />{/if}
			{/each}
			{#if zeroY != null}<line x1={M.l} x2={W - M.r} y1={zeroY} y2={zeroY} stroke="#3a4660" stroke-width="0.8" />{/if}
			{#if hoverI >= 0}<line x1={isWf ? xw(hoverI) : x(hoverI)} x2={isWf ? xw(hoverI) : x(hoverI)} y1={M.t} y2={M.t + plotH} stroke="#94a3b8" stroke-width="0.8" stroke-dasharray="2 2" />{/if}
			{#if isWf}
				<!-- 워터폴 — floating rect (total 은 0 부터) + 점선 connector + step name 라벨 -->
				{#each wfBars as b, i (i)}
					<rect x={xw(i) - wfBarW / 2} y={Math.min(yL(b.from), yL(b.to))} width={wfBarW} height={Math.max(0.8, Math.abs(yL(b.to) - yL(b.from)))} fill={wfColor(b)} fill-opacity={hoverI < 0 || hoverI === i ? 0.9 : 0.45} />
					{#if i < wfBars.length - 1}
						<line x1={xw(i) + wfBarW / 2} x2={xw(i + 1) - wfBarW / 2} y1={yL(b.to)} y2={yL(b.to)} stroke="#5b6b86" stroke-width="0.7" stroke-dasharray="2 2" />
					{/if}
					<text x={xw(i)} y={H - 4} text-anchor="middle" class="mfcAx">{b.name}</text>
				{/each}
			{:else}
				<!-- bars -->
				{#each periods as _p, i (i)}
					{#if card.stacked && card.signed}
						<!-- signed 스택 — 양수는 0 위로, 음수는 0 아래로 같은 부호끼리 누적 -->
						{#each barSeries as b, bi (b.name)}
							{@const v = b.data[i]}
							{#if fin(v) && v !== 0}
								{@const base = barSeries.slice(0, bi).reduce((a, s) => { const u = s.data[i]; return fin(u) && (u > 0) === (v > 0) ? a + u : a; }, 0)}
								<rect x={x(i) - barW / 2} y={Math.min(yL(base), yL(base + v))} width={barW} height={Math.max(0.5, Math.abs(yL(base + v) - yL(base)))} fill={b.color} fill-opacity={hoverI < 0 || hoverI === i ? 0.9 : 0.42} />
							{/if}
						{/each}
					{:else if card.stacked}
						{#each barSeries as b, bi (b.name)}
							{@const below = barSeries.slice(0, bi).reduce((a, s) => a + (fin(s.data[i]) ? (s.data[i] as number) : 0), 0)}
							{@const v = b.data[i]}
							{#if fin(v) && v > 0}<rect x={x(i) - barW / 2} y={Math.min(yL(below), yL(below + v))} width={barW} height={Math.max(0.5, Math.abs(yL(below + v) - yL(below)))} fill={b.color} fill-opacity={hoverI < 0 || hoverI === i ? 0.9 : 0.42} />{/if}
						{/each}
					{:else}
						{#each barSeries as b, bi (b.name)}
							{@const v = b.data[i]}
							{#if fin(v)}
								{@const base = zeroY != null ? zeroY : yL(leftExt[0])}
								{@const gx = x(i) - groupW / 2 + bi * barW + barW / 2}
								<rect x={gx - barW / 2} y={Math.min(base, yL(v))} width={Math.max(0.8, barW - 0.6)} height={Math.max(0.5, Math.abs(yL(v) - base))} fill={b.color} fill-opacity={hoverI < 0 || hoverI === i ? 0.88 : 0.4} />
							{/if}
						{/each}
					{/if}
				{/each}
				<!-- lines -->
				{#each leftLineSeries as l (l.name)}<path d={linePath(l.data, yL)} fill="none" stroke={l.color} stroke-width="1.7" />{/each}
				{#each rightSeries as r (r.name)}<path d={linePath(r.data, yR)} fill="none" stroke={r.color} stroke-width="1.7" />{/each}
				<!-- 호버 점 -->
				{#if hoverI >= 0}
					{#each card.series as s (s.name)}
						{@const v = s.data[hoverI]}
						{#if fin(v)}<circle cx={x(hoverI)} cy={(s.axis === 'r' ? yR : yL)(v)} r="2.4" fill={s.color} stroke="#0b1220" stroke-width="0.7" />{/if}
					{/each}
				{/if}
				<!-- X 라벨 -->
				{#each xLabels as i (i)}<text x={x(i)} y={H - 4} text-anchor="middle" class="mfcAx">{periods[i]}</text>{/each}
			{/if}
		</svg>
		{#if hoverI >= 0}
			<div class="mfcTip" style={n > 1 && hoverI / (n - 1) > 0.5 ? 'left:3px' : 'right:3px'}>
				{#if isWf}
					{@const b = wfBars[hoverI]}
					{#if b}
						<div class="mfcTipP mono">{b.name}</div>
						<div class="mfcTipR"><i style={`background:${wfColor(b)}`}></i><span class="mfcTipN">{b.total ? '소계' : '증감'}</span><b class="mono">{fmtTip(b.value)}{unitScale.unit}</b></div>
						{#if !b.total}<div class="mfcTipR"><i style="background:#5b6b86"></i><span class="mfcTipN">누계</span><b class="mono">{fmtTip(b.to)}{unitScale.unit}</b></div>{/if}
					{/if}
				{:else}
					<div class="mfcTipP mono">{periods[hoverI]}</div>
					{#each card.series as s (s.name)}
						{@const v = s.data[hoverI]}
						<div class="mfcTipR"><i style={`background:${s.color}`}></i><span class="mfcTipN">{s.name}</span><b class="mono">{fin(v) ? fmtTip(v as number, s.axis !== 'r') : '—'}</b></div>
					{/each}
				{/if}
			</div>
		{/if}
	</div>
</div>
