<!--
	ArtifactView — 우측 워크벤치 패널 (4 탭 SSOT).

	탭 4 종:
	  - Preview: artifact 미리보기 (CSV/JSON/markdown/원본 텍스트)
	  - Code:    artifact raw + 복사
	  - Timeline: activeMessage 의 tool 호출들을 시간순 행으로 (분석 흐름 복기)
	  - Report:  activeMessage 를 인쇄·저장 가능 보고서 — 질문 + 답변 + 도구 입출력 + ref + 사용 코드 fenced (재활용 위해 카피)

	props:
	  artifact: { url, fileName, sizeBytes? }   — Preview/Code 대상
	  activeMessage: { role, text, parts, ... } — Timeline/Report 대상
	  onClose: () => void
-->
<script>
	import { Check, Code2, Copy, Download, Eye, FileText, Link, ListOrdered, X } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { groupLoops } from "$lib/agent/conversationModel.js";

	let { artifact = null, activeMessage = null, onClose } = $props();

	let mode = $state("preview"); // "preview" | "code" | "timeline" | "report"
	let raw = $state("");
	let loading = $state(false);
	let error = $state("");
	let copied = $state(false);
	let linkCopied = $state(false);
	let codeCopied = $state({});
	let modalRow = $state(null);

	async function copyContent() {
		if (!raw) return;
		try {
			await navigator.clipboard.writeText(raw);
			copied = true;
			setTimeout(() => (copied = false), 1500);
		} catch (_) {}
	}

	async function copyLink() {
		if (!url) return;
		try {
			const absolute = new URL(url, window.location.href).href;
			await navigator.clipboard.writeText(absolute);
			linkCopied = true;
			setTimeout(() => (linkCopied = false), 1500);
		} catch (_) {}
	}

	async function copyCodeBlock(key, code) {
		if (!code) return;
		try {
			await navigator.clipboard.writeText(code);
			codeCopied = { ...codeCopied, [key]: true };
			setTimeout(() => { codeCopied = { ...codeCopied, [key]: false }; }, 1500);
		} catch (_) {}
	}

	let fileName = $derived(artifact?.fileName || artifact?.name || "artifact");
	let url = $derived(artifact?.url || "");
	let sizeLabel = $derived(
		artifact?.sizeBytes
			? `${Math.round((artifact.sizeBytes / 1024) * 10) / 10} KB`
			: ""
	);
	let isJson = $derived(/\.jsonl?$/.test(fileName));
	let isCsv = $derived(/\.csv$/.test(fileName));

	$effect(() => {
		if (!url) {
			raw = "";
			return;
		}
		loading = true;
		error = "";
		fetch(url)
			.then((res) => (res.ok ? res.text() : Promise.reject(new Error(`HTTP ${res.status}`))))
			.then((text) => { raw = text; loading = false; })
			.catch((err) => { error = err.message || "로드 실패"; loading = false; });
	});

	let preview = $derived.by(() => {
		if (!raw) return [];
		if (isCsv) {
			const lines = raw.split(/\r?\n/).filter(Boolean).slice(0, 50);
			return lines.map((line) => line.split(","));
		}
		if (isJson) {
			const lines = raw.split(/\r?\n/).filter(Boolean).slice(0, 50);
			try { return lines.map((line) => JSON.parse(line)); }
			catch { return []; }
		}
		return [];
	});

	// Timeline / Report 데이터
	let messageParts = $derived(Array.isArray(activeMessage?.parts) ? activeMessage.parts : []);
	let toolCalls = $derived(messageParts.filter((p) => p?.type === "tool"));
	let activities = $derived(messageParts.filter((p) => p?.type === "activity"));
	let textParts = $derived(messageParts.filter((p) => p?.type === "text"));
	let loopCards = $derived(groupLoops(messageParts));
	// Report 의 사용 코드 묶음 — RunPython 류 도구의 args.code 를 모은다.
	let codeBlocks = $derived.by(() => {
		const out = [];
		for (const part of toolCalls) {
			const code = part?.args?.code;
			if (typeof code === "string" && code.trim()) {
				out.push({
					id: part.id || part.toolCallId || `code-${out.length}`,
					name: part.name || "tool",
					code,
					summary: part.summary || "",
				});
			}
		}
		return out;
	});

	function openRowModal(row) { modalRow = row; }
	function closeRowModal() { modalRow = null; }

	function jsonPretty(obj, max = 800) {
		try {
			const s = JSON.stringify(obj, null, 2);
			return s.length > max ? s.slice(0, max) + "\n…" : s;
		} catch { return String(obj); }
	}
	function fenceCode(code, lang = "python") {
		return "```" + lang + "\n" + (code || "") + "\n```";
	}
	function formatTime(ts) {
		if (!ts) return "";
		try {
			const d = new Date(ts);
			return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
		} catch { return ""; }
	}
	function shortText(s, max = 600) {
		if (typeof s !== "string") return "";
		return s.length > max ? s.slice(0, max) + "\n…" : s;
	}

	let hasArtifact = $derived(!!artifact?.url);
	let hasMessage = $derived(!!activeMessage);
	let headerLabel = $derived.by(() => {
		if (mode === "timeline" || mode === "report") {
			return activeMessage?.text?.slice(0, 40) || "메시지 워크벤치";
		}
		return fileName;
	});
