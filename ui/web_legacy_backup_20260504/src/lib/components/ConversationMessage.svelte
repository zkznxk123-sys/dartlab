<script>
	import { AlertTriangle, CheckCircle2, Circle, FileText, Loader2, Terminal, Search } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";

	let {
		message,
		onRegenerate,
		onEditResend,
	} = $props();

	let parts = $derived(Array.isArray(message.parts) ? message.parts : []);
	let text = $derived(message.text || message.content || "");

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
				{#if part.type === "activity"}
					<div class="flex items-center gap-2 text-[12px] text-dl-text-dim">
						{#if part.status === "running"}
							<Loader2 size={13} class="animate-spin text-amber-400" />
						{:else}
							<Circle size={12} class="text-dl-accent" />
						{/if}
						<span>{part.summary}</span>
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
									<a class="rounded-full border border-dl-primary/25 bg-dl-primary/10 px-2 py-0.5 text-[11px] text-dl-primary-light" href={artifact.url} target="_blank" rel="noreferrer">
										{artifact.fileName || artifact.name || "artifact"}
									</a>
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
			{#if message.refs?.length || message.artifacts?.length}
				<div class="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-dl-text-dim">
					{#if message.refs?.length}
						<span class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/50 px-2 py-1">
							<Search size={12} /> 근거 {message.refs.length}개
						</span>
					{/if}
					{#if message.artifacts?.length}
						<span class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/50 px-2 py-1">
							<FileText size={12} /> 파일 {message.artifacts.length}개
						</span>
					{/if}
				</div>
			{/if}
		</div>
		{#if !message.loading && onRegenerate}
			<div class="mt-2 flex gap-2 text-[11px] text-dl-text-dim">
				<button class="hover:text-dl-text-muted" onclick={onRegenerate}>다시 생성</button>
			</div>
		{/if}
	</div>
{/if}
