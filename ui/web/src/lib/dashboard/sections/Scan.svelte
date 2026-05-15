<!--
	Scan — 다중 종목 스크리너 (Editorial Financial Terminal 톤).
	dartlab scan.* 엔진 호출 → DataFrame (종목코드/종목명/axis별 metrics/등급) →
	정렬 + 검색 + 등급 필터 + percentile 색 표.

	Phase G 골격: 5 핵심 axis (profitability / growth / valuation / efficiency / liquidity).
	향후: Distribution panel + Preset modal + SavedSets + InsightsFeed + multi-axis join.
-->
<script>
	import { onMount } from "svelte";
	import { Filter, Search, ArrowUpDown, ChevronDown, ChevronUp } from "lucide-svelte";
	import { dlCall } from "$lib/api/dlCall.js";
	import { isFiniteNum, fmtKrw, fmtPct } from "$lib/dashboard/chart/util.js";

	const AXES = [
		{ key: "scan.profitability", label: "수익성", desc: "영업이익률 · 순이익률 · ROE · ROA · 등급", numericCols: ["영업이익률", "순이익률", "ROE", "ROA"], gradeCol: "등급" },
		{ key: "scan.growth", label: "성장성", desc: "매출CAGR · 영업이익CAGR · 순이익CAGR · 패턴", numericCols: ["매출CAGR", "영업이익CAGR", "순이익CAGR", "years"], gradeCol: "등급" },
		{ key: "scan.valuation", label: "밸류에이션", desc: "PER · PBR · PSR · 배당수익률 · 등급", numericCols: ["PER", "PBR", "PSR", "배당수익률"], gradeCol: "등급" },
		{ key: "scan.efficiency", label: "효율성", desc: "회전율 · CCC · DSO/DIO/DPO", numericCols: ["CCC", "DSO", "DIO", "DPO"], gradeCol: "등급" },
		{ key: "scan.liquidity", label: "유동성", desc: "유동비율 · 당좌비율 · cash ratio", numericCols: ["유동비율", "당좌비율"], gradeCol: "등급" },
	];

	let selectedAxis = $state(AXES[0]);
	let loading = $state(true);
	let error = $state(null);
	let rows = $state([]);
	let columns = $state([]);
	let totalRows = $state(0);
	let searchQuery = $state("");
	let gradeFilter = $state("all");
	let sortKey = $state(null);
	let sortDir = $state("desc");
	let abortCtrl = null;

	async function fetchAxis(axis) {
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		loading = true;
		error = null;
		rows = [];
		columns = [];
		try {
			const r = await dlCall(axis.key, { signal: abortCtrl.signal });
			const d = r?.data;
			if (d && d._type === "DataFrame" && Array.isArray(d.rows)) {
				rows = d.rows;
				columns = d.columns;
				totalRows = d.rowCount;
				if (axis.numericCols.length > 0 && !sortKey) {
					sortKey = axis.numericCols[0];
				}
			} else {
				rows = [];
				columns = [];
				totalRows = 0;
				error = { message: "DataFrame 형태 응답이 아님" };
			}
		} catch (e) {
			if (e?.name !== "AbortError") error = { message: e?.message || String(e) };
		} finally {
			loading = false;
		}
	}

	function selectAxis(axis) {
		selectedAxis = axis;
		sortKey = null;
		searchQuery = "";
		gradeFilter = "all";
		fetchAxis(axis);
	}

	onMount(() => fetchAxis(selectedAxis));

	const grades = $derived.by(() => {
		const seen = new Set();
		for (const r of rows) {
			const g = r?.[selectedAxis.gradeCol];
			if (g != null) seen.add(String(g));
		}
		return ["all", ...seen];
	});

	const filtered = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		const grade = gradeFilter;
		return rows.filter((r) => {
			if (q) {
				const code = String(r["종목코드"] ?? "").toLowerCase();
				const name = String(r["종목명"] ?? "").toLowerCase();
				if (!code.includes(q) && !name.includes(q)) return false;
			}
			if (grade !== "all") {
				if (String(r?.[selectedAxis.gradeCol]) !== grade) return false;
			}
			return true;
		});
	});

	const sorted = $derived.by(() => {
		if (!sortKey) return filtered;
		const dir = sortDir === "asc" ? 1 : -1;
		return [...filtered].sort((a, b) => {
			const av = a?.[sortKey];
			const bv = b?.[sortKey];
			const aFinite = isFiniteNum(av);
			const bFinite = isFiniteNum(bv);
			if (!aFinite && !bFinite) return 0;
			if (!aFinite) return 1;
			if (!bFinite) return -1;
			return (av - bv) * dir;
		});
	});

	// 활성 컬럼별 p10/p90 percentile — 셀 색
	const percentiles = $derived.by(() => {
		const map = new Map();
		for (const col of selectedAxis.numericCols) {
			const vals = rows.map((r) => r?.[col]).filter(isFiniteNum);
			if (vals.length < 10) continue;
			vals.sort((a, b) => a - b);
			map.set(col, {
				p10: vals[Math.floor(vals.length * 0.1)],
				p90: vals[Math.floor(vals.length * 0.9)],
				p50: vals[Math.floor(vals.length * 0.5)],
			});
		}
		return map;
	});

	function cellColor(col, value) {
		const p = percentiles.get(col);
		if (!p || !isFiniteNum(value)) return null;
		// 높을수록 좋은 컬럼 가정 (PER 등 낮을수록 좋은 건 향후 보강)
		const lowerBetter = col === "PER" || col === "PBR" || col === "PSR" || col === "CCC" || col === "DSO" || col === "DIO";
		const good = lowerBetter ? value <= p.p10 : value >= p.p90;
		const bad = lowerBetter ? value >= p.p90 : value <= p.p10;
		if (good) return "var(--ed-up)";
		if (bad) return "var(--ed-down)";
		return null;
	}

	function fmtCell(col, v) {
		if (v == null) return "—";
		if (typeof v === "boolean") return v ? "✓" : "—";
		if (typeof v === "number") {
			if (col === "시가총액" || col === "revenue") return fmtKrw(v);
			if (col === "PER" || col === "PBR" || col === "PSR") return v.toFixed(2);
			if (col.includes("CAGR") || col.includes("률") || col === "ROE" || col === "ROA" || col === "배당수익률") return fmtPct(v);
			if (col === "DSO" || col === "DIO" || col === "DPO" || col === "CCC") return v.toFixed(0) + "일";
			if (Math.abs(v) >= 1e9) return fmtKrw(v);
			return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
		}
		return String(v);
	}

	function toggleSort(col) {
		if (sortKey === col) {
			sortDir = sortDir === "asc" ? "desc" : "asc";
		} else {
			sortKey = col;
			sortDir = "desc";
		}
	}

	const limited = $derived(sorted.slice(0, 100));
