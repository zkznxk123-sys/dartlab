<!--
	Waterfall — P&L / Cash Flow 분해 시각화. 누적 stepping bar (Editorial 톤).
	props:
	  steps: Array<{ label, value, type: 'total' | 'positive' | 'negative' }>
	    · total: 절대값 (시작·중간 subtotal·끝). y=0 부터 그림.
	    · positive: 증가 step. 이전 누적 위에 쌓음.
	    · negative: 감소 step. 이전 누적 아래로 내려감.
-->
<script>
	import { isFiniteNum, fmtKrw, linearScale } from "./util.js";

	let {
		steps = [],
		height = 260,
		unit = "",
		format = null,
	} = $props();

	const W = 800;
	const PAD = { top: 24, right: 32, bottom: 40, left: 64 };

	const fmt = $derived(format || fmtKrw);

	// 각 step 의 누적 cumulative 계산 (running)
	const computed = $derived.by(() => {
		let running = 0;
		const out = [];
		for (const s of steps) {
			if (!isFiniteNum(s.value)) {
				out.push({ ...s, start: running, end: running, valid: false });
				continue;
			}
			if (s.type === "total") {
				running = s.value;
				out.push({ ...s, start: 0, end: s.value, valid: true });
			} else if (s.type === "positive") {
				const next = running + s.value;
				out.push({ ...s, start: running, end: next, valid: true });
				running = next;
			} else if (s.type === "negative") {
				// negative 는 value 가 양수든 음수든 빼는 의미. 화면엔 |value| 의 하강 표시.
				const delta = Math.abs(s.value);
				const next = running - delta;
				out.push({ ...s, start: running, end: next, valid: true, displayDelta: -delta });
				running = next;
			} else {
				out.push({ ...s, start: running, end: running, valid: false });
			}
		}
		return out;
	});

	const yDomain = $derived.by(() => {
		const vals = [];
		for (const c of computed) {
			if (isFiniteNum(c.start)) vals.push(c.start);
			if (isFiniteNum(c.end)) vals.push(c.end);
		}
		vals.push(0);
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const range = max - min || 1;
		return [min - range * 0.04, max + range * 0.08];
	});

	const yScale = $derived(linearScale(yDomain, [height - PAD.bottom, PAD.top]));
	const N = $derived(computed.length);
	const innerW = $derived(W - PAD.left - PAD.right);
	const step = $derived(innerW / Math.max(1, N));
	const barW = $derived(step * 0.62);
	function xLeft(i) {
		return PAD.left + step * i + (step - barW) / 2;
	}

	const yTicks = $derived.by(() => {
		const [lo, hi] = yDomain;
		const s = (hi - lo) / 4;
		return [0, 1, 2, 3, 4].map((i) => lo + s * i);
	});

	const COLOR = {
		total: "var(--ed-text)",
		positive: "var(--ed-up)",
		negative: "var(--ed-down)",
	};
</script>

<div class="w-full">
	<svg viewBox="0 0 {W} {height}" preserveAspectRatio="xMidYMid meet" class="w-full block">
		{#each yTicks as t}
			{@const y = yScale(t)}
			<line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--ed-line)" stroke-width="0.5" />
			<text x={PAD.left - 6} y={y + 3.5} text-anchor="end" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{fmt(t)}
			</text>
		{/each}

		{@const y0 = yScale(0)}
		<line x1={PAD.left} x2={W - PAD.right} y1={y0} y2={y0} stroke="var(--ed-text-3)" stroke-width="0.5" />

		<!-- Connectors (이전 end → 다음 start 가로 점선) -->
		{#each computed as c, i}
			{#if i > 0 && c.valid && computed[i - 1].valid && c.type !== "total"}
				{@const prevEnd = computed[i - 1].end}
				{@const prevX = xLeft(i - 1) + barW}
				{@const currX = xLeft(i)}
				<line x1={prevX} y1={yScale(prevEnd)} x2={currX} y2={yScale(prevEnd)} stroke="var(--ed-text-3)" stroke-width="0.5" stroke-dasharray="2 2" opacity="0.6" />
			{/if}
		{/each}

		<!-- Bars -->
		{#each computed as c, i}
			{#if c.valid}
				{@const yTop = yScale(Math.max(c.start, c.end))}
				{@const yBot = yScale(Math.min(c.start, c.end))}
				{@const color = COLOR[c.type] || "var(--ed-text-2)"}
				<rect x={xLeft(i)} y={yTop} width={barW} height={Math.max(0.5, yBot - yTop)} fill={color} opacity={c.type === "total" ? 0.88 : 0.82} />
				<!-- 값 label 위에 -->
				<text x={xLeft(i) + barW / 2} y={yTop - 4} text-anchor="middle" font-size="9.5" fill="var(--ed-text)" font-family="var(--font-num)" font-weight="500">
					{c.type === "negative" ? "−" : c.type === "positive" ? "+" : ""}{fmt(c.type === "negative" ? Math.abs(c.value) : c.value)}
				</text>
			{/if}
			<text x={xLeft(i) + barW / 2} y={height - 22} text-anchor="middle" font-size="10" fill="var(--ed-text-2)" font-family="var(--font-body)">
				{c.label}
			</text>
		{/each}
	</svg>
</div>
