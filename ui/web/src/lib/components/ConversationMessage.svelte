<script>
	import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Circle, FileText, Loader2, Sparkles, Terminal, Search } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { groupActivities } from "$lib/agent/conversationModel.js";
	import SuggestedQuestions from "./SuggestedQuestions.svelte";

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
	<div class="flex justify-end py-2">
		<div class="max-w-[760px] rounded-2xl border border-white/10 bg-dl-bg-card px-4 py-2.5 text-[14px] font-medium text-dl-text">
			{text}
		</div>
	</div>
{:else}
	<div class="py-3">
		<div class="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-dl-text-dim">
			<span>DartLab</span>
			{#if message.loading}
				<Loader2 size={13} class="animate-spin text-dl-accent" />
			{/if}
		</div>
		<div class="space-y-3">
			{#each parts as part, idx (`${part.type}-${part.id || "part"}-${idx}`)}
				{#if part.type === "activity-group"}
					{@const isOpen = openGroups[part.id] ?? part.running}
					<div class="rounded-xl border border-dl-border/45 bg-dl-bg-card/55">
						<button
							type="button"
							class="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-dl-text-muted transition hover:bg-white/5"
							onclick={() => toggleGroup(part.id)}
						>
							<img
								src={part.avatar || "/avatar.png"}
								alt={part.label || ""}
								class="h-5 w-5 flex-shrink-0 rounded-full object-cover"
							/>
							{#if part.running}
								<Loader2 size={12} class="animate-spin text-amber-400" />
							{/if}
							<span class="flex-1 min-w-0">
								<span class="flex items-center gap-2">
									<span class="font-semibold text-dl-text">{part.label || "단계"}</span>
									<span class="text-dl-text-dim text-[10px]">{part.activities.length}단계</span>
									{#if part.running && typeof part.progress === "number"}
										<span class="flex-1 max-w-[120px] h-1 rounded-full bg-dl-bg-card-hover overflow-hidden">
											<span class="block h-full bg-dl-primary transition-all" style="width: {part.progress}%"></span>
										</span>
									{/if}
									{#if part.startedAt && part.lastAt && part.lastAt !== part.startedAt}
										<span class="text-dl-text-dim text-[10px]">{Math.max(1, Math.round((part.lastAt - part.startedAt) / 1000))}s</span>
									{/if}
								</span>
								{#if !isOpen && part.summary}
									<span class="block truncate text-dl-text-dim text-[11px]">— {part.summary}</span>
								{/if}
							</span>
							{#if isOpen}
								<ChevronDown size={13} class="text-dl-text-dim" />
							{:else}
								<ChevronRight size={13} class="text-dl-text-dim" />
							{/if}
						</button>
						{#if isOpen}
							<div class="space-y-1.5 border-t border-dl-border/40 px-3 py-2">
								{#each part.activities as activity (activity.id)}
									<div class="flex items-center gap-2 text-[12px] text-dl-text-dim">
										{#if activity.status === "running"}
											<Loader2 size={12} class="animate-spin text-amber-400" />
										{:else if activity.status === "error"}
											<AlertTriangle size={12} class="text-red-400" />
										{:else}
											<Circle size={11} class="text-dl-accent" />
										{/if}
										<span>{activity.summary}</span>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{:else if part.type === "tool"}
					<div class="rounded-lg border border-dl-border/50 bg-dl-bg-card/55 px-3 py-2">
						<div class="flex items-center gap-2 text-[12px] font-semibold text-dl-text-muted">
							{#if part.status === "running"}
								<Loader2 size={14} class="animate-spin text-amber-400" />
							{:else if part.status === "error"}
								<AlertTriangle size={14} class="text-red-400" />
							{:else}
								<CheckCircle2 size={14} class="text-emerald-400" />
							{/if}
							<Terminal size={14} />
							<span>{visibleToolName(part.name)}</span>
						</div>
						{#if part.summary}
							<div class="mt-1 text-[12px] text-dl-text-dim">{part.summary}</div>
						{/if}
						{#if part.artifacts?.length}
							<div class="mt-2 flex flex-wrap gap-1.5">
								{#each part.artifacts as artifact}
									{#if onOpenArtifact}
										<button
											type="button"
											class="rounded-full border border-dl-primary/25 bg-dl-primary/10 px-2 py-0.5 text-[11px] text-dl-primary-light hover:bg-dl-primary/20"
											onclick={() => onOpenArtifact(artifact)}
										>
											{artifact.fileName || artifact.name || "artifact"}
										</button>
									{:else}
										<a class="rounded-full border border-dl-primary/25 bg-dl-primary/10 px-2 py-0.5 text-[11px] text-dl-primary-light" href={artifact.url} target="_blank" rel="noreferrer">
											{artifact.fileName || artifact.name || "artifact"}
										</a>
									{/if}
								{/each}
							</div>
						{/if}
					</div>
				{:else if part.type === "failure"}
					<div class="rounded-lg border border-red-500/35 bg-red-500/10 px-3 py-2 text-[13px] text-red-200">
						<div class="flex items-center gap-2 font-semibold">
							<AlertTriangle size={14} />
							<span>{part.summary}</span>
						</div>
					</div>
				{:else if part.type === "text"}
					<div class="prose prose-invert max-w-none text-[15px] leading-7 text-dl-text">
						{@html renderMarkdown(part.content || "")}
					</div>
				{/if}
			{/each}
			{#if !parts.length && text}
				<div class="prose prose-invert max-w-none text-[15px] leading-7 text-dl-text">
					{@html renderMarkdown(text)}
				</div>
			{/if}
			{#if onOpenArtifact && message.artifacts?.length}
				<div class="grid gap-2 sm:grid-cols-2 pt-1">
					{#each message.artifacts as artifact}
						<button
							type="button"
							class="group flex items-center gap-2 rounded-xl border border-dl-border/45 bg-dl-bg-card/55 px-3 py-2 text-left transition hover:border-dl-primary/40 hover:bg-dl-bg-card"
							onclick={() => onOpenArtifact(artifact)}
						>
							<FileText size={14} class="flex-shrink-0 text-dl-accent" />
							<span class="min-w-0 flex-1">
								<span class="block truncate text-[12px] font-medium text-dl-text">{artifact.fileName || artifact.name || "artifact"}</span>
								{#if artifact.sizeBytes}
									<span class="block text-[10px] text-dl-text-dim">{Math.round((artifact.sizeBytes / 1024) * 10) / 10} KB · 패널에서 보기</span>
								{:else}
									<span class="block text-[10px] text-dl-text-dim">패널에서 보기</span>
								{/if}
							</span>
						</button>
					{/each}
				</div>
			{/if}
			{#if message.refs?.length || message.artifacts?.length}
				<div class="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-dl-text-dim">
					{#if message.refs?.length}
						<span class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/50 px-2 py-1">
							<Search size={12} /> 근거 {message.refs.length}개
						</span>
					{/if}
					{#if message.artifacts?.length}
						{#if onOpenArtifact}
							{#each message.artifacts as artifact}
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/50 px-2 py-1 hover:border-dl-primary/40 hover:text-dl-primary-light"
									onclick={() => onOpenArtifact(artifact)}
								>
									<FileText size={12} />
									<span class="max-w-[160px] truncate">{artifact.fileName || artifact.name || "파일"}</span>
								</button>
							{/each}
						{:else}
							<span class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/50 px-2 py-1">
								<FileText size={12} /> 파일 {message.artifacts.length}개
							</span>
						{/if}
					{/if}
				</div>
			{/if}
			{#if !message.loading && message.suggestedQuestions?.length}
				<SuggestedQuestions
					questions={message.suggestedQuestions}
					onSelect={onSuggestionSelect}
				/>
			{/if}
		</div>
		{#if !message.loading && onRegenerate}
			<div class="mt-2 flex gap-2 text-[11px] text-dl-text-dim">
				<button class="hover:text-dl-text-muted" onclick={onRegenerate}>다시 생성</button>
			</div>
		{/if}
	</div>
{/if}
