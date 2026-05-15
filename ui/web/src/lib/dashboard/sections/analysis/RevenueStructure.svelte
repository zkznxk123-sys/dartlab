<!--
	RevenueStructure — Analysis 수익구조 axis specialized 시각.
	응답: {
	  profile: { sector, products },
	  segmentComposition: null | {...},
	  segmentTrend: null | {...},
	  growth: { yoy, cagr3y, quarterlySelect (polars repr) },
	  growthContribution: null,
	  concentration: null,
	  revenueQuality: { cashConversion, cashConversionLabel, grossMargin, grossMarginTrend: [...], grossMarginDirection },
	  revenueFlags: []
	}
-->
<script>
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import Sparkline from "$lib/dashboard/cards/Sparkline.svelte";
	import Donut from "$lib/dashboard/chart/Donut.svelte";
	import { fmtPct, fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const profile = $derived(payload?.profile || null);
	const growth = $derived(payload?.growth || null);
	const quality = $derived(payload?.revenueQuality || null);
	const segments = $derived(payload?.segmentComposition || null);
	const flags = $derived(payload?.revenueFlags || []);

	const segmentSlices = $derived.by(() => {
		if (!segments || typeof segments !== "object") return [];
		// segmentComposition shape 가 backend 별로 다를 수 있어서 일반화.
		if (Array.isArray(segments.items)) {
			return segments.items.map((s) => ({
				label: s.name || s.label || s.segment || String(s.key ?? ""),
				value: s.value ?? s.amount ?? s.share ?? 0,
			}));
		}
		if (Array.isArray(segments)) {
			return segments.map((s) => ({
				label: s.name || s.label || s.segment || "",
				value: s.value ?? s.share ?? 0,
			}));
		}
		// flat dict: { segmentName: value }
		const entries = Object.entries(segments).filter(([, v]) => isFiniteNum(v) && v > 0);
		return entries.map(([k, v]) => ({ label: k, value: v }));
	});
</script>

{#if loading}
	<div class="ed-card">
		<div class="ed-eyebrow mb-2">Loading</div>
		<div class="editorial-skeleton h-32 w-full"></div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;">
		<div class="ed-eyebrow mb-1">No data</div>
		<div class="text-[12px]" style="color: var(--ed-text-2);">수익구조 데이터 없음</div>
	</div>
{:else}
	<!-- Profile chip -->
	{#if profile}
		<div class="ed-card mb-4 flex flex-col gap-1">
			<div class="ed-eyebrow">Business profile</div>
			{#if profile.sector}<div class="text-[13px]" style="color: var(--ed-text);">{profile.sector}</div>{/if}
			{#if profile.products}<div class="text-[12px]" style="color: var(--ed-text-2);">{profile.products}</div>{/if}
		</div>
	{/if}

	<!-- KPI strip 3 칸 (growth + quality 핵심) -->
	<div class="grid grid-cols-3 gap-3 mb-4">
		<KpiTile
			label="CAGR 3y"
			value={growth?.cagr3y}
			unit="%"
		/>
		<KpiTile
			label="현금전환율 CCR"
			value={quality?.cashConversion}
			unit="%"
			deltaSuffix={quality?.cashConversionLabel || ""}
		/>
		<KpiTile
			label="매출총이익률 GPM"
			value={quality?.grossMargin}
			unit="%"
			deltaSuffix={quality?.grossMarginDirection || ""}
		/>
	</div>

	<!-- Segment composition Donut (if available) -->
	{#if segmentSlices.length > 0}
		<div class="ed-card mb-4">
			<div class="ed-eyebrow mb-3">매출 세그먼트 구성</div>
			<Donut slices={segmentSlices} height={240} />
		</div>
	{:else}
		<div class="ed-card mb-4" style="border-style: dashed;">
			<div class="ed-eyebrow mb-1">매출 세그먼트</div>
			<div class="text-[11px]" style="color: var(--ed-text-3);">
				segmentComposition 데이터 없음 — 회사 공시에 세그먼트 분리 미공시 (또는 dartlab gather 단계 미수집)
			</div>
		</div>
	{/if}

	<!-- GPM 4 분기 sparkline (revenueQuality.grossMarginTrend) -->
	{#if quality?.grossMarginTrend && Array.isArray(quality.grossMarginTrend) && quality.grossMarginTrend.length >= 2}
		<div class="ed-card mb-4">
			<div class="flex items-baseline justify-between mb-2">
				<div class="ed-eyebrow">GPM 최근 추이</div>
				<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">
					{quality.grossMarginTrend[0].toFixed(1)}% → {quality.grossMarginTrend[quality.grossMarginTrend.length - 1].toFixed(1)}%
				</div>
			</div>
			<Sparkline data={quality.grossMarginTrend} class="h-12 w-full" />
		</div>
	{/if}

	<!-- Polars quarterly select (textual) -->
	{#if growth?.quarterlySelect}
		<details class="ed-card mb-4">
			<summary class="cursor-pointer select-none ed-eyebrow">분기별 매출 시계열 (raw polars repr)</summary>
			<pre class="mt-3 overflow-x-auto text-[10.5px] leading-snug"
				style="font-family: var(--font-num); color: var(--ed-text-2); max-height: 320px;">{growth.quarterlySelect}</pre>
		</details>
	{/if}

	<!-- Flags -->
	{#if Array.isArray(flags) && flags.length > 0}
		<div class="ed-card mb-4" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-2" style="color: var(--ed-down);">매출 quality flags</div>
			<ul class="flex flex-col gap-1 text-[11.5px]">
				{#each flags as f}
					<li style="color: var(--ed-text-2);">· {typeof f === "string" ? f : JSON.stringify(f)}</li>
				{/each}
			</ul>
		</div>
	{/if}
{/if}
