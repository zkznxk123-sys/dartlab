<!--
	Sparkline — primitive array (numbers + null) 의 inline 시각화.
	min-max 정규화 → polyline path. 상승/하락 색 분기. null gap 처리.
-->
<script>
	let { data = [], class: klass = "", strokeWidth = 1.5 } = $props();

	const W = 100;
	const H = 30;
	const padY = 2;

	const nums = $derived(data.map((v) => (typeof v === "number" && Number.isFinite(v) ? v : null)));
	const finite = $derived(nums.filter((v) => v !== null));
	const min = $derived(finite.length ? Math.min(...finite) : 0);
	const max = $derived(finite.length ? Math.max(...finite) : 1);
	const range = $derived(max - min || 1);

	function pointsPath(arr) {
		if (arr.length < 2) return "";
		const n = arr.length - 1;
		let d = "";
		let pen = false;
		arr.forEach((v, i) => {
			if (v === null) {
				pen = false;
				return;
			}
			const x = (i / n) * W;
			const y = H - padY - ((v - min) / range) * (H - 2 * padY);
			d += pen ? ` L${x.toFixed(2)} ${y.toFixed(2)}` : `M${x.toFixed(2)} ${y.toFixed(2)}`;
			pen = true;
		});
		return d;
	}

	const path = $derived(pointsPath(nums));
	const direction = $derived(
		finite.length >= 2
			? finite[finite.length - 1] >= finite[0]
				? "up"
				: "down"
			: "flat"
	);
	const stroke = $derived(
		direction === "up" ? "var(--color-dl-success)" : direction === "down" ? "var(--color-dl-primary)" : "var(--color-dl-text-muted)"
	);
	const lastPt = $derived.by(() => {
		for (let i = nums.length - 1; i >= 0; i--) {
			if (nums[i] !== null) {
				const x = (i / Math.max(1, nums.length - 1)) * W;
				const y = H - padY - ((nums[i] - min) / range) * (H - 2 * padY);
				return { x, y };
			}
		}
		return null;
	});
</script>

<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" class={klass} aria-hidden="true">
	{#if path}
		<path d={path} fill="none" stroke={stroke} stroke-width={strokeWidth} stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
		{#if lastPt}
			<circle cx={lastPt.x} cy={lastPt.y} r="1.6" fill={stroke} />
		{/if}
	{/if}
</svg>
