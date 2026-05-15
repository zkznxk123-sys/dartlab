<!--
	Story Hub — 14 analysis axes 의 perspective 묶음 (UI layer).
	dartlab story 엔진은 6 막 narrative; 본 hub 는 perspective 필터로
	axis 묶음을 보여주는 UI 추가 layer.

	Layout (사용자 vision):
	  상단 perspective tabs (5)
	  좌측 axis list (perspective 별 highlight)
	  본문 선택된 axis 의 AnalysisAxisCard
-->
<script>
	import { BookOpen, Info } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadEngineAxis } from "$lib/dashboard/data/loaders.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import * as Card from "$lib/ui/card";
	import { cn } from "$lib/utils.js";

	const dash = getDashboardStore();

	const PERSPECTIVES = [
		{
			key: "investor",
			label: "투자관점",
			desc: "수익 창출력 · 성장 동력 · 자본 효율",
			axes: ["수익성", "성장성", "효율성", "이익품질", "투자효율"],
		},
		{
			key: "credit",
			label: "신용관점",
			desc: "지급능력 · 부채 부담 · 현금흐름 안정성",
			axes: ["안정성", "현금흐름", "자금조달", "자산구조"],
		},
		{
			key: "ma",
			label: "M&A 관점",
			desc: "수익원 다각화 · 자본배분 · 사업부 강점",
			axes: ["수익구조", "자본배분", "비용구조", "투자효율"],
		},
		{
			key: "esg",
			label: "ESG 관점",
			desc: "거버넌스 · 재무 신뢰성 · 공시 품질",
			axes: ["재무정합성", "종합평가"],
		},
		{
			key: "shock",
			label: "거시충격",
			desc: "외부 충격 시 회복 탄력 · 유동성 buffer",
			axes: ["안정성", "현금흐름", "자금조달"],
		},
	];

	const ALL_AXES = [
		"수익구조", "비용구조", "수익성", "성장성", "이익품질",
		"자산구조", "자금조달", "안정성", "효율성", "현금흐름",
		"자본배분", "투자효율", "종합평가", "재무정합성",
	];

	let perspectiveKey = $state("investor");
	let selectedAxis = $state("수익성");
	let axisPayload = $state(null);
	let axisLoading = $state(true);
	let axisError = $state(null);

	async function fetchAxis(axis) {
		axisLoading = true;
		axisError = null;
		axisPayload = null;
		const r = await loadEngineAxis("Company.analysis", dash.stockCode, axis);
		if (r.ok) {
			axisPayload = r.data.payload;
		} else {
			axisError = r.error;
		}
		axisLoading = false;
	}

	function selectPerspective(key) {
		perspectiveKey = key;
		const persp = PERSPECTIVES.find((p) => p.key === key);
		if (persp && persp.axes.length) {
			selectedAxis = persp.axes[0];
			fetchAxis(selectedAxis);
		}
	}

	function selectAxis(axis) {
		selectedAxis = axis;
		fetchAxis(axis);
	}

	$effect(() => {
		dash.stockCode;
		fetchAxis(selectedAxis);
	});

	const currentPerspective = $derived(
		PERSPECTIVES.find((p) => p.key === perspectiveKey) || PERSPECTIVES[0]
	);

	function isPersAxis(axis) {
		return currentPerspective.axes.includes(axis);
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Perspective tabs -->
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				<BookOpen size={15} />
				Story — 관점별 분석 (perspective UI layer)
			</Card.Title>
			<Card.Description class="text-[11px] flex items-start gap-1.5 mt-1">
				<Info size={11} class="shrink-0 mt-0.5" />
				<span>{currentPerspective.desc}</span>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-1">
				{#each PERSPECTIVES as p}
					<button
						type="button"
						class={cn(
							"px-3 py-1.5 rounded-md border text-[12px] font-medium transition-colors",
							perspectiveKey === p.key
								? "border-primary bg-primary/10 text-foreground"
								: "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
						)}
						onclick={() => selectPerspective(p.key)}
						title={p.desc}
					>
						{p.label}
					</button>
				{/each}
			</div>
		</Card.Content>
	</Card.Root>

	<!-- Axis list (좌) + 본문 (우) — flex split -->
	<div class="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-4">
		<Card.Root class="self-start">
			<Card.Header>
				<Card.Title class="text-[12px]">14 분석 축</Card.Title>
				<Card.Description class="text-[10px]">{currentPerspective.label} 강조</Card.Description>
			</Card.Header>
			<Card.Content class="p-2">
				<ul class="flex flex-col gap-0.5">
					{#each ALL_AXES as axis}
						{@const pers = isPersAxis(axis)}
						<li>
							<button
								type="button"
								class={cn(
									"w-full px-2.5 py-1.5 rounded text-left text-[12px] transition-colors",
									selectedAxis === axis
										? "bg-secondary text-foreground font-medium"
										: pers
											? "text-foreground hover:bg-muted"
											: "text-muted-foreground/50 hover:bg-muted hover:text-muted-foreground"
								)}
								onclick={() => selectAxis(axis)}
							>
								<div class="flex items-center justify-between gap-2">
									<span class="truncate">{axis}</span>
									{#if pers}
										<span class="text-[9px] text-primary font-medium uppercase tracking-wide">●</span>
									{/if}
								</div>
							</button>
						</li>
					{/each}
				</ul>
			</Card.Content>
		</Card.Root>

		<div>
			{#if axisError}
				<Card.Root class="border-destructive/30">
					<Card.Header>
						<Card.Title class="text-[14px] text-destructive">{selectedAxis} 로드 실패</Card.Title>
						<Card.Description class="text-[11px]">{axisError.message}</Card.Description>
					</Card.Header>
				</Card.Root>
			{:else}
				<AnalysisAxisCard payload={axisPayload} loading={axisLoading} />
			{/if}
		</div>
	</div>
</div>
