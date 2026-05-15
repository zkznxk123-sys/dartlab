<script>
	import LineChart from "./charts/LineChart.svelte";
	import BarChart from "./charts/BarChart.svelte";
	import PieChart from "./charts/PieChart.svelte";
	import WaterfallChart from "./charts/WaterfallChart.svelte";

	let { spec } = $props();
</script>

{#if spec?.kind === "line"}
	<LineChart {spec} />
{:else if spec?.kind === "bar"}
	<BarChart {spec} />
{:else if spec?.kind === "pie"}
	<PieChart {spec} />
{:else if spec?.kind === "waterfall"}
	<WaterfallChart {spec} />
{:else}
	<div class="flex items-center justify-center h-full text-xs text-muted-foreground">
		<span>지원되지 않는 차트 kind: {spec?.kind}</span>
	</div>
{/if}
