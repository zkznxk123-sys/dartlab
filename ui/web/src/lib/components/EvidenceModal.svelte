<!--
	근거 모달 — Context / Snapshot / Tool Event 상세 보기.
-->
<script>
	import { cn } from "$lib/utils.js";
	import { formatEvidenceLabel, formatToolLabel } from "$lib/ai/evidenceLabels.js";
	import { X, Database, Brain, FileText, Code } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { describeCallArgs, cleanErrorMessage } from "$lib/ai/toolSummary.js";

	let { message, openModal = $bindable(null), modalType = $bindable("context") } = $props();

	let contextTab = $state("rendered");

	let isSystemPrompt = $derived(modalType === "system");
	let isUserContent = $derived(modalType === "userContent");
	let isContext = $derived(modalType === "context");
	let isSnapshot = $derived(modalType === "snapshot");
	let isTool = $derived(modalType === "tool");

	let ctx = $derived(isContext ? message.contexts?.[openModal] : null);
	let toolEvent = $derived(isTool ? message.toolEvents?.[openModal] : null);
	let toolIsError = $derived(isTool && toolEvent?.type === "result" && toolEvent?.status === "error");

	let toolHeaderLabel = $derived.by(() => {
		if (!toolEvent) return "";
		const base = toolEvent.label || formatToolLabel(toolEvent.name);
		return toolEvent.type === "call" ? `${base} 호출` : `${base} 결과`;
	});

	let toolInArgs = $derived(
		isTool && toolEvent ? describeCallArgs(toolEvent.type === "call" ? toolEvent : findMatchingCall(toolEvent)) : ""
	);

	function findMatchingCall(resultEv) {
		if (!resultEv || !message.toolEvents) return null;
		for (let i = openModal - 1; i >= 0; i--) {
			const ev = message.toolEvents[i];
			if (ev?.type === "call" && ev?.id === resultEv.id) return ev;
		}
		return null;
	}

	let toolOutText = $derived.by(() => {
		if (!isTool || !toolEvent || toolEvent.type !== "result") return "";
		const r = toolEvent.result;
		if (typeof r === "string") return r;
		if (r === null || r === undefined) return "";
		try { return JSON.stringify(r, null, 2); } catch { return String(r); }
	});

	let modalTitle = $derived(
		isSnapshot ? "핵심 수치 (원본 데이터)" :
		isSystemPrompt ? "레거시 런타임 입력" :
		isUserContent ? "레거시 사용자 입력" :
		isTool ? toolHeaderLabel :
		formatEvidenceLabel(ctx?.label || ctx?.module, ctx?.label || "")
	);

	let modalText = $derived(
		isSnapshot ? JSON.stringify(message.snapshot, null, 2) :
		isSystemPrompt ? message.systemPrompt :
		isUserContent ? message.userContent :
		ctx?.text
	);

	function close() { openModal = null; }
</script>

