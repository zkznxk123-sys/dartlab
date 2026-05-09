<script>
	import { AlertTriangle, ChevronDown, FileText, Loader2, Maximize2, Search, X } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { groupActivities, groupTools } from "$lib/agent/conversationModel.js";
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
	// activity-group 으로 묶은 후, 연속 조사도구 (ReadSkill/Capability/SkillBody) 도 묶음.
	let parts = $derived(groupTools(groupActivities(rawParts)));
	let text = $derived(message.text || message.content || "");
	// 푸터 indicator 는 다른 진행 표현이 없을 때만 (도구 spinner / streaming text 가 진행 전담).
	let anyToolRunning = $derived(parts.some((p) => p.type === "tool" && p.status === "running"));
	let showLoadingFooter = $derived(!!message.loading && !anyToolRunning && !text);

	let openGroups = $state({});
	function toggleGroup(id) {
		openGroups = { ...openGroups, [id]: !openGroups[id] };
	}

	function visibleToolName(name) {
		// underscore 유지 — grid 레이아웃에서 wrap 방지.
		return String(name || "tool");
	}

	let openTools = $state({});
	function toggleTool(id) {
		openTools = { ...openTools, [id]: !openTools[id] };
	}

	let modalTool = $state(null);
	function openToolModal(part) { modalTool = part; }
	function closeToolModal() { modalTool = null; }

	const TOOL_LONG_THRESHOLD = 1500;
	function isLongOutput(part) {
		const r = part?.result;
		const code = part?.args?.code;
		if (typeof code === "string" && code.length > TOOL_LONG_THRESHOLD) return true;
		if (!r) return false;
		if (typeof r.stdout === "string" && r.stdout.length > TOOL_LONG_THRESHOLD) return true;
		if (typeof r.body === "string" && r.body.length > TOOL_LONG_THRESHOLD) return true;
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
			{:else if part.type === "tool-research-group"}
				{@const isOpen = openGroups[part.id] ?? false}
				<div class="tool-research-group {part.hasError ? 'tool-research-group-error' : ''}">
					<button
						type="button"
						class="tool-research-head"
						onclick={() => toggleGroup(part.id)}
						title={isOpen ? "접기" : "펼치기"}
					>
						{#if part.running}
							<Loader2 size={12} class="animate-spin" />
						{:else}
							<Search size={12} class="text-dl-text-dim" />
						{/if}
						<span class="tool-research-label">사전조사</span>
						<span class="tool-research-count">{part.calls.length}회</span>
						{#if part.lastSummary}
							<span class="tool-research-latest">· {part.lastSummary}</span>
						{/if}
						<ChevronDown
							size={11}
							class="flex-shrink-0 ml-auto text-dl-text-dim transition-transform {isOpen ? '' : '-rotate-90'}"
						/>
					</button>
					{#if isOpen}
						<ul class="tool-research-list">
							{#each part.calls as call (call.id)}
								<li>
									<button
										type="button"
										class="tool-research-row {call.status === 'error' ? 'tool-research-row-error' : ''}"
										onclick={() => openToolModal(call)}
										title="상세 보기"
									>
										{#if call.status === "running"}
											<Loader2 size={11} class="animate-spin flex-shrink-0" />
										{:else if call.status === "error"}
											<AlertTriangle size={11} class="text-red-400 flex-shrink-0" />
										{:else}
											<span class="tool-research-row-dot"></span>
										{/if}
										<span class="tool-research-row-name">{visibleToolName(call.name)}</span>
										{#if call.summary}
											<span class="tool-research-row-summary">· {call.summary}</span>
										{/if}
										<Maximize2 size={10} class="flex-shrink-0 ml-auto text-dl-text-dim opacity-0 group-hover:opacity-100" />
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{:else if part.type === "tool"}
				{@const isOpen = openTools[part.id] ?? false}
				{@const tooLong = isLongOutput(part)}
				<div class="tool-run-card {part.status === 'error' ? 'tool-run-error' : ''}">
					<button
						type="button"
						class="tool-run-header"
						onclick={() => toggleTool(part.id)}
						title={isOpen ? "접기" : "펼치기"}
					>
						{#if part.status === "running"}
							<Loader2 size={12} class="animate-spin tool-run-terminal" />
						{:else if part.status === "error"}
							<AlertTriangle size={12} class="text-red-400" />
						{/if}
						<span class="tool-run-name">{visibleToolName(part.name)}</span>
						{#if part.summary}
							<span class="tool-run-summary">{part.summary}</span>
						{/if}
						<ChevronDown
							size={11}
							class="flex-shrink-0 ml-auto text-dl-text-dim transition-transform {isOpen ? '' : '-rotate-90'}"
						/>
					</button>

					{#if isOpen}
						<div class="tool-run-body">
							{#if part.args && Object.keys(part.args).length}
								<div class="tool-section-label">
									<span>입력</span>
									{#if tooLong}
										<button
											type="button"
											class="tool-modal-trigger"
											onclick={() => openToolModal(part)}
											title="전체 보기 (모달)"
										>
											<Maximize2 size={11} />
											<span>전체</span>
										</button>
									{/if}
								</div>
								{#if isRunPython(part.name) && typeof part.args.code === "string"}
									<div class="tool-out prose-dartlab">{@html renderMarkdown(fenceCode(shortText(part.args.code, TOOL_LONG_THRESHOLD), "python"))}</div>
								{:else if isRead(part.name) && part.args.target}
									<div class="tool-meta-line">
										{part.args.target}
										{#if part.args.startLine || part.args.endLine}
											<span class="text-dl-text-dim"> · L{part.args.startLine || 1}-L{part.args.endLine || ""}</span>
										{/if}
									</div>
								{:else}
									<pre class="tool-args">{jsonPretty(part.args)}</pre>
								{/if}
							{/if}

							{#if part.result}
								<div class="tool-section-label">
									<span>출력</span>
									{#if part.result.durationMs}
										<span class="text-[10px] text-dl-text-dim">{part.result.durationMs}ms</span>
									{/if}
								</div>
								{#if part.result.values}
									<pre class="tool-args">{jsonPretty(part.result.values)}</pre>
								{/if}
								{#if Array.isArray(part.result.tableHead) && part.result.tableHead.length}
									<div class="text-[10px] text-dl-text-dim mt-1">
										테이블 {part.result.tableRows ?? part.result.tableHead.length}행 (앞 {part.result.tableHead.length} 표시)
									</div>
									<pre class="tool-args">{jsonPretty(part.result.tableHead, 800)}</pre>
								{/if}
								{#if part.result.stdout}
									<div class="text-[10px] text-dl-text-dim mt-1">stdout</div>
									<pre class="tool-args">{shortText(part.result.stdout, 600)}</pre>
								{/if}
								{#if part.result.stderr}
									<div class="text-[10px] text-dl-primary-light mt-1">stderr</div>
									<pre class="tool-args">{shortText(part.result.stderr, 600)}</pre>
								{/if}
								{#if part.result.body}
									<pre class="tool-args">{shortText(part.result.body, 800)}</pre>
								{/if}
							{/if}

							{#if part.error}
								<div class="tool-section-label text-dl-primary-light">에러</div>
								<pre class="tool-args">{shortText(String(part.error), 600)}</pre>
							{/if}

							{#if part.refs?.length}
								<div class="text-[10px] text-dl-text-dim mt-1">
									ref: {part.refs.length}개
								</div>
							{/if}

							{#if part.artifacts?.length}
								<div class="flex flex-wrap gap-1.5 mt-2">
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
							{/if}
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
		{#if showLoadingFooter}
			<div class="assistant-loading">
				<Loader2 size={12} class="animate-spin" />
				<span>준비 중...</span>
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

{#if modalTool}
	<div
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn"
		onclick={(e) => { if (e.target === e.currentTarget) closeToolModal(); }}
		role="presentation"
	>
		<div class="surface-overlay w-full max-w-3xl max-h-[85vh] bg-dl-bg-card border border-dl-border rounded-2xl shadow-2xl overflow-hidden flex flex-col">
			<div class="flex items-center justify-between border-b border-dl-border/40 px-5 py-3">
				<div class="flex items-center gap-2">
					<span class="text-[12px] font-semibold text-dl-text">{visibleToolName(modalTool.name)}</span>
					{#if modalTool.summary}
						<span class="text-[11px] text-dl-text-dim">{modalTool.summary}</span>
					{/if}
				</div>
				<button class="p-1 rounded-lg text-dl-text-dim hover:text-dl-text" onclick={closeToolModal} aria-label="닫기">
					<X size={16} />
				</button>
			</div>
			<div class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
				{#if modalTool.args && Object.keys(modalTool.args).length}
					<div class="text-[11px] font-medium text-dl-text-muted">입력</div>
					{#if isRunPython(modalTool.name) && typeof modalTool.args.code === "string"}
						<div class="prose-dartlab">{@html renderMarkdown(fenceCode(modalTool.args.code, "python"))}</div>
					{:else}
						<pre class="tool-args">{jsonPretty(modalTool.args, 8000)}</pre>
					{/if}
				{/if}
				{#if modalTool.result}
					<div class="text-[11px] font-medium text-dl-text-muted">출력</div>
					{#if modalTool.result.values}
						<pre class="tool-args">{jsonPretty(modalTool.result.values, 4000)}</pre>
					{/if}
					{#if Array.isArray(modalTool.result.tableHead) && modalTool.result.tableHead.length}
						<pre class="tool-args">{jsonPretty(modalTool.result.tableHead, 8000)}</pre>
					{/if}
					{#if modalTool.result.stdout}
						<div class="text-[10px] text-dl-text-dim">stdout</div>
						<pre class="tool-args">{modalTool.result.stdout}</pre>
					{/if}
					{#if modalTool.result.stderr}
						<div class="text-[10px] text-dl-primary-light">stderr</div>
						<pre class="tool-args">{modalTool.result.stderr}</pre>
					{/if}
					{#if modalTool.result.body}
						<pre class="tool-args">{modalTool.result.body}</pre>
					{/if}
				{/if}
				{#if modalTool.error}
					<div class="text-[11px] font-medium text-dl-primary-light">에러</div>
					<pre class="tool-args">{modalTool.error}</pre>
				{/if}
			</div>
		</div>
	</div>
{/if}
