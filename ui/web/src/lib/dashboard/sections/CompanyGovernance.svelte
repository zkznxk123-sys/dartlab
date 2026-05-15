<!--
	Company > Governance — 거버넌스 16 지표 scorecard + 등급/총점 hero.
-->
<script>
	import { onMount } from "svelte";
	import { Shield } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadGovernance } from "$lib/dashboard/data/loaders.js";
	import GovernanceScorecard from "$lib/dashboard/cards/GovernanceScorecard.svelte";
	import * as Card from "$lib/ui/card";
	import { Skeleton } from "$lib/ui/skeleton";
	import { cn } from "$lib/utils.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let row = $state({});
	let columns = $state([]);
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		const result = await loadGovernance(dash.stockCode);
		if (result.ok) {
			row = result.data.row;
			columns = result.data.columns;
		} else {
			error = result.error;
			row = {};
			columns = [];
		}
		loading = false;
	}

	$effect(() => {
		dash.stockCode;
		fetchAll();
	});

	onMount(() => {
		fetchAll();
	});

	// Hero: 등급 + 총점
	const grade = $derived(row["등급"] ?? "—");
	const totalScore = $derived(row["총점"]);
	const scoreLabel = $derived(
		typeof totalScore === "number" ? totalScore.toFixed(1) : "—"
	);
	const gradeColor = $derived(
		typeof grade === "string" && /^A/.test(grade)
			? "text-primary"
			: typeof grade === "string" && /^B/.test(grade)
				? "text-muted-foreground"
				: "text-foreground"
	);
</script>

<div class="flex flex-col gap-4">
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				<Shield size={15} />
				거버넌스 종합 등급
			</Card.Title>
			<Card.Description class="text-[11px]">지분구조 · 이사회 · 임원 변동의 가중 합성</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if loading}
				<div class="flex items-center gap-4">
					<Skeleton class="h-16 w-24" />
					<Skeleton class="h-16 w-32" />
				</div>
			{:else if error}
				<div class="text-[12px] text-destructive">{error.message}</div>
			{:else}
				<div class="flex items-baseline gap-6">
					<div>
						<div class="text-[10px] text-muted-foreground uppercase tracking-wider">등급</div>
						<div class={cn("text-[42px] font-bold font-mono tabular-nums leading-none mt-1", gradeColor)}>
							{grade}
						</div>
					</div>
					<div>
						<div class="text-[10px] text-muted-foreground uppercase tracking-wider">총점</div>
						<div class="text-[28px] font-semibold font-mono tabular-nums leading-none mt-1 text-foreground">
							{scoreLabel}
						</div>
					</div>
				</div>
			{/if}
		</Card.Content>
	</Card.Root>

	<GovernanceScorecard {row} {columns} {loading} />
</div>
