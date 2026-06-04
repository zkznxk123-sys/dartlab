<script lang="ts">
	// 공시뷰어 — panel 하나로 브라우저 readWide → TOC + 항목×기간 격자 + 원본 링크. ui/web ViewerTab 이식.
	import { onMount } from 'svelte';
	import { loadPanelBundle } from '$lib/viewer/panelLoad';
	import PanelTocTree from '$lib/components/viewer/PanelTocTree.svelte';
	import PanelMatrix from '$lib/components/viewer/PanelMatrix.svelte';
	import type { PanelBundle } from '$lib/viewer/types';

	let { data }: { data: { code: string } } = $props();
	const code = $derived(data.code);

	let bundle = $state<PanelBundle | null>(null);
	let errorMsg = $state<string | null>(null);
	let loading = $state(true);
	let activeSectionKey = $state<string | undefined>(undefined);
	let windowEnd = $state(0); // periods 인덱스 (0 = 최신)
	const COLS = 3;

	onMount(async () => {
		try {
			const b = await loadPanelBundle(code);
			bundle = b;
			activeSectionKey = b.toc.chapters[0]?.sections[0]?.sectionKey;
			if (!b.periods.length) errorMsg = '이 종목의 panel 데이터가 없습니다 (HF 업로드 대기 중일 수 있음).';
		} catch (e) {
			errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`;
		} finally {
			loading = false;
		}
	});

	const periods = $derived(bundle?.periods ?? []);
	const windowPeriods = $derived(periods.slice(windowEnd, windowEnd + COLS));
	const rows = $derived(activeSectionKey && bundle ? (bundle.gridBySection.get(activeSectionKey) ?? []) : []);
	const dartUrls = $derived(bundle?.dartUrlByPeriod ?? {});
	const sectionLabel = $derived(activeSectionKey?.split('␟').pop() ?? '');

	function pick(sectionKey: string) {
		activeSectionKey = sectionKey;
		windowEnd = 0;
	}
	const canNewer = $derived(windowEnd > 0);
	const canOlder = $derived(windowEnd + COLS < periods.length);
</script>

<svelte:head><title>{bundle?.corpName ?? code} 공시뷰어</title></svelte:head>

<div class="flex h-[calc(100vh-4rem)] min-h-0 overflow-hidden">
	{#if loading}
		<div class="flex w-full flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
			<div class="h-7 w-7 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-foreground"></div>
			<div>{code} 공시 본문 로드 중…</div>
		</div>
	{:else if errorMsg}
		<div class="flex w-full items-center justify-center p-6 text-center text-sm text-muted-foreground">{errorMsg}</div>
	{:else if bundle}
		<aside class="w-60 shrink-0 overflow-y-auto border-r bg-card/30 p-2">
			<PanelTocTree toc={bundle.toc} {activeSectionKey} onpick={pick} />
		</aside>
		<main class="flex min-h-0 min-w-0 flex-1 flex-col overflow-x-hidden">
			<div class="shrink-0 border-b bg-background px-3 py-2">
				<div class="flex items-baseline justify-between gap-3">
					<div>
						<div class="text-xs text-muted-foreground">{bundle.corpName ? `${bundle.corpName} · ${code}` : code}</div>
						<h1 class="mt-1 text-lg font-semibold tracking-tight">{sectionLabel}</h1>
					</div>
					<div class="flex items-center gap-2 text-[11px] text-muted-foreground">
						<span>항목 {rows.length} · 전체 기간 {periods.length}</span>
						<button type="button" disabled={!canNewer} onclick={() => (windowEnd = Math.max(0, windowEnd - COLS))} class="rounded border px-1.5 py-0.5 {canNewer ? 'hover:bg-accent' : 'opacity-30'}">← 최신</button>
						<button type="button" disabled={!canOlder} onclick={() => (windowEnd = windowEnd + COLS)} class="rounded border px-1.5 py-0.5 {canOlder ? 'hover:bg-accent' : 'opacity-30'}">과거 →</button>
					</div>
				</div>
			</div>
			<div class="min-h-0 flex-1">
				<PanelMatrix {rows} periods={windowPeriods} dartUrlByPeriod={dartUrls} />
			</div>
		</main>
	{/if}
</div>