</script>

<div class="flex h-full flex-col">
	<header class="flex items-center gap-2 border-b border-dl-border/40 px-3 py-2">
		<FileText size={14} class="text-dl-text-dim" />
		<div class="flex-1 truncate text-[12px] font-semibold text-dl-text-muted">
			{headerLabel}
		</div>
		{#if sizeLabel && (mode === "preview" || mode === "code")}
			<span class="rounded-full border border-dl-border/40 px-2 py-0.5 text-[10px] text-dl-text-dim">
				{sizeLabel}
			</span>
		{/if}
		{#if onClose}
			<button class="dl-icon-btn" aria-label="닫기" onclick={onClose}>
				<X size={14} />
			</button>
		{/if}
	</header>

	<div class="flex items-center gap-1 border-b border-dl-border/40 px-2 py-1.5">
		<button
			class="wb-tab"
			class:wb-tab-active={mode === "preview"}
			disabled={!hasArtifact}
			onclick={() => (mode = "preview")}
			type="button"
		>
			<Eye size={12} /> Preview
		</button>
		<button
			class="wb-tab"
			class:wb-tab-active={mode === "code"}
			disabled={!hasArtifact}
			onclick={() => (mode = "code")}
			type="button"
		>
			<Code2 size={12} /> Code
		</button>
		<button
			class="wb-tab"
			class:wb-tab-active={mode === "timeline"}
			disabled={!hasMessage}
			onclick={() => (mode = "timeline")}
			type="button"
		>
			<ListOrdered size={12} /> Timeline
		</button>
		<button
			class="wb-tab"
			class:wb-tab-active={mode === "report"}
			disabled={!hasMessage}
			onclick={() => (mode = "report")}
			type="button"
		>
			<FileText size={12} /> Report
		</button>
		<div class="flex-1"></div>
		{#if mode === "preview" || mode === "code"}
			<button
				class="wb-action"
				onclick={copyContent}
				disabled={!raw}
				type="button"
				title="내용 복사"
			>
				{#if copied}
					<Check size={12} class="text-emerald-400" /> 복사됨
				{:else}
					<Copy size={12} /> 복사
				{/if}
			</button>
			{#if url}
				<button class="wb-action" onclick={copyLink} type="button" title="공유 링크 복사">
					{#if linkCopied}
						<Check size={12} class="text-emerald-400" /> 링크
					{:else}
						<Link size={12} /> 공유
					{/if}
				</button>
				<a class="wb-action" href={url} download={fileName}>
					<Download size={12} /> 다운로드
				</a>
			{/if}
		{:else if mode === "report"}
			<button class="wb-action" onclick={() => window.print()} type="button" title="인쇄 / PDF 저장">
				<Download size={12} /> 인쇄
			</button>
		{/if}
	</div>

	<div class="flex-1 overflow-auto px-3 py-3 text-[12px]">
		{#if mode === "preview" || mode === "code"}
			{#if !hasArtifact}
				<div class="text-dl-text-dim">artifact 미선택</div>
			{:else if loading}
				<div class="text-dl-text-dim">로드 중…</div>
			{:else if error}
				<div class="text-red-400">로드 실패: {error}</div>
			{:else if mode === "code"}
				<pre class="whitespace-pre-wrap break-words font-mono text-[11px] text-dl-text">{raw}</pre>
			{:else if isCsv && preview.length}
				<table class="w-full border-collapse text-[11px]">
					<thead class="text-dl-text-dim">
						<tr>
							{#each preview[0] as cell}
								<th class="border border-dl-border/40 px-2 py-1 text-left font-medium">{cell}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each preview.slice(1) as row}
							<tr>
								{#each row as cell}
									<td class="border border-dl-border/40 px-2 py-1 text-dl-text">{cell}</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			{:else if isJson && preview.length}
				<ul class="space-y-1 font-mono text-[11px]">
					{#each preview as item}
						<li class="rounded border border-dl-border/40 bg-dl-bg-card/40 px-2 py-1 text-dl-text">
							{JSON.stringify(item)}
						</li>
					{/each}
				</ul>
			{:else}
				<pre class="whitespace-pre-wrap break-words font-mono text-[11px] text-dl-text">{raw || ""}</pre>
			{/if}

		{:else if mode === "timeline"}
			{#if !hasMessage || !toolCalls.length}
				<div class="text-dl-text-dim">이 메시지에는 도구 호출이 없습니다.</div>
			{:else}
				<ol class="wb-timeline">
					{#each toolCalls as call, i (call.id || i)}
						<li class="wb-timeline-row" class:wb-timeline-row-error={call.status === "error"}>
							<button type="button" class="wb-timeline-head" onclick={() => openRowModal(call)} title="상세 보기">
								<span class="wb-timeline-num">{i + 1}</span>
								<span class="wb-timeline-time">{formatTime(call.timestamp)}</span>
								{#if call.passLabel}
									<span class="wb-timeline-pass">{call.passLabel}</span>
								{/if}
								<span class="wb-timeline-name">{call.name}</span>
								{#if call.summary}
									<span class="wb-timeline-summary">· {call.summary}</span>
								{/if}
								{#if call.result?.durationMs}
									<span class="wb-timeline-dur">{call.result.durationMs}ms</span>
								{/if}
							</button>
						</li>
					{/each}
				</ol>
			{/if}

		{:else if mode === "report"}
			{#if !hasMessage}
				<div class="text-dl-text-dim">메시지 미선택</div>
			{:else}
				<article class="wb-report prose-dartlab">
					<header class="wb-report-header">
						<h1>분석 보고서</h1>
						{#if activeMessage.createdAt}
							<div class="wb-report-meta">{formatTime(activeMessage.createdAt)}</div>
						{/if}
					</header>

					{#if textParts.length}
						<section>
							<h2>답변</h2>
							{#each textParts as t}
								<div>{@html renderMarkdown(t.content || "")}</div>
							{/each}
						</section>
					{:else if activeMessage.text}
						<section>
							<h2>답변</h2>
							<div>{@html renderMarkdown(activeMessage.text)}</div>
						</section>
					{/if}

					{#if loopCards.some((p) => p.type === "loop-card")}
						<section>
							<h2>분석 흐름</h2>
							<ul class="wb-report-loops">
								{#each loopCards.filter((p) => p.type === "loop-card") as loop, li (loop.id || li)}
									<li>
										<strong>{loop.label}</strong>
										<span class="wb-report-loops-meta">{loop.toolCount}건{loop.errorCount > 0 ? ` · ${loop.errorCount} 실패` : ""}</span>
										{#if loop.summary}
											<span class="wb-report-loops-summary">— {loop.summary}</span>
										{/if}
									</li>
								{/each}
							</ul>
						</section>
					{/if}

					{#if codeBlocks.length}
						<section>
							<h2>사용된 코드 ({codeBlocks.length}건)</h2>
							{#each codeBlocks as block (block.id)}
								<div class="wb-code-block">
									<div class="wb-code-block-head">
										<span class="wb-code-block-name">{block.name}</span>
										{#if block.summary}
											<span class="wb-code-block-summary">· {block.summary}</span>
										{/if}
										<button
											type="button"
											class="wb-code-block-copy"
											onclick={() => copyCodeBlock(block.id, block.code)}
											title="코드 복사"
										>
											{#if codeCopied[block.id]}
												<Check size={11} class="text-emerald-400" /> 복사됨
											{:else}
												<Copy size={11} /> 복사
											{/if}
										</button>
									</div>
									<div class="wb-code-block-body">
										{@html renderMarkdown(fenceCode(block.code, "python"))}
									</div>
								</div>
							{/each}
						</section>
					{/if}

					{#if toolCalls.length}
						<section>
							<h2>도구 호출 ({toolCalls.length}건)</h2>
							<ul class="wb-report-tools">
								{#each toolCalls as call (call.id || call.toolCallId)}
									<li class:wb-report-tools-error={call.status === "error"}>
										<strong>{call.name}</strong>
										{#if call.summary}
											<span> — {call.summary}</span>
										{/if}
										{#if call.result?.markdown}
											<div class="wb-report-tools-body">{@html renderMarkdown(call.result.markdown)}</div>
										{:else if call.result?.stdout}
											<pre class="wb-report-tools-body">{shortText(call.result.stdout, 1200)}</pre>
										{/if}
									</li>
								{/each}
							</ul>
						</section>
					{/if}
				</article>
			{/if}
		{/if}
	</div>
</div>

{#if modalRow}
	<div
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn"
		onclick={(e) => { if (e.target === e.currentTarget) closeRowModal(); }}
		role="presentation"
	>
		<div class="surface-overlay w-full max-w-3xl max-h-[85vh] bg-dl-bg-card border border-dl-border rounded-2xl shadow-2xl overflow-hidden flex flex-col">
			<div class="flex items-center justify-between border-b border-dl-border/40 px-5 py-3">
				<div class="flex items-center gap-2">
					<span class="text-[12px] font-semibold text-dl-text">{modalRow.name}</span>
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
					<pre class="loop-row-pre">{jsonPretty(modalRow.args, 8000)}</pre>
				{/if}
				{#if modalRow.result}
					<div class="text-[11px] font-medium text-dl-text-muted">출력</div>
					{#if modalRow.result.markdown}
						<div class="prose-dartlab">{@html renderMarkdown(modalRow.result.markdown)}</div>
					{:else}
						<pre class="loop-row-pre">{jsonPretty(modalRow.result, 8000)}</pre>
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

<style>
	.wb-tab {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		border-radius: 6px;
		font-size: 11px;
		font-weight: 500;
		color: var(--color-dl-text-dim);
		background: transparent;
		border: 0;
		cursor: pointer;
		transition: background var(--motion-fast);
	}
	.wb-tab:hover:not(:disabled) {
		background: var(--color-dl-bg-card-hover);
		color: var(--color-dl-text-muted);
	}
	.wb-tab:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.wb-tab-active {
		background: var(--color-dl-bg-card-hover);
		color: var(--color-dl-text);
	}
	.wb-action {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 6px;
		font-size: 11px;
		color: var(--color-dl-text-dim);
		background: transparent;
		cursor: pointer;
		text-decoration: none;
	}
	.wb-action:hover:not(:disabled) {
		color: var(--color-dl-text);
		background: rgba(148, 163, 184, 0.08);
	}
	.wb-action:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.wb-timeline {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.wb-timeline-row {
		border-radius: 6px;
		background: rgba(13, 17, 23, 0.40);
		border: 1px solid rgba(148, 163, 184, 0.12);
	}
	.wb-timeline-row-error {
		border-color: rgba(248, 113, 113, 0.32);
		background: rgba(248, 113, 113, 0.05);
	}
	.wb-timeline-head {
		display: grid;
		grid-template-columns: 22px max-content max-content max-content minmax(0, 1fr) max-content;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 6px 10px;
		border: 0;
		background: transparent;
		text-align: left;
		cursor: pointer;
		font-size: 11px;
		color: var(--color-dl-text-muted);
	}
	.wb-timeline-head:hover {
		background: rgba(148, 163, 184, 0.05);
	}
	.wb-timeline-num {
		color: var(--color-dl-text-dim);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
	.wb-timeline-time {
		color: var(--color-dl-text-dim);
		font-family: var(--font-mono);
		font-size: 10px;
	}
	.wb-timeline-pass {
		color: var(--color-dl-text);
		background: rgba(148, 163, 184, 0.12);
		padding: 1px 5px;
		border-radius: 4px;
		font-size: 10px;
		font-weight: 600;
		letter-spacing: 0.02em;
	}
	.wb-timeline-name {
		color: var(--color-dl-text);
		font-weight: 600;
		white-space: nowrap;
	}
	.wb-timeline-summary {
		color: var(--color-dl-text-dim);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.wb-timeline-dur {
		color: var(--color-dl-text-dim);
		font-family: var(--font-mono);
		font-size: 10px;
	}

	.wb-report-header {
		margin-bottom: 1em;
	}
	.wb-report-meta {
		font-size: 11px;
		color: var(--color-dl-text-dim);
	}
	.wb-report-loops {
		list-style: none;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.wb-report-loops-meta {
		color: var(--color-dl-text-dim);
		font-size: 11px;
		margin-left: 8px;
	}
	.wb-report-loops-summary {
		color: var(--color-dl-text-muted);
		font-size: 12px;
		margin-left: 6px;
	}
	.wb-report-tools {
		list-style: none;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.wb-report-tools-error strong {
		color: var(--color-dl-primary-light);
	}
	.wb-report-tools-body {
		margin-top: 4px;
		padding: 6px 8px;
		background: rgba(13, 17, 23, 0.30);
		border-radius: 4px;
		font-size: 11px;
		max-height: 240px;
		overflow-y: auto;
	}

	.wb-code-block {
		margin: 6px 0;
		border: 1px solid rgba(148, 163, 184, 0.16);
		border-radius: 6px;
		background: rgba(13, 17, 23, 0.32);
		overflow: hidden;
	}
	.wb-code-block-head {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 5px 10px;
		border-bottom: 1px solid rgba(148, 163, 184, 0.10);
		font-size: 11px;
	}
	.wb-code-block-name {
		color: var(--color-dl-text);
		font-weight: 600;
	}
	.wb-code-block-summary {
		color: var(--color-dl-text-dim);
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.wb-code-block-copy {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 6px;
		border-radius: 4px;
		background: rgba(148, 163, 184, 0.08);
		color: var(--color-dl-text-dim);
		border: 0;
		cursor: pointer;
		font-size: 10px;
		margin-left: auto;
	}
	.wb-code-block-copy:hover {
		background: rgba(148, 163, 184, 0.16);
		color: var(--color-dl-text);
	}
	.wb-code-block-body {
		padding: 0 8px 6px 8px;
	}

	@media print {
		.wb-tab, .wb-action, header {
			display: none !important;
		}
	}
</style>
