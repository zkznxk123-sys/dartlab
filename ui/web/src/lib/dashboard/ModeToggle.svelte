<!--
	ModeToggle — Ask 모드 ⇄ Dashboard 모드 사이드바 상단 토글.
	Tabs primitive 가 아닌 두 버튼으로 직접. 선택 시 즉시 mode store 갱신.
-->
<script>
	import { LayoutDashboard, MessageSquare } from "lucide-svelte";
	import { getUiMode } from "$lib/stores/uiMode.svelte.js";
	import { cn } from "$lib/utils.js";

	const ui = getUiMode();
</script>

<div class="inline-flex w-full rounded-md border border-border bg-card p-0.5">
	<button
		type="button"
		class={cn(
			"flex-1 inline-flex items-center justify-center gap-1.5 rounded px-2 py-1 text-[12px] font-medium transition-colors",
			ui.value === "ask"
				? "bg-secondary text-foreground"
				: "text-muted-foreground hover:text-foreground"
		)}
		aria-pressed={ui.value === "ask"}
		onclick={() => ui.setMode("ask")}
	>
		<MessageSquare size={13} />
		<span>Ask</span>
	</button>
	<button
		type="button"
		class={cn(
			"flex-1 inline-flex items-center justify-center gap-1.5 rounded px-2 py-1 text-[12px] font-medium transition-colors",
			ui.value === "dashboard"
				? "bg-secondary text-foreground"
				: "text-muted-foreground hover:text-foreground"
		)}
		aria-pressed={ui.value === "dashboard"}
		onclick={() => ui.setMode("dashboard")}
	>
		<LayoutDashboard size={13} />
		<span>Dashboard</span>
	</button>
</div>