{#if openModal !== null}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-[300] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn"
		onclick={(e) => { if (e.target === e.currentTarget) close(); }}
		onkeydown={(e) => { if (e.key === "Escape") close(); }}
	>
		<div class="w-full max-w-3xl max-h-[80vh] mx-4 bg-dl-bg-card border border-dl-border rounded-2xl shadow-2xl shadow-black/40 overflow-hidden flex flex-col">
			<div class="flex-shrink-0 border-b border-dl-border/50">
				<div class="flex items-center justify-between px-5 pt-4 pb-3">
					<div class="flex items-center gap-2 text-[14px] font-medium text-dl-text">
						{#if isSnapshot}
							<Database size={15} class="text-dl-success flex-shrink-0" />
						{:else if isSystemPrompt}
							<Brain size={15} class="text-dl-primary-light flex-shrink-0" />
						{:else if isUserContent}
							<FileText size={15} class="text-dl-accent flex-shrink-0" />
						{:else}
							<Database size={15} class="flex-shrink-0" />
						{/if}
						<span>{modalTitle}</span>
						{#if isSystemPrompt}
							<span class="text-[10px] text-dl-text-dim">({modalText?.length?.toLocaleString()}자)</span>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						{#if isContext}
							<div class="flex items-center gap-0.5 bg-dl-bg-darker rounded-lg p-0.5">
								<button
									class={cn(
										"flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] transition-colors",
										contextTab === "rendered"
											? "bg-dl-bg-card text-dl-text shadow-sm"
											: "text-dl-text-dim hover:text-dl-text-muted"
									)}
									onclick={() => contextTab = "rendered"}
								>
									<FileText size={11} />
									렌더링
								</button>
								<button
									class={cn(
										"flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] transition-colors",
										contextTab === "raw"
											? "bg-dl-bg-card text-dl-text shadow-sm"
											: "text-dl-text-dim hover:text-dl-text-muted"
									)}
									onclick={() => contextTab = "raw"}
								>
									<Code size={11} />
									원문
								</button>
							</div>
						{/if}
						<button
							class="p-1 rounded-lg text-dl-text-dim hover:text-dl-text hover:bg-white/5 transition-colors"
							onclick={close}
						>
							<X size={18} />
						</button>
					</div>
				</div>

				{#if isContext && message.contexts?.length > 1}
					<div class="px-5 pb-2.5 overflow-x-auto scrollbar-hide">
						<div class="flex items-center gap-1.5">
							{#each message.contexts as _, idx}
								<button
									class={cn(
										"px-2.5 py-1 rounded-lg text-[11px] whitespace-nowrap transition-colors flex-shrink-0",
										idx === openModal
											? "bg-dl-primary/20 text-dl-primary-light font-medium"
											: "bg-dl-bg-darker text-dl-text-dim hover:text-dl-text-muted hover:bg-dl-bg-darker/80"
									)}
									onclick={() => { openModal = idx; }}
								>
									{formatEvidenceLabel(message.contexts[idx].label || message.contexts[idx].module, message.contexts[idx].label || "컨텍스트")}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				{#if !isContext && !isSnapshot && !isTool}
					<div class="px-5 pb-2.5">
						<div class="flex items-center gap-1.5">
							{#if message.systemPrompt}
								<button
									class={cn(
										"px-2.5 py-1 rounded-lg text-[11px] whitespace-nowrap transition-colors flex-shrink-0",
										isSystemPrompt
											? "bg-dl-primary/20 text-dl-primary-light font-medium"
											: "bg-dl-bg-darker text-dl-text-dim hover:text-dl-text-muted"
									)}
									onclick={() => { modalType = "system"; }}
								>
									레거시 런타임 입력
								</button>
							{/if}
							{#if message.userContent}
								<button
									class={cn(
										"px-2.5 py-1 rounded-lg text-[11px] whitespace-nowrap transition-colors flex-shrink-0",
										isUserContent
											? "bg-dl-accent/20 text-dl-accent font-medium"
											: "bg-dl-bg-darker text-dl-text-dim hover:text-dl-text-muted"
									)}
									onclick={() => { modalType = "userContent"; }}
								>
									레거시 사용자 입력
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<div class="flex-1 overflow-y-auto px-5 pb-5 min-h-0">
				{#if isContext && contextTab === "rendered"}
					<div class="prose-dartlab text-[13px] leading-[1.7] pt-3">
						{@html renderMarkdown(ctx?.text)}
					</div>
				{:else if isTool}
					<div class="mt-3 space-y-3">
						<div class={cn(
							"rounded-xl border p-3",
							toolIsError ? "border-dl-primary/30 bg-dl-primary/[0.06]" : "border-dl-border/40 bg-dl-bg-darker"
						)}>
							<div class="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-dl-text-dim">
								{toolEvent?.type === "call" ? "호출" : (toolIsError ? "오류" : "결과")}
							</div>
							<div class="text-[12px] leading-relaxed text-dl-text-muted">
								{#if toolEvent?.type === "call"}
									LLM이 이 도구를 호출하며 다음 조건을 지정했습니다.
								{:else if toolIsError}
									<span class="text-dl-primary-light font-medium">데이터 없음 — 도구가 에러를 반환했습니다.</span>
								{:else}
									도구 실행 결과가 반환되었습니다.
								{/if}
							</div>
							{#if toolInArgs}
								<div class="mt-2 text-[11px] text-dl-text">{toolInArgs}</div>
							{/if}
							{#if toolEvent?.summary}
								<div class="mt-2 text-[12px] text-dl-text">{toolEvent.summary}</div>
							{/if}
						</div>

						{#if toolEvent?.type === "result"}
							<div class="rounded-xl border border-dl-border/40 bg-dl-bg-darker p-3">
								<div class="mb-2 text-[10px] uppercase tracking-wide text-dl-text-dim">반환 내용</div>
								{#if toolIsError}
									<div class="text-[12px] leading-relaxed text-dl-primary-light/90">
										{cleanErrorMessage(toolOutText)}
									</div>
								{:else if toolOutText}
									<div class="prose-dartlab text-[12px] leading-[1.65]">
										{@html renderMarkdown(toolOutText)}
									</div>
								{:else}
									<div class="text-[11px] text-dl-text-dim">반환 내용이 비어 있습니다.</div>
								{/if}
							</div>
						{/if}

						<details class="rounded-xl border border-dl-border/30 bg-dl-bg-darker/70 p-2">
							<summary class="cursor-pointer text-[10px] uppercase tracking-wide text-dl-text-dim hover:text-dl-text-muted">원본 JSON 보기 (디버그)</summary>
							<pre class="mt-2 text-[11px] text-dl-text-muted font-mono overflow-x-auto whitespace-pre-wrap break-words">{JSON.stringify(toolEvent, null, 2)}</pre>
						</details>
					</div>
				{:else}
					<pre class="text-[11px] text-dl-text-muted font-mono bg-dl-bg-darker rounded-xl p-4 mt-3 overflow-x-auto whitespace-pre-wrap break-words">{modalText}</pre>
				{/if}
			</div>
		</div>
	</div>
{/if}
