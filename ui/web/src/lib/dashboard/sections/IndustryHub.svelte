<!--
	Industry Hub — Company.industry / Company.rank / Company.network 통합.
	각 API 가 axis 없이 단일 호출. 상단 toggle 로 선택.
-->
<script>
	import { onMount } from "svelte";
	import { Factory, Info } from "lucide-svelte";
	import { dlCall } from "$lib/api/dlCall.js";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import * as Card from "$lib/ui/card";
	import { cn } from "$lib/utils.js";

	const dash = getDashboardStore();

	const VIEWS = [
		{ apiRef: "Company.industry", label: "산업/Peers", desc: "산업 분류 · 가치사슬 위치 · 동종업계 peer list" },
		{ apiRef: "Company.rank", label: "Peer Ranking", desc: "주요 지표 동종업계 순위" },
		{ apiRef: "Company.network", label: "Network", desc: "공급망 · 고객 · 경쟁자 네트워크" },
	];

	let selected = $state("Company.industry");
	let payload = $state(null);
	let loading = $state(true);
	let error = $state(null);

	async function fetch(apiRef) {
		loading = true;
		error = null;
		payload = null;
		try {
			const r = await dlCall(apiRef, { target: dash.stockCode });
			payload = r?.data ?? null;
		} catch (e) {
			error = { message: e?.message || String(e) };
		} finally {
			loading = false;
		}
	}

	function select(apiRef) {
		selected = apiRef;
		fetch(apiRef);
	}

	$effect(() => {
		dash.stockCode;
		fetch(selected);
	});

	onMount(() => {
		fetch(selected);
	});

	const currentMeta = $derived(VIEWS.find((v) => v.apiRef === selected) || VIEWS[0]);
</script>

<div class="flex flex-col gap-4">
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				<Factory size={15} />
				Industry — 동종업계 · peers · 네트워크
			</Card.Title>
			<Card.Description class="text-[11px] flex items-start gap-1.5 mt-1">
				<Info size={11} class="shrink-0 mt-0.5" />
				<span>{currentMeta.desc}</span>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-1">
				{#each VIEWS as v}
					<button
						type="button"
						class={cn(
							"px-2.5 py-1 rounded-md border text-[12px] font-medium transition-colors",
							selected === v.apiRef
								? "border-primary bg-primary/10 text-foreground"
								: "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
						)}
						onclick={() => select(v.apiRef)}
						title={v.desc}
					>
						{v.label}
					</button>
				{/each}
			</div>
		</Card.Content>
	</Card.Root>

	{#if error}
		<Card.Root class="border-destructive/30">
			<Card.Header>
				<Card.Title class="text-[14px] text-destructive">{currentMeta.label} 로드 실패</Card.Title>
				<Card.Description class="text-[11px]">{error.message}</Card.Description>
			</Card.Header>
		</Card.Root>
	{:else}
		<AnalysisAxisCard {payload} {loading} />
	{/if}
</div>