</script>

<div class="flex flex-col gap-4">
	<!-- axis tabs + description -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">Scan Axis</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">{selectedAxis.label}</h2>
			</div>
			<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">
				{loading ? "—" : `${filtered.length} / ${totalRows} 종목`}
			</div>
		</div>
		<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">{selectedAxis.desc}</div>
		<div class="flex flex-wrap gap-1">
			{#each AXES as ax}
				<button type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					style="background: {selectedAxis.key === ax.key ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'}; border-color: {selectedAxis.key === ax.key ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {selectedAxis.key === ax.key ? 'var(--ed-text)' : 'var(--ed-text-2)'};"
					onclick={() => selectAxis(ax)}>
					{ax.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- Filter bar -->
	<div class="ed-card">
		<div class="grid grid-cols-[1fr_auto_auto] gap-3 items-center">
			<div class="flex items-center gap-2 px-2.5 py-1.5 rounded border" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
				<Search size={12} style="color: var(--ed-text-3);" />
				<input type="text" bind:value={searchQuery} placeholder="종목명 / 종목코드 검색..."
					class="flex-1 bg-transparent outline-none text-[12px]" style="color: var(--ed-text); font-family: var(--font-body);" />
			</div>
			<div class="flex items-center gap-2 text-[11px]">
				<Filter size={12} style="color: var(--ed-text-3);" />
				<select bind:value={gradeFilter}
					class="px-2 py-1 rounded border text-[11px] outline-none"
					style="border-color: var(--ed-line); background: var(--ed-surface-2); color: var(--ed-text); font-family: var(--font-body);">
					{#each grades as g}
						<option value={g}>{g === "all" ? "전체 등급" : g}</option>
					{/each}
				</select>
			</div>
			<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">
				상위 {Math.min(100, sorted.length)} / {sorted.length} 표시
			</div>
		</div>
	</div>

	<!-- Grid table -->
	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
			<button class="mt-2 px-3 py-1 rounded border text-[11px]" style="border-color: var(--ed-line); color: var(--ed-text);"
				onclick={() => fetchAxis(selectedAxis)}>retry</button>
		</div>
	{:else if loading}
		<div class="ed-card">
			<div class="ed-eyebrow mb-2">Loading</div>
			<div class="flex flex-col gap-1.5">
				{#each [1, 2, 3, 4, 5, 6, 7, 8] as _}
					<div class="editorial-skeleton h-5 w-full"></div>
				{/each}
			</div>
		</div>
	{:else}
		<div class="ed-card" style="padding: 0;">
			<div class="overflow-x-auto" style="max-height: 70vh;">
				<table class="w-full text-[11.5px]" style="font-family: var(--font-num);">
					<thead style="position: sticky; top: 0; background: var(--ed-surface); z-index: 1;">
						<tr style="border-bottom: 1px solid var(--ed-line);">
							{#each columns as col}
								<th class="text-left px-2.5 py-2 whitespace-nowrap cursor-pointer select-none"
									style="color: var(--ed-text-3); font-weight: 600; font-family: var(--font-body); text-transform: uppercase; letter-spacing: 0.04em; font-size: 10.5px;"
									onclick={() => toggleSort(col)}>
									<span class="inline-flex items-center gap-1">
										{col}
										{#if sortKey === col}
											{#if sortDir === "asc"}<ChevronUp size={11} />{:else}<ChevronDown size={11} />{/if}
										{:else}
											<ArrowUpDown size={10} class="opacity-30" />
										{/if}
									</span>
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each limited as r, i}
							<tr style="border-bottom: 1px solid var(--ed-line);" class="hover-row">
								{#each columns as col}
									{@const v = r?.[col]}
									{@const color = cellColor(col, v)}
									{@const isCode = col === "종목코드"}
									{@const isName = col === "종목명"}
									{@const isGrade = col === selectedAxis.gradeCol}
									<td class="px-2.5 py-1.5 whitespace-nowrap"
										style="color: {color || (isName ? 'var(--ed-text)' : 'var(--ed-text-2)')}; {isCode ? 'font-family: var(--font-num);' : ''} {isName ? 'font-family: var(--font-body); font-weight: 500;' : ''}">
										{#if isGrade && v != null}
											<span class="editorial-chip">{v}</span>
										{:else}
											{fmtCell(col, v)}
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>

<style>
	.hover-row:hover {
		background: color-mix(in srgb, var(--ed-surface-2) 50%, transparent);
	}
</style>
