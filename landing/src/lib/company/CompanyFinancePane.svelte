<script lang="ts">
	import FinanceStatementPane from '$lib/components/viewer/FinanceStatementPane.svelte';

	let { code, corpName = '' }: { code: string; corpName?: string } = $props();
</script>

<FinanceStatementPane {code} {corpName} />
