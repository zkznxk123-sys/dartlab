<script>
	import { renderMarkdown } from "$lib/markdown.js";
	import ActivityTimeline from "./ActivityTimeline.svelte";
	import ArtifactPreview from "./ArtifactPreview.svelte";
	import FailureNotice from "./FailureNotice.svelte";
	import SourceStrip from "./SourceStrip.svelte";
	import ToolRunCard from "./ToolRunCard.svelte";

	let {
		message,
		onOpenEvidence = null,
		onOpenArtifact = null,
		onRegenerate = null,
		onContentClick = null,
		contentEl = $bindable(),
	} = $props();

	const CHAT_TOOL_NAMES = new Set(["run_python", "compile_visual", "pythonExec"]);

	let parts = $derived(message.parts || []);
	let activityParts = $derived(parts.filter(part => part.type === "activity" || part.type === "failure"));
	let timelineParts = $derived(parts.filter(part => {
		if (part.type === "activity") return false;
		if (part.type === "failure") return true;
		if (part.type === "text") return Boolean(part.content);
		if (part.type === "tool") return CHAT_TOOL_NAMES.has(part.name);
		if (part.type === "artifact") return true;
		if (part.type === "source") return true;
		return false;
	}));
	let sourceRefs = $derived.by(() => {
		const refs = [];
		for (const part of parts) {
			for (const ref of part.refs || part.activity?.refs || part.evidenceRefs || []) {
				if (ref && !refs.includes(ref)) refs.push(ref);
			}
		}
		return refs;
	});
	let hasStructuredContent = $derived(activityParts.length || timelineParts.length);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="assistant-surface" class:text-dl-primary={message.error} bind:this={contentEl} onclick={onContentClick}>
	{#if hasStructuredContent}
		<ActivityTimeline parts={parts} loading={message.loading} {onOpenEvidence} />

		{#each timelineParts as part, idx (`${part.type}-${part.id || idx}-${idx}`)}
			{#if part.type === "failure"}
				<FailureNotice {part} {onRegenerate} />
			{:else if part.type === "text"}
				<div class="assistant-answer prose-dartlab">
					{@html renderMarkdown(part.content)}
				</div>
			{:else if part.type === "tool"}
				<ToolRunCard {part} />
			{:else if part.type === "artifact"}
				<ArtifactPreview {part} {onOpenArtifact} />
			{:else if part.type === "source"}
				<SourceStrip refs={part.refs || []} {onOpenEvidence} />
			{/if}
		{/each}
		<SourceStrip refs={sourceRefs} {onOpenEvidence} />
	{:else if message.text}
		<div class="assistant-answer prose-dartlab">
			{@html renderMarkdown(message.text)}
		</div>
	{/if}
</div>
