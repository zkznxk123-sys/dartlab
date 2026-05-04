<script>
	import { AlertTriangle } from "lucide-svelte";

	let { part, onRegenerate = null } = $props();
	let summary = $derived(String(part.summary || part.activity?.summary || "최종 답변 생성 실패"));
	let reason = $derived(String(part.activity?.error || part.error || ""));
</script>

<div class="failure-notice">
	<AlertTriangle size={14} />
	<div class="failure-copy">
		<div class="failure-title">{summary}</div>
		{#if reason && reason !== summary}
			<div class="failure-reason">{reason}</div>
		{/if}
	</div>
	{#if onRegenerate}
		<button class="failure-retry" type="button" onclick={() => onRegenerate?.()}>다시 시도</button>
	{/if}
</div>
