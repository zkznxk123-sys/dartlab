<script>
	import { AlertTriangle, ChevronDown, Loader2, Maximize2, X } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { groupLoops } from "$lib/agent/conversationModel.js";
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
	// 한 루프 = 한 카드. activity / tool / skill 모두 loop-card 의 row 로 흡수.
	let parts = $derived(groupLoops(rawParts));
	let text = $derived(message.text || message.content || "");
	let anyLoopRunning = $derived(parts.some((p) => p.type === "loop-card" && p.running));
	let showLoadingFooter = $derived(!!message.loading && !anyLoopRunning && !text);

	let openLoops = $state({});
	let openRows = $state({});
	let modalRow = $state(null);

	function toggleLoop(id) {
		openLoops = { ...openLoops, [id]: !openLoops[id] };
	}
	function toggleRow(id) {
		openRows = { ...openRows, [id]: !openRows[id] };
	}
	function openRowModal(row) {
		modalRow = row;
	}
	function closeRowModal() {
		modalRow = null;
	}

	function visibleToolName(name) {
		return String(name || "tool");
	}

	const ROW_LONG_THRESHOLD = 1500;
	function isLongRow(row) {
		const r = row?.result;
		const code = row?.args?.code;
		if (typeof code === "string" && code.length > ROW_LONG_THRESHOLD) return true;
		if (!r) return false;
		if (typeof r.stdout === "string" && r.stdout.length > ROW_LONG_THRESHOLD) return true;
		if (typeof r.body === "string" && r.body.length > ROW_LONG_THRESHOLD) return true;
		if (Array.isArray(r.tableHead) && r.tableRows > 10) return true;
		return false;
	}

	function shortText(s, max = 600) {
		if (typeof s !== "string") return "";
		return s.length > max ? s.slice(0, max) + "\n…" : s;
	}

	function fenceCode(s, lang = "python") {
		return "```" + lang + "\n" + (s || "") + "\n```";
	}

	function jsonPretty(obj, max = 600) {
		try {
			const s = JSON.stringify(obj, null, 2);
			return shortText(s, max);
		} catch {
			return String(obj);
		}
	}

	function isRunPython(name) {
		return /^run[_\s]?python$/i.test(String(name || ""));
	}
	function isRead(name) {
		return /^read$/i.test(String(name || ""));
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
			{#if part.type === "loop-card"}
				{@const isOpen = openLoops[part.id] ?? part.running}
				<div class="loop-card {part.status === 'error' ? 'loop-card-error' : ''}">
					<button
						type="button"
						class="loop-card-header"
						onclick={() => toggleLoop(part.id)}
						title={isOpen ? "접기" : "펼치기"}
					>
						{#if part.running}
							<Loader2 size={12} class="animate-spin loop-card-icon-running" />
						{:else if part.status === "error"}
							<AlertTriangle size={12} class="loop-card-icon-error" />
						{:else}
							<span class="loop-card-dot"></span>
						{/if}
						<span class="loop-card-label">{part.label}</span>
						{#if part.toolCount > 0}
							<span class="loop-card-count">{part.toolCount}건{part.errorCount > 0 ? ` · ${part.errorCount} 실패` : ""}</span>
						{/if}
						{#if part.summary}
							<span class="loop-card-summary">· {part.summary}</span>
						{/if}
						<ChevronDown
							size={11}
							class="loop-card-chevron transition-transform {isOpen ? '' : '-rotate-90'}"
						/>
					</button>
					{#if isOpen}
						<ul class="loop-card-rows">
							{#each part.rows as row, ri (row.id || `row-${ri}`)}
								{#if row.kind === "activity"}
									<li class="loop-row loop-row-activity {row.status === 'error' ? 'loop-row-error' : ''}">
										<span class="loop-row-num">{ri + 1}</span>
										<span class="loop-row-text">{row.summary || ""}</span>
									</li>
								{:else}
									{@const isRowOpen = openRows[row.id] ?? false}
									{@const tooLong = isLongRow(row)}
									<li class="loop-row loop-row-call {row.status === 'error' ? 'loop-row-error' : ''}">
										<button
											type="button"
											class="loop-row-head"
											onclick={() => toggleRow(row.id)}
										>
											{#if row.status === "running"}
												<Loader2 size={11} class="animate-spin" />
											{:else if row.status === "error"}
												<AlertTriangle size={11} class="loop-row-icon-error" />
											{:else}
												<span class="loop-row-dot"></span>
											{/if}
											<span class="loop-row-name">{visibleToolName(row.name)}</span>
											{#if row.summary}
												<span class="loop-row-summary">· {row.summary}</span>
											{/if}
											<span class="loop-row-actions">
												{#if tooLong}
													<button
														type="button"
														class="loop-row-modal"
														onclick={(e) => { e.stopPropagation(); openRowModal(row); }}
														title="모달로 전체 보기"
													>
														<Maximize2 size={10} />
													</button>
												{/if}
												<ChevronDown
													size={11}
													class="loop-row-chevron transition-transform {isRowOpen ? '' : '-rotate-90'}"
												/>
											</span>
										</button>
										{#if isRowOpen}
											<div class="loop-row-body">
												{#if row.args && Object.keys(row.args).length}
													<div class="loop-row-section-label">
														<span>입력</span>
													</div>
													{#if isRunPython(row.name) && typeof row.args.code === "string"}
														<div class="loop-row-out prose-dartlab">{@html renderMarkdown(fenceCode(shortText(row.args.code, ROW_LONG_THRESHOLD), "python"))}</div>
													{:else if isRead(row.name) && row.args.target}
														<div class="loop-row-meta-line">
															{row.args.target}
															{#if row.args.startLine || row.args.endLine}
																<span class="text-dl-text-dim"> · L{row.args.startLine || 1}-L{row.args.endLine || ""}</span>
															{/if}
														</div>
													{:else}
														<pre class="loop-row-pre">{jsonPretty(row.args)}</pre>
													{/if}
												{/if}

												{#if row.result}
													<div class="loop-row-section-label">
														<span>출력</span>
														{#if row.result.durationMs}
															<span class="loop-row-meta">{row.result.durationMs}ms</span>
														{/if}
													</div>
													{#if row.result.markdown}
														<div class="loop-row-out prose-dartlab">{@html renderMarkdown(row.result.markdown)}</div>
													{:else}
														{#if row.result.values}
															<pre class="loop-row-pre">{jsonPretty(row.result.values)}</pre>
														{/if}
														{#if Array.isArray(row.result.tableHead) && row.result.tableHead.length}
															<div class="loop-row-meta">
																테이블 {row.result.tableRows ?? row.result.tableHead.length}행 (앞 {row.result.tableHead.length} 표시)
															</div>
															<pre class="loop-row-pre">{jsonPretty(row.result.tableHead, 800)}</pre>
														{/if}
														{#if row.result.stdout}
															<div class="loop-row-meta">stdout</div>
															<pre class="loop-row-pre">{shortText(row.result.stdout, 600)}</pre>
														{/if}
														{#if row.result.stderr}
															<div class="loop-row-meta loop-row-stderr">stderr</div>
															<pre class="loop-row-pre">{shortText(row.result.stderr, 600)}</pre>
														{/if}
														{#if row.result.body}
															<pre class="loop-row-pre">{shortText(row.result.body, 800)}</pre>
														{/if}
													{/if}
												{/if}

												{#if row.error}
													<div class="loop-row-section-label loop-row-stderr">에러</div>
													<pre class="loop-row-pre">{shortText(String(row.error), 600)}</pre>
												{/if}

												{#if row.refs?.length}
													<div class="loop-row-meta">ref: {row.refs.length}개</div>
												{/if}

												{#if row.artifacts?.length}
													<div class="loop-row-artifacts">
														{#each row.artifacts as artifact}
															<button
																type="button"
																class="artifact-preview"
																onclick={() => onOpenArtifact?.(artifact)}
															>
																<span class="artifact-url">{artifact.fileName || artifact.name || "artifact"}</span>
															</button>
														{/each}
													</div>
												{/if}
											</div>
										{/if}
									</li>
								{/if}
							{/each}
						</ul>
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
		{#if showLoadingFooter}
			<div class="assistant-loading">
				<Loader2 size={12} class="animate-spin" />
				<span>준비 중...</span>
			</div>
		{/if}
		{#if onOpenArtifact && message.artifacts?.length}
			<div class="loop-row-artifacts pt-1">
				{#each message.artifacts as artifact}
					<button
						type="button"
						class="artifact-preview"
						onclick={() => onOpenArtifact(artifact)}
					>
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

{#if modalRow}
	<div
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn"
		onclick={(e) => { if (e.target === e.currentTarget) closeRowModal(); }}
		role="presentation"
	>
		<div class="surface-overlay w-full max-w-3xl max-h-[85vh] bg-dl-bg-card border border-dl-border rounded-2xl shadow-2xl overflow-hidden flex flex-col">
			<div class="flex items-center justify-between border-b border-dl-border/40 px-5 py-3">
				<div class="flex items-center gap-2">
					<span class="text-[12px] font-semibold text-dl-text">{visibleToolName(modalRow.name)}</span>
					{#if modalRow.summary}
						<span class="text-[11px] text-dl-text-dim">{modalRow.summary}</span>
					{/if}
				</div>
				<button class="p-1 rounded-lg text-dl-text-dim hover:text-dl-text" onclick={closeRowModal} aria-label="닫기">
					<X size={16} />
				</button>
			</div>
			<div class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
				{#if modalRow.args && Object.keys(modalRow.args).length}
					<div class="text-[11px] font-medium text-dl-text-muted">입력</div>
					{#if isRunPython(modalRow.name) && typeof modalRow.args.code === "string"}
						<div class="prose-dartlab">{@html renderMarkdown(fenceCode(modalRow.args.code, "python"))}</div>
					{:else}
						<pre class="loop-row-pre">{jsonPretty(modalRow.args, 8000)}</pre>
					{/if}
				{/if}
				{#if modalRow.result}
					<div class="text-[11px] font-medium text-dl-text-muted">출력</div>
					{#if modalRow.result.markdown}
						<div class="prose-dartlab">{@html renderMarkdown(modalRow.result.markdown)}</div>
					{:else}
						{#if modalRow.result.values}
							<pre class="loop-row-pre">{jsonPretty(modalRow.result.values, 4000)}</pre>
						{/if}
						{#if Array.isArray(modalRow.result.tableHead) && modalRow.result.tableHead.length}
							<pre class="loop-row-pre">{jsonPretty(modalRow.result.tableHead, 8000)}</pre>
						{/if}
						{#if modalRow.result.stdout}
							<div class="text-[10px] text-dl-text-dim">stdout</div>
							<pre class="loop-row-pre">{modalRow.result.stdout}</pre>
						{/if}
						{#if modalRow.result.stderr}
							<div class="text-[10px] text-dl-primary-light">stderr</div>
							<pre class="loop-row-pre">{modalRow.result.stderr}</pre>
						{/if}
						{#if modalRow.result.body}
							<pre class="loop-row-pre">{modalRow.result.body}</pre>
						{/if}
					{/if}
				{/if}
				{#if modalRow.error}
					<div class="text-[11px] font-medium text-dl-primary-light">에러</div>
					<pre class="loop-row-pre">{modalRow.error}</pre>
				{/if}
			</div>
		</div>
	</div>
{/if}
