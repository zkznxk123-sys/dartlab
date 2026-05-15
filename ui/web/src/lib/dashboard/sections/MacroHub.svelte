<!--
	Macro Hub — dartlab.macro.* 12 sub-engines (회사 무관).
	각 sub-engine 이 별도 capability — 클릭 시 dlCall(apiRef) 직접 호출.
-->
<script>
	import { onMount } from "svelte";
	import { Globe, Info } from "lucide-svelte";
	import { dlCall } from "$lib/api/dlCall.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import * as Card from "$lib/ui/card";
	import { cn } from "$lib/utils.js";

	// 12 macro sub-engines (capability registry 일치)
	const SUB_ENGINES = [
		{ apiRef: "macro.rates", label: "금리", desc: "기준금리 · 국고채 · 수익률곡선" },
		{ apiRef: "macro.assets", label: "자산", desc: "자산군별 수익률 · 상관" },
		{ apiRef: "macro.cycle", label: "사이클", desc: "경기 사이클 phase" },
		{ apiRef: "macro.liquidity", label: "유동성", desc: "통화·신용 유동성" },
		{ apiRef: "macro.sentiment", label: "심리", desc: "투자 sentiment gauge" },
		{ apiRef: "macro.inventory", label: "재고", desc: "재고 사이클 추이" },
		{ apiRef: "macro.trade", label: "교역", desc: "수출입 · 무역 흐름" },
		{ apiRef: "macro.corporate", label: "기업", desc: "법인 활동 거시 지표" },
		{ apiRef: "macro.forecast", label: "전망", desc: "거시 변수 예측" },
		{ apiRef: "macro.scenario", label: "시나리오", desc: "시나리오 충격 분석" },
		{ apiRef: "macro.crisis", label: "위기", desc: "위기 시그널 모니터" },
		{ apiRef: "macro.summary", label: "요약", desc: "거시 종합 요약" },
	];

	let selected = $state("macro.rates");
	let payload = $state(null);
	let loading = $state(true);
	let error = $state(null);

	async function fetch(apiRef) {
		loading = true;
		error = null;
		payload = null;
		try {
			const r = await dlCall(apiRef);
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

	onMount(() => {
		fetch(selected);
	});

	const currentMeta = $derived(SUB_ENGINES.find((s) => s.apiRef === selected) || SUB_ENGINES[0]);
</script>

<div class="flex flex-col gap-4">
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				<Globe size={15} />
				Macro — 거시 환경 12 sub-engines
			</Card.Title>
			<Card.Description class="text-[11px] flex items-start gap-1.5 mt-1">
				<Info size={11} class="shrink-0 mt-0.5" />
				<span>{currentMeta.desc}</span>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-1">
				{#each SUB_ENGINES as eng}
					<button
						type="button"
						class={cn(
							"px-2.5 py-1 rounded-md border text-[12px] font-medium transition-colors",
							selected === eng.apiRef
								? "border-primary bg-primary/10 text-foreground"
								: "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
						)}
						onclick={() => select(eng.apiRef)}
						title={eng.desc}
					>
						{eng.label}
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
