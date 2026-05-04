<script>
	import { CheckCircle2, Circle, Loader2, Search, Terminal, XCircle } from "lucide-svelte";

	let { parts = [], loading = false, onOpenEvidence = null } = $props();

	let activityParts = $derived((parts || []).filter(part => part.type === "activity" || part.type === "failure"));
	let visibleParts = $derived(loading ? activityParts.slice(-6) : activityParts);
	let refs = $derived.by(() => {
		const out = [];
		for (const part of activityParts) {
			for (const ref of part.refs || part.activity?.refs || []) {
				if (ref && !out.includes(ref)) out.push(ref);
			}
		}
		return out;
	});
	let latest = $derived(activityParts[activityParts.length - 1] || null);
	let latestSummary = $derived(readableSummary(latest));
	let statusText = $derived(loading ? "작업 중" : `작업 ${activityParts.length}개 완료`);

	function iconFor(part) {
		const kind = part.activity?.kind || "";
		if (part.status === "error") return XCircle;
		if (part.status === "running") return Loader2;
		if (kind.includes("python") || kind.includes("execute") || kind.includes("visual")) return Terminal;
		if (kind.includes("search") || kind.includes("read") || kind.includes("inspect") || kind === "reference") return Search;
		return part.status === "done" ? CheckCircle2 : Circle;
	}

	function openEvidence(part) {
		if (!onOpenEvidence) return;
		const partRefs = part.refs || part.activity?.refs || [];
		if (partRefs.length > 0) onOpenEvidence("tool-results", 0);
	}

	function readableSummary(part) {
		return String(part?.summary || part?.activity?.summary || "");
	}
</script>

{#if activityParts.length}
	<section class="assistant-activity" aria-label="AI 작업 진행">
		<div class="assistant-activity-head">
			{#if loading}
				<Loader2 size={13} class="animate-spin assistant-activity-head-icon" />
			{:else if latest?.status === "error"}
				<XCircle size={13} class="assistant-activity-head-icon activity-error" />
			{:else}
				<CheckCircle2 size={13} class="assistant-activity-head-icon" />
			{/if}
			<span class="assistant-activity-status">{statusText}</span>
			{#if refs.length}
				<span class="assistant-activity-meta">근거 {refs.length}개</span>
			{/if}
			{#if latestSummary}
				<span class="assistant-activity-latest">{latestSummary}</span>
			{/if}
		</div>

		{#if loading}
			<div class="assistant-activity-list">
				{#each visibleParts as part, partIdx (`${part.id || part.type}-${partIdx}`)}
					{@const Icon = iconFor(part)}
					<button class="assistant-activity-row" class:activity-error={part.status === "error"} type="button" onclick={() => openEvidence(part)}>
						<Icon size={12} class={part.status === "running" ? "animate-spin" : ""} />
						<span>{readableSummary(part)}</span>
					</button>
				{/each}
			</div>
		{:else if activityParts.length > 1}
			<details class="assistant-activity-details">
				<summary>작업 내역 보기</summary>
				<div class="assistant-activity-list">
					{#each visibleParts as part, partIdx (`${part.id || part.type}-${partIdx}`)}
						{@const Icon = iconFor(part)}
						<button class="assistant-activity-row" class:activity-error={part.status === "error"} type="button" onclick={() => openEvidence(part)}>
							<Icon size={12} />
							<span>{readableSummary(part)}</span>
						</button>
					{/each}
				</div>
			</details>
		{/if}
	</section>
{/if}
