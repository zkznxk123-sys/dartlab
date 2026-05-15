<!--
	Analysis > 자산구조 — assetStructure.latest+history+diagnosis, workingCapital, capexPattern.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import Donut from "$lib/dashboard/chart/Donut.svelte";

	let { payload = null, loading = false } = $props();

	const asset = $derived(payload?.assetStructure || null);
	const assetLatest = $derived(asset?.latest || {});
	const assetHist = $derived(asset?.history || []);
	const diagnosis = $derived(asset?.diagnosis || "");
	const wc = $derived(payload?.workingCapital?.latest || {});
	const wcHist = $derived(payload?.workingCapital?.history || []);
	const capex = $derived(payload?.capexPattern?.latest || {});
	const capexHist = $derived(payload?.capexPattern?.history || []);
	const flags = $derived(Array.isArray(payload?.assetFlags) ? payload.assetFlags : []);

	const donutData = $derived([
		{ key: "opAssets", label: "영업", value: assetLatest.opAssetsPct ?? 0, color: "var(--ed-brand)" },
		{ key: "nonOpAssets", label: "비영업", value: assetLatest.nonOpAssetsPct ?? 0, color: "var(--ed-text-2)" },
		{ key: "otherAssets", label: "기타", value: assetLatest.otherAssetsPct ?? 0, color: "var(--ed-text-3)" },
	].filter((d) => isFiniteNum(d.value) && d.value > 0));

	function fmtKrw(v) {
		if (!isFiniteNum(v)) return "—";
		const a = Math.abs(v);
		if (a >= 1e12) return (v / 1e12).toFixed(2) + "조";
		if (a >= 1e8) return (v / 1e8).toFixed(2) + "억";
		return v.toLocaleString();
	}
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- 자산 구성 (Donut) + diagnosis -->
		{#if donutData.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">자산 구성 · 영업/비영업/기타</div>
				<div class="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4 items-center">
					<Donut data={donutData} centerLabel="총자산" centerValue={fmtKrw(assetLatest.totalAssets)} />
					<div class="text-[12px] space-y-1">
						{#each donutData as d}
							<div class="flex items-center gap-2"><span class="inline-block w-2 h-2 rounded" style="background: {d.color};"></span><span style="color: var(--ed-text);">{d.label}</span><span class="ed-num ml-auto" style="color: var(--ed-text-2);">{d.value.toFixed(1)}%</span></div>
						{/each}
						{#if diagnosis}<div class="mt-3 text-[11px] pt-2 border-t" style="color: var(--ed-text-2); border-color: var(--ed-line);">{diagnosis}</div>{/if}
					</div>
				</div>
			</div>
		{/if}

		<!-- 자산 비중 추이 -->
		{#if assetHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">영업 / 비영업 자산 비중 · 추이</div>
				<LineTrend history={assetHist} series={[
					{ key: "opAssetsPct", label: "영업 %", color: "var(--ed-brand)" },
					{ key: "nonOpAssetsPct", label: "비영업 %", color: "var(--ed-text-2)" },
				]} xKey="period" height={200} yIsPercent={true} />
			</div>
		{/if}

		<!-- Working Capital KPI -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">WC</div><div class="ed-num text-[18px] mt-1" style="color: {wc.wc < 0 ? 'var(--ed-down)' : 'var(--ed-text)'};">{fmtKrw(wc.wc)}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">CCC</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(wc.ccc) ? wc.ccc.toFixed(1) : "—"}<span class="text-[10px]" style="color: var(--ed-text-3);">d</span></div></div>
			<div class="ed-card"><div class="ed-eyebrow">DSO</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(wc.receivableDays) ? wc.receivableDays.toFixed(1) : "—"}<span class="text-[10px]" style="color: var(--ed-text-3);">d</span></div></div>
			<div class="ed-card"><div class="ed-eyebrow">DIO</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(wc.inventoryDays) ? wc.inventoryDays.toFixed(1) : "—"}<span class="text-[10px]" style="color: var(--ed-text-3);">d</span></div></div>
		</div>

		<!-- WC days trend -->
		{#if wcHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Working Capital Days · 추이</div>
				<LineTrend history={wcHist} series={[
					{ key: "receivableDays", label: "매출채권 일", color: "var(--ed-brand)" },
					{ key: "inventoryDays", label: "재고 일", color: "var(--ed-text-2)" },
					{ key: "payableDays", label: "매입채무 일", color: "var(--ed-text-3)" },
					{ key: "ccc", label: "CCC", color: "var(--ed-down)" },
				]} xKey="period" height={220} yIsPercent={false} />
			</div>
		{/if}

		<!-- Capex pattern -->
		{#if capexHist.length > 0}
			<div class="ed-card">
				<div class="flex items-baseline justify-between mb-2">
					<div class="ed-eyebrow">Capex 패턴 · capex / 감가상각</div>
					<div class="text-[10px]" style="color: var(--ed-text-3);">{capex.investmentType || "—"} · ratio {isFiniteNum(capex.capexToDepRatio) ? capex.capexToDepRatio.toFixed(2) : "—"}x</div>
				</div>
				<LineTrend history={capexHist} series={[
					{ key: "capexToDepRatio", label: "Capex / Dep", color: "var(--ed-brand)" },
					{ key: "cipPct", label: "CIP %", color: "var(--ed-text-2)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if flags.length > 0}
			<div class="ed-card"><div class="ed-eyebrow mb-2">Flags ({flags.length})</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each flags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
