<!--
	CashFlow — Analysis 현금흐름 axis specialized.
	응답: { cashFlowOverview: { history: [{ period, ocf, icf, fcfFinancing, capex, fcf, pattern, fcfDrivers: [{factor, contribution_amt, share_pct}] }] } }
-->
<script>
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtKrw, fmtPct, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const overview = $derived(payload?.cashFlowOverview || null);
	const history = $derived(overview?.history || []);
	const latest = $derived(history[0] || null);
	const prev = $derived(history[1] || null);

	function delta(curr, prevVal) {
		if (!isFiniteNum(curr) || !isFiniteNum(prevVal)) return null;
		return curr - prevVal;
	}

	const fcfDrivers = $derived.by(() => {
		if (!latest?.fcfDrivers || !Array.isArray(latest.fcfDrivers)) return [];
		// fcfDrivers shape: {factor, contribution_amt, share_pct} — DriverBar 는 contribution_pp 기대.
		// 여기서는 share_pct 를 contribution_pp 처럼 사용 (% 단위, 양/음 부호 = 기여 방향).
		return latest.fcfDrivers.map((d) => ({
			factor: d.factor,
			contribution_pp: d.share_pct,
			share_pct: d.share_pct,
		}));
	});

	const fcfMargin = $derived.by(() => {
		if (!isFiniteNum(latest?.fcf) || !history.length) return null;
		// fcf / revenue 가 history 에 없으면 null
		return null;
	});
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !overview}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">cashFlowOverview 데이터 없음</div></div>
{:else}
	<!-- KPI 4 칸 — OCF / FCF / Capex / Pattern -->
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile
			label="영업현금흐름 OCF"
			value={latest?.ocf}
			delta={delta(latest?.ocf, prev?.ocf)}
			unit="KRW"
		/>
		<KpiTile
			label="잉여현금흐름 FCF"
			value={latest?.fcf}
			delta={delta(latest?.fcf, prev?.fcf)}
			unit="KRW"
		/>
		<KpiTile
			label="자본적지출 Capex"
			value={latest?.capex}
			delta={delta(latest?.capex, prev?.capex)}
			unit="KRW"
		/>
		<div class="ed-card flex flex-col gap-1.5">
			<div class="ed-eyebrow">현금흐름 패턴</div>
			<div class="text-[13px]" style="color: var(--ed-text);">
				{latest?.pattern || "—"}
			</div>
			<div class="text-[11px]" style="color: var(--ed-text-3);">
				{latest?.period ?? ""}
			</div>
		</div>
	</div>

	<!-- OCF/ICF/FCF trend -->
	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">OCF · ICF · FCF Trend</div>
		<LineTrend
			rows={history}
			xKey="period"
			series={[
				{ key: "ocf", label: "OCF (영업)", color: "var(--ed-up)" },
				{ key: "icf", label: "ICF (투자)", color: "var(--ed-down)" },
				{ key: "fcf", label: "FCF (잉여)", color: "var(--ed-brand)" },
				{ key: "fcfFinancing", label: "F.financing", color: "var(--ed-text-2)" },
			]}
			height={260}
			unit="KRW"
		/>
	</div>

	<!-- Capex trend -->
	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">Capex 추이</div>
		<LineTrend
			rows={history}
			xKey="period"
			series={[
				{ key: "capex", label: "Capex", color: "var(--ed-warn)" },
			]}
			height={200}
			unit="KRW"
		/>
	</div>

	<!-- FCF drivers (latest) -->
	{#if fcfDrivers.length > 0}
		<div class="ed-card mb-4">
			<div class="ed-eyebrow mb-3">{latest?.period} FCF 변동 driver 분해</div>
			<ul class="flex flex-col gap-2">
				{#each latest.fcfDrivers as d}
					<li class="grid grid-cols-[180px_1fr_120px] items-center gap-3 text-[11.5px]">
						<span class="truncate" style="color: var(--ed-text-2);" title={d.factor}>{d.factor}</span>
						<div class="relative h-3 rounded-sm" style="background: var(--ed-surface-2);">
							{#if isFiniteNum(d.share_pct)}
								<div class="absolute top-0 bottom-0 rounded-sm"
									style="
										left: 50%;
										width: {Math.abs(d.share_pct) / 2}%;
										transform: {d.share_pct < 0 ? 'translateX(-100%)' : 'none'};
										background: {d.share_pct >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};
										opacity: 0.85;
									"></div>
								<div class="absolute top-0 bottom-0 left-1/2 w-px" style="background: var(--ed-text-3); opacity: 0.5;"></div>
							{/if}
						</div>
						<span class="ed-num text-right" style="color: {isFiniteNum(d.share_pct) && d.share_pct >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">
							{isFiniteNum(d.contribution_amt) ? fmtKrw(d.contribution_amt) : "—"} ({isFiniteNum(d.share_pct) ? d.share_pct.toFixed(1) : "—"}%)
						</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- History full -->
	<details class="ed-card">
		<summary class="cursor-pointer select-none ed-eyebrow">상세 표 — {history.length} 기간 full</summary>
		<div class="mt-3 overflow-x-auto max-h-96">
			<table class="w-full text-[11px]" style="font-family: var(--font-num);">
				<thead style="position: sticky; top: 0; background: var(--ed-surface);"><tr style="border-bottom: 1px solid var(--ed-line);">
					<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Period</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">OCF</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">ICF</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">FCF</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Capex</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">F.fin</th>
					<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Pattern</th>
				</tr></thead>
				<tbody>
					{#each history as r}
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<td class="p-1.5" style="color: var(--ed-text); font-weight: 500;">{r.period ?? ""}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.ocf) && r.ocf >= 0 ? 'var(--ed-text)' : 'var(--ed-down)'};">{fmtKrw(r.ocf)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.icf) && r.icf >= 0 ? 'var(--ed-text)' : 'var(--ed-down)'};">{fmtKrw(r.icf)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.fcf) && r.fcf >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtKrw(r.fcf)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.capex)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtKrw(r.fcfFinancing)}</td>
							<td class="p-1.5 text-[10px]" style="color: var(--ed-text-3);">{r.pattern || ""}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</details>
{/if}
