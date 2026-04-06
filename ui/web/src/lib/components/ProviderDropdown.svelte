<script>
	import { cn } from "$lib/utils.js";
	import { ChevronDown, Cog, Loader2, AlertCircle, Check } from "lucide-svelte";
	import { getUiStore } from "$lib/stores/ui.svelte.js";

	let { onOpenSettings } = $props();
	const ui = getUiStore();
	let open = $state(false);

	// store 값 derived — props 통과 시 reactivity 끊김 우회
	let isLoading = $derived(ui.statusLoading);
	let activeProv = $derived(ui.activeProvider);
	let activeMod = $derived(ui.activeModel);
	let provs = $derived(ui.providers || {});

	let providerList = $derived.by(() => {
		const entries = Object.entries(provs);
		return entries
			.filter(([, v]) => v.label)
			.map(([id, v]) => ({
				id,
				label: v.label || id,
				available: v.available === true,
				freeTier: v.freeTier || "",
			}))
			.sort((a, b) => (b.available ? 1 : 0) - (a.available ? 1 : 0));
	});

	function select(id) {
		ui.selectProvider(id);
		open = false;
	}

	// Svelte 5 이벤트 위임 우회 — document에 직접 click 리스너
	if (typeof document !== "undefined") {
		document.addEventListener("click", (e) => {
			if (!e.target.closest(".provider-dropdown")) open = false;
		});
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
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
		onclick={() => { open = !open; }}
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
		<ChevronDown size={10} class="transition-transform {open ? 'rotate-180' : ''}" />
	</button>

	{#if open}
		<div class="absolute right-0 top-full mt-1 w-56 rounded-lg border border-dl-border/50 bg-dl-bg-darker shadow-overlay z-50 py-1 overflow-hidden">
			{#each providerList as p}
				<button
					class={cn(
						"w-full flex items-center gap-2 px-3 py-2 text-left text-[12px] transition-colors hover:bg-white/5",
						p.id === ui.activeProvider ? "text-dl-text" : "text-dl-text-muted"
					)}
					onclick={() => { select(p.id); }}
				>
					{#if p.available}
						<span class="w-1.5 h-1.5 rounded-full bg-dl-success flex-shrink-0"></span>
					{:else}
						<span class="w-1.5 h-1.5 rounded-full bg-dl-text-dim/30 flex-shrink-0"></span>
					{/if}
					<span class="flex-1">{p.label}</span>
					{#if p.id === ui.activeProvider}
						<Check size={12} class="text-dl-success flex-shrink-0" />
					{/if}
				</button>
			{/each}
			<div class="border-t border-dl-border/30 mt-1 pt-1">
				<button
					class="w-full flex items-center gap-2 px-3 py-2 text-left text-[12px] text-dl-text-dim hover:text-dl-text hover:bg-white/5 transition-colors"
					onclick={() => { open = false; onOpenSettings?.(); }}
				>
					<Cog size={12} />
					<span>프로바이더 설정</span>
				</button>
			</div>
		</div>
	{/if}
</div>
