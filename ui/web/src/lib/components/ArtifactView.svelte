<!--
	ArtifactView — Claude.ai 식 우측 패널 산출물 뷰어.

	본문 답변과 분리된 산출물 (CSV/JSON/JSONL · table · chart · snapshot) 을
	Preview / Code 토글 + 다운로드 + 메타데이터 (파일명·크기·생성일) 와 함께 노출.

	Props:
	  artifact: { url, fileName, mediaType?, sizeBytes?, createdAt? }
	  onClose: () => void
-->
<script>
	import { Check, Code2, Copy, Download, Eye, Link, X, FileText } from "lucide-svelte";
	import { onMount } from "svelte";

	let { artifact = null, onClose } = $props();

	let mode = $state("preview"); // "preview" | "code"
	let raw = $state("");
	let loading = $state(false);
	let error = $state("");
	let copied = $state(false);
	let linkCopied = $state(false);

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
</script>

<div class="flex h-full flex-col">
	<header class="flex items-center gap-2 border-b border-dl-border/40 px-3 py-2">
		<FileText size={14} class="text-dl-text-dim" />
		<div class="flex-1 truncate text-[12px] font-semibold text-dl-text-muted">
			{fileName}
		</div>
		{#if sizeLabel}
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
			class="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition"
			class:bg-dl-bg-card-hover={mode === "preview"}
			class:text-dl-text={mode === "preview"}
			class:text-dl-text-dim={mode !== "preview"}
			onclick={() => (mode = "preview")}
			type="button"
		>
			<Eye size={12} /> Preview
		</button>
		<button
			class="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition"
			class:bg-dl-bg-card-hover={mode === "code"}
			class:text-dl-text={mode === "code"}
			class:text-dl-text-dim={mode !== "code"}
			onclick={() => (mode = "code")}
			type="button"
		>
			<Code2 size={12} /> Code
		</button>
		<div class="flex-1"></div>
		<button
			class="flex items-center gap-1 rounded-md border border-dl-border/40 px-2 py-1 text-[11px] text-dl-text-dim hover:text-dl-text disabled:opacity-50"
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
			<button
				class="flex items-center gap-1 rounded-md border border-dl-border/40 px-2 py-1 text-[11px] text-dl-text-dim hover:text-dl-text"
				onclick={copyLink}
				type="button"
				title="공유 링크 복사"
			>
				{#if linkCopied}
					<Check size={12} class="text-emerald-400" /> 링크 복사됨
				{:else}
					<Link size={12} /> 공유
				{/if}
			</button>
			<a
				class="flex items-center gap-1 rounded-md border border-dl-border/40 px-2 py-1 text-[11px] text-dl-text-dim hover:text-dl-text"
				href={url}
				download={fileName}
			>
				<Download size={12} /> 다운로드
			</a>
		{/if}
	</div>

	<div class="flex-1 overflow-auto px-3 py-3 text-[12px]">
		{#if loading}
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
	</div>
</div>
