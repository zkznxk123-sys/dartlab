<!--
	Industry > Peers — Company.industry 응답 specialized.
	응답: { industry, industryName, stage, stageName, role, stream, confidence, source, peers: [{stockCode, corpName, confidence}] }
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	let { payload = null, loading = false } = $props();
	const peers = $derived(payload?.peers || []);
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">Industry Classification</div>
		<div class="grid grid-cols-4 gap-3">
			<div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">산업</div>
				<div class="text-[16px] font-medium" style="color: var(--ed-text); font-family: var(--font-display);">{payload.industryName || payload.industry || "—"}</div>
			</div>
			<div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">단계</div>
				<div class="text-[16px] font-medium" style="color: var(--ed-text); font-family: var(--font-display);">{payload.stageName || payload.stage || "—"}</div>
			</div>
			<div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">역할</div>
				<div class="text-[14px]" style="color: var(--ed-text-2);">{payload.role || "—"} · {payload.stream || "—"}</div>
			</div>
			<div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">신뢰도</div>
				<div class="ed-num text-[16px]" style="color: var(--ed-text);">{isFiniteNum(payload.confidence) ? (payload.confidence * 100).toFixed(1) + "%" : "—"}</div>
				<div class="text-[9.5px]" style="color: var(--ed-text-3);">source: {payload.source || "—"}</div>
			</div>
		</div>
	</div>

	{#if peers.length > 0}
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Peers ({peers.length})</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">confidence 정렬</div>
			</div>
			<ul class="grid grid-cols-1 md:grid-cols-2 gap-1.5">
				{#each peers as p}
					<li class="grid grid-cols-[80px_1fr_60px] items-center gap-2 px-2.5 py-1.5 rounded border text-[12px]"
						style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<span class="ed-num" style="color: var(--ed-text-3);">{p.stockCode}</span>
						<span style="color: var(--ed-text); font-weight: 500;">{p.corpName}</span>
						<span class="ed-num text-right" style="color: {p.confidence >= 0.85 ? 'var(--ed-up)' : 'var(--ed-text-2)'};">
							{isFiniteNum(p.confidence) ? (p.confidence * 100).toFixed(0) + "%" : "—"}
						</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
{/if}
