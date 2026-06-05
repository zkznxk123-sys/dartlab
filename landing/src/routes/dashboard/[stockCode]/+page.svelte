<script lang="ts">
	import CompanyWorkspace from '$lib/company/CompanyWorkspace.svelte';

	let { data }: { data: { stockCode: string } } = $props();
</script>

<svelte:head>
	<title>{data.stockCode} 대시보드 · dartlab</title>
</svelte:head>

<CompanyWorkspace code={data.stockCode} />
