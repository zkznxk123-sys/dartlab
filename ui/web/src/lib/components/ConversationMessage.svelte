<script>
	import { AlertTriangle, ChevronDown, FileText, Loader2 } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { groupActivities } from "$lib/agent/conversationModel.js";
	import SuggestedQuestions from "./SuggestedQuestions.svelte";
	import ViewSpecRenderer from "$lib/ai/ViewSpecRenderer.svelte";

	let {
		message,
		onRegenerate,
		onEditResend,
		onOpenArtifact,
		onSuggestionSelect,
	} = $props();

	let rawParts = $derived(Array.isArray(message.parts) ? message.parts : []);
	let parts = $derived(groupActivities(rawParts));
	let text = $derived(message.text || message.content || "");

	let openGroups = $state({});
	function toggleGroup(id) {
		openGroups = { ...openGroups, [id]: !openGroups[id] };
	}

	function visibleToolName(name) {
		return String(name || "tool").replaceAll("_", " ");
	}
</script>

{#if message.role === "user"}
	<div class="msg-user flex justify-end py-1.5">
		<div class="max-w-[720px] rounded-md bg-dl-bg-card-hover px-4 py-2 text-[14px] leading-[22px] text-dl-text">
			{text}
		</div>
	</div>
{:else}
	<div class="assistant-surface py-2.5">
		{#each parts as part, idx (`${part.type}-${part.id || "part"}-${idx}`)}
			{#if part.type === "activity-group"}
				{@const isOpen = openGroups[part.id] ?? part.running}
				<div class="assistant-activity">
					<button
						type="button"
						class="assistant-activity-head"
						onclick={() => toggleGroup(part.id)}
					>
						{#if part.running}
							<Loader2 size={11} class="assistant-activity-head-icon animate-spin" />
						{/if}
						<span class="assistant-activity-status">{part.label || "단계"}</span>
						<span class="assistant-activity-latest">{part.summary || ""}</span>
						<ChevronDown
							size={12}
							class="flex-shrink-0 ml-auto text-dl-text-dim transition-transform {isOpen ? '' : '-rotate-90'}"
						/>
					</button>
					{#if isOpen}
						<ol class="assistant-activity-list">
							{#each part.activities as activity, ai (activity.id)}
								<li class="assistant-activity-row">
									<span class="text-[10px] text-dl-text-dim w-4 inline-block">{ai + 1}</span>
									<span class={activity.status === "error" ? "activity-error" : ""}>{activity.summary}</span>
								</li>
							{/each}
						</ol>
					{/if}
				</div>
			{:else if part.type === "tool"}
				<div class="tool-run-card {part.status === 'error' ? 'tool-run-error' : ''}">
					<div class="tool-run-header">
						{#if part.status === "running"}
							<Loader2 size={12} class="animate-spin tool-run-terminal" />
						{:else if part.status === "error"}
							<AlertTriangle size={12} class="text-red-400" />
						{/if}
						<span class="tool-run-name">{visibleToolName(part.name)}</span>
						{#if part.summary}
							<span class="tool-run-summary">{part.summary}</span>
						{/if}
					</div>
					{#if part.artifacts?.length}
						<div class="tool-run-body">
							<div class="flex flex-wrap gap-1.5">
								{#each part.artifacts as artifact}
									<button
										type="button"
										class="artifact-preview"
										onclick={() => onOpenArtifact?.(artifact)}
									>
										<FileText size={12} />
										<span class="artifact-url">{artifact.fileName || artifact.name || "artifact"}</span>
									</button>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{:else if part.type === "failure"}
				<div class="failure-notice">
					<AlertTriangle size={14} />
					<div class="failure-copy">
						<div class="failure-title">{part.summary}</div>
					</div>
				</div>
			{:else if part.type === "view-spec"}
				<ViewSpecRenderer view={part.spec} {onOpenArtifact} />
			{:else if part.type === "text"}
				<div class="assistant-answer prose-dartlab">
					{@html renderMarkdown(part.content || "")}
				</div>
			{/if}
		{/each}
		{#if !parts.length && text}
			<div class="assistant-answer prose-dartlab">
				{@html renderMarkdown(text)}
			</div>
		{/if}
		{#if onOpenArtifact && message.artifacts?.length}
			<div class="flex flex-wrap gap-1.5 pt-1">
				{#each message.artifacts as artifact}
					<button
						type="button"
						class="artifact-preview"
						onclick={() => onOpenArtifact(artifact)}
					>
						<FileText size={12} />
						<span class="artifact-url">{artifact.fileName || artifact.name || "artifact"}</span>
					</button>
				{/each}
			</div>
		{/if}
		{#if !message.loading && message.suggestedQuestions?.length}
			<SuggestedQuestions
				questions={message.suggestedQuestions}
				onSelect={onSuggestionSelect}
			/>
		{/if}
		{#if !message.loading && onRegenerate}
			<div class="mt-2 flex gap-2 text-[11px] text-dl-text-dim">
				<button class="hover:text-dl-text-muted" onclick={onRegenerate}>다시 생성</button>
			</div>
		{/if}
	</div>
{/if}
