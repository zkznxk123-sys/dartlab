<script>
	import { FileText } from "lucide-svelte";

	let { part, onOpenArtifact = null } = $props();
	let artifact = $derived(part.artifact || {});
	let label = $derived(artifact.label || artifact.name || artifact.id || "artifact");
	let url = $derived(artifact.url || "");
</script>

<button class="artifact-preview" type="button" onclick={() => onOpenArtifact?.(artifact)}>
	<FileText size={13} />
	<span>{label}</span>
	{#if url}<span class="artifact-url">{url}</span>{/if}
</button>
