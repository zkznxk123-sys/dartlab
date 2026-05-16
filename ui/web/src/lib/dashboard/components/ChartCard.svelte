<script>
	import * as Chart from "$lib/ui/chart";
	import * as Card from "$lib/ui/card";
	import { BarChart, LineChart, PieChart } from "layerchart";

	let { title = "", subtitle = "", payload = null, loading = false, error = null, height = 280 } = $props();

	const spec = $derived(payload?.chartSpec || null);
	const kind = $derived(spec?.kind || null);

	const SLOT_TO_VAR = {
		primary: "--chart-1",
		secondary: "--chart-2",
		tertiary: "--chart-3",
		success: "--chart-4",
		warning: "--chart-5",
		destructive: "--chart-1",
		muted: "--muted-foreground",
	};
	function slotColor(slot) {
		return `var(${SLOT_TO_VAR[slot] || "--chart-1"})`;
	}

	const chartConfig = $derived.by(() => {
		if (!spec?.series) return {};
		const cfg = {};
		for (const s of spec.series) {
			cfg[s.key] = { label: s.label || s.key, color: slotColor(s.colorSlot) };
		}
		return cfg;
	});

	const rowData = $derived.by(() => {
		if (!spec) return [];
		const cats = spec.categories || [];
		return cats.map((c, i) => {
			const row = { _x: c };
			for (const s of spec.series || []) {
				row[s.key] = s.data?.[i] ?? null;
			}
			return row;
		});
	});

	const lineSeries = $derived(
		(spec?.series || []).map((s) => ({ key: s.key, label: s.label || s.key, color: slotColor(s.colorSlot) }))
	);

	const barSeries = $derived(
		(spec?.series || [])
			.filter((s) => (s.type || "bar") !== "line")
			.map((s) => ({ key: s.key, label: s.label || s.key, color: slotColor(s.colorSlot) }))
	);

	const pieData = $derived.by(() => {
		if (!spec?.series?.length) return [];
		const main = spec.series[0];
		const labels = main.labels || [];
		const values = main.data || [];
		return labels.map((lab, i) => ({ name: lab, value: values[i] ?? 0 }));
	});

	const waterfallRows = $derived.by(() => {
		if (kind !== "waterfall") return [];
		let acc = 0;
		return (spec.series || []).map((s) => {
			const v = typeof s.value === "number" ? s.value : 0;
			let start, end;
			if (s.measure === "absolute" || s.measure === "total") {
				start = 0;
				end = v;
				acc = v;
			} else {
				start = acc;
				end = acc + v;
				acc = end;
			}
			return { _x: s.label, key: s.key, value: v, start, end, color: slotColor(s.colorSlot) };
		});
	});
</script>

<Card.Root class="overflow-hidden">
	<Card.Header class="pb-2">
		<Card.Title class="text-sm font-semibold tracking-tight">{title || spec?.title || ""}</Card.Title>
		{#if subtitle}
			<Card.Description class="text-xs">{subtitle}</Card.Description>
		{/if}
	</Card.Header>
	<Card.Content class="pt-1">
		{#if loading}
			<div class="w-full animate-pulse rounded-md bg-muted" style="height: {height}px"></div>
		{:else if error}
			<div class="flex items-center justify-center text-xs text-destructive" style="height: {height}px">{error}</div>
		{:else if !spec}
			<div class="flex items-center justify-center text-xs text-muted-foreground" style="height: {height}px">데이터 없음</div>
		{:else}
			<div style="height: {height}px">
				<Chart.Container config={chartConfig} class="h-full w-full">
					{#if kind === "line"}
						<LineChart data={rowData} x="_x" series={lineSeries} legend />
					{:else if kind === "bar"}
						<BarChart
							data={rowData}
							x="_x"
							series={barSeries}
							seriesLayout={spec?.options?.stacked ? "stack" : "group"}
							legend
						/>
					{:else if kind === "pie"}
						<PieChart data={pieData} key="name" value="value" legend />
					{:else if kind === "waterfall"}
						<BarChart
							data={waterfallRows}
							x="_x"
							y={["start", "end"]}
							series={[{ key: "value", label: "변동", color: "var(--chart-1)" }]}
						/>
					{:else}
						<div class="flex items-center justify-center text-xs text-muted-foreground h-full">지원되지 않는 차트 kind: {kind}</div>
					{/if}
				</Chart.Container>
			</div>
		{/if}
	</Card.Content>
</Card.Root>
