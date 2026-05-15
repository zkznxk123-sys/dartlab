<!--
	GovernanceScorecard — Company.governance 의 16 col scorecard 시각화.
	1 row × 16 col DataFrame → 카드 그리드.
-->
<script>
	import * as Card from "$lib/ui/card";
	import { Skeleton } from "$lib/ui/skeleton";
	import { cn } from "$lib/utils.js";

	let { row = {}, columns = [], loading = false } = $props();

	// 핵심 metric 우선 정렬 — 등급/총점 먼저, 그 다음 비율, 그 다음 raw count.
	const HIGHLIGHT_KEYS = ["등급", "총점", "지분율", "사외이사비율"];
	const SUFFIX_PCT = ["비율", "지분율"];

	const sorted = $derived(
		columns
			.filter((c) => c !== "stockCode")
			.sort((a, b) => {
				const ai = HIGHLIGHT_KEYS.indexOf(a);
				const bi = HIGHLIGHT_KEYS.indexOf(b);
				if (ai >= 0 && bi >= 0) return ai - bi;
				if (ai >= 0) return -1;
				if (bi >= 0) return 1;
				return a.localeCompare(b, "ko");
			})
	);

	function formatValue(key, value) {
		if (value == null || value === "") return "—";
		if (typeof value === "number") {
			const isPct = SUFFIX_PCT.some((s) => key.includes(s));
			if (isPct) return `${(value * 100).toFixed(1)}%`;
			if (Number.isInteger(value)) return value.toLocaleString();
			return value.toFixed(2);
		}
		return String(value);
	}

	function isHighlight(key) {
		return HIGHLIGHT_KEYS.includes(key);
	}
</script>

<Card.Root>
	<Card.Header>
		<Card.Title class="text-[14px]">거버넌스 스코어카드</Card.Title>
		<Card.Description class="text-[11px]">
			지분구조 · 이사회 · 임원 변동 16 지표
		</Card.Description>
	</Card.Header>
	<Card.Content>
		{#if loading}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each Array(8) as _}
					<Skeleton class="h-16" />
				{/each}
			</div>
		{:else if sorted.length === 0}
			<div class="text-[12px] text-muted-foreground py-6 text-center">데이터 없음</div>
		{:else}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each sorted as key}
					<div
						class={cn(
							"rounded-md border border-border bg-card/40 p-2.5",
							isHighlight(key) && "border-primary/30 bg-primary/[0.03]"
						)}
					>
						<div class="text-[10px] text-muted-foreground truncate uppercase tracking-wide">
							{key}
						</div>
						<div
							class={cn(
								"mt-1 text-[15px] font-semibold font-mono tabular-nums truncate",
								isHighlight(key) ? "text-primary" : "text-foreground"
							)}
						>
							{formatValue(key, row[key])}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</Card.Content>
</Card.Root>
