<script>
	import { cn } from "$lib/utils.js";
	import { onMount } from "svelte";
	import { ChevronDown, Settings, Loader2, AlertCircle, Check } from "lucide-svelte";
	import { getUiStore } from "$lib/stores/ui.svelte.js";

	let { onOpenSettings } = $props();
	const ui = getUiStore();
	let open = $state(false);

	// 단일 $state 객체 — 개별 let보다 proxy 추적이 확실함
	let snap = $state({
		isLoading: true,
		activeProv: null,
		activeMod: null,
		provs: {},
		dbgStep: "init",
		diag: "init",
		tick: 0,
	});

	function syncFromStore() {
		try {
			const isL = ui.statusLoading;
			const pv = ui.providers || {};
			// 전체 객체를 새로 할당 — 부분 할당보다 reactivity 트리거 확실
			snap = {
				isLoading: isL,
				activeProv: ui.activeProvider,
				activeMod: ui.activeModel,
				provs: pv,
				dbgStep: ui.debugStep || "?",
				diag: (ui.debugStep || "?") + " L" + (isL ? 1 : 0) + "P" + Object.keys(pv).length,
				tick: snap.tick + 1,
			};
		} catch (e) {
			snap = { ...snap, diag: "syncErr:" + String(e).slice(0, 30) };
		}
	}

	// 폴링 — lifecycle hook 없이 즉시
	if (typeof window !== "undefined") {
		try { syncFromStore(); } catch (_) {}
		setInterval(syncFromStore, 250);
	}
	onMount(() => syncFromStore());

	// 각 값 derived — 템플릿이 읽을 때마다 snap에서 재평가
	let isLoading = $derived(snap.isLoading);
	let activeProv = $derived(snap.activeProv);
	let activeMod = $derived(snap.activeMod);
	let provs = $derived(snap.provs);
	let _diag = $derived(snap.diag);

	let providerList = $derived.by(() => {
		const entries = Object.entries(provs || {});
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

	// Svelte 5 이벤트 위임 + stopPropagation 충돌 우회 — document에 직접 붙임
	function handleDocClick(e) {
		if (!e.target.closest(".provider-dropdown")) open = false;
	}
	if (typeof document !== "undefined") {
		document.addEventListener("click", handleDocClick);
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
			<span id="_dl_diag_span">확인 중 [{_diag}]</span>
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
					<Settings size={12} />
					<span>프로바이더 설정</span>
				</button>
			</div>
		</div>
	{/if}
</div>
