<!--
	SnapshotChip — Ask 모드 input 영역 위 dismissible chip.
	dashboardStore.pendingSnapshot 표시. AI 에 함께 첨부될 컨텍스트 미리보기.
-->
<script>
	import { Paperclip, X } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";

	const dash = getDashboardStore();

	function dismiss() {
		dash.clearPendingSnapshot();
	}

	function formatKpi(k) {
		if (typeof k === "object" && k != null && "name" in k && "value" in k) {
			return `${k.name}=${k.value}`;
		}
		return String(k);
	}
</script>

{#if dash.pendingSnapshot}
	{@const snap = dash.pendingSnapshot}
	<div class="mx-3 mb-2 flex items-start gap-2 rounded-md border border-primary/30 bg-primary/[0.04] px-3 py-2">
		<Paperclip size={13} class="text-primary shrink-0 mt-0.5" />
		<div class="flex-1 min-w-0">
			<div class="text-[11px] font-semibold text-foreground">현재 대시보드 화면 첨부됨</div>
			<div class="text-[10px] text-muted-foreground font-mono mt-0.5 truncate">
				{snap.dashboardView}
				{#if snap.axis} · {snap.axis}{/if}
				{#if snap.stockCode} · {snap.stockCode}{/if}
				{#if snap.period} · {snap.period}{/if}
			</div>
			{#if Array.isArray(snap.visibleKpis) && snap.visibleKpis.length > 0}
				<div class="text-[10px] text-muted-foreground truncate mt-0.5">
					KPI: {snap.visibleKpis.map(formatKpi).join(", ")}
				</div>
			{/if}
		</div>
		<button
			type="button"
			class="p-0.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors shrink-0"
			onclick={dismiss}
			aria-label="첨부 해제"
		>
			<X size={12} />
		</button>
	</div>
{/if}
