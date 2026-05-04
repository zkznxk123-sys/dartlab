<script>
	import { Link2 } from "lucide-svelte";

	let { refs = [], onOpenEvidence = null } = $props();
</script>

{#if refs?.length}
	<button class="source-strip" type="button" onclick={() => onOpenEvidence?.("tool-results", 0)}>
		<Link2 size={12} />
		<span>근거 refs {refs.length}개</span>
	</button>
{/if}
