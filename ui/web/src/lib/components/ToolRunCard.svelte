<script>
	import { CheckCircle2, Loader2, Terminal, XCircle } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { describeCallArgs } from "$lib/ai/toolSummary.js";

	let { part } = $props();
	let expanded = $state(false);

	let displayName = $derived(part.displayName || String(part.name || "tool").replaceAll("_", " "));
	let argsText = $derived(describeCallArgs({ arguments: part.args }) || part.summary || "");
	let parsed = $derived.by(() => {
		if (typeof part.result !== "string") return null;
		try { return JSON.parse(part.result); } catch { return null; }
	});
	let execution = $derived(parsed?.result?.execution || parsed?.execution || null);
	let stdout = $derived(execution?.stdout || "");
	let stderr = $derived(execution?.stderr || "");
	let outputPreview = $derived(stdout || stderr || part.summary || "");
	let artifactUrl = $derived(part.fullResultArtifact?.url || part.artifacts?.[0]?.url || "");
	let artifactSize = $derived(part.sizeBytes ? `${Math.round(part.sizeBytes / 1024)} KB` : "");
</script>

<div class="tool-run-card" class:tool-run-error={part.status === "error"}>
	<button class="tool-run-header" type="button" onclick={() => { expanded = !expanded; }}>
		{#if part.status === "running"}
			<Loader2 size={13} class="animate-spin" />
		{:else if part.status === "error"}
			<XCircle size={13} />
		{:else}
			<CheckCircle2 size={13} />
		{/if}
		<span class="tool-run-name">{displayName} 실행함</span>
		<span class="tool-run-summary">{part.summary}</span>
		<Terminal size={12} class="tool-run-terminal" />
	</button>

	{#if expanded || part.status === "running" || part.status === "error"}
		<div class="tool-run-body">
			{#if argsText}
				<div class="tool-run-section">
					<div class="tool-run-label">입력</div>
					<div class="tool-run-text">{argsText}</div>
				</div>
			{/if}
			{#if part.progressLines?.length}
				<div class="tool-run-section">
					<div class="tool-run-label">진행</div>
					<div class="tool-run-log">
						{#each part.progressLines.slice(-5) as line}
							<div>{line}</div>
						{/each}
					</div>
				</div>
			{/if}
			{#if outputPreview}
				<div class="tool-run-section">
					<div class="tool-run-label">{part.status === "error" ? "오류" : "출력"}</div>
					<div class="tool-run-output prose-dartlab">{@html renderMarkdown(String(outputPreview).slice(0, 3000))}</div>
				</div>
			{/if}
			{#if artifactUrl}
				<div class="tool-run-artifact">전체 결과 artifact: {artifactUrl}{artifactSize ? ` (${artifactSize})` : ""}</div>
			{/if}
		</div>
	{/if}
</div>
