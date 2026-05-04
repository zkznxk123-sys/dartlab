<script>
	import { cn } from "$lib/utils.js";
	import { Loader2, AlertCircle, Settings2 } from "lucide-svelte";
	import { getUiStore } from "$lib/stores/ui.svelte.js";

	let { onOpenSettings } = $props();
	const ui = getUiStore();

	// store 값 derived — props 통과 시 reactivity 끊김 우회
	let isLoading = $derived(ui.statusLoading);
	let activeProv = $derived(ui.activeProvider);
	let activeMod = $derived(ui.activeModel);
	let provs = $derived(ui.providers || {});
</script>

<div class="provider-dropdown relative">
	<button
		class={cn(
			"flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] transition-colors",
			isLoading
				? "text-dl-text-dim"
				: !activeProv || !provs[activeProv]?.available
					? "text-dl-primary-light bg-dl-primary/10 hover:bg-dl-primary/15"
					: "text-dl-text-muted hover:text-dl-text hover:bg-white/5"
		)}
		onclick={() => onOpenSettings?.("providers")}
		aria-label="프로바이더 설정 열기"
	>
		{#if isLoading}
			<Loader2 size={12} class="animate-spin" />
			<span>확인 중...</span>
		{:else if !activeProv || !provs[activeProv]?.available}
			<AlertCircle size={12} />
			<span>설정 필요</span>
		{:else}
			<span class="w-1.5 h-1.5 rounded-full bg-dl-success flex-shrink-0"></span>
			<span>{provs[activeProv]?.label || activeProv}</span>
			{#if activeMod}
				<span class="text-dl-text-dim">/</span>
				<span class="max-w-[80px] truncate">{activeMod}</span>
			{/if}
		{/if}
		<Settings2 size={11} class="opacity-70" />
	</button>
</div>
