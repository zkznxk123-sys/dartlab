<!--
	HistoryChart — Company.analysis(axis) 의 metric.history 시계열을
	기존 TrendChart 로 시각화. history rows 에서 numeric column 자동 추출.

	Props:
	  history: Array<{ period: string, ...numericFields }>
	  title?: string
	  pickedFields?: string[]  — 명시적 series 선택 (없으면 자동)
	  chartType?: "line" | "bar" — default "line"
	  unit?: string
-->
<script>
	import TrendChart from "$lib/chart/TrendChart.svelte";
	import { COLORS } from "$lib/chart/colors.js";

	let {
		history = [],
		title = "",
		pickedFields = null,
		chartType = "line",
		unit = "",
		maxSeries = 4,
	} = $props();

	function isNumeric(v) {
		return typeof v === "number" && Number.isFinite(v);
	}

	function detectFields(rows) {
		// period / label / quarter / date 같은 카테고리 컬럼은 series 에서 제외.
		const CATEGORY = new Set(["period", "year", "quarter", "date", "label", "key"]);
		const seenNumeric = new Map(); // field → count of non-null numeric
		for (const r of rows) {
			if (!r || typeof r !== "object") continue;
			for (const [k, v] of Object.entries(r)) {
				if (CATEGORY.has(k)) continue;
				if (isNumeric(v)) {
					seenNumeric.set(k, (seenNumeric.get(k) || 0) + 1);
				}
			}
		}
		// 적어도 절반 row 에서 numeric 인 field 만 채택. 가장 많은 순.
		const threshold = Math.max(1, Math.floor(rows.length / 2));
		return [...seenNumeric.entries()]
			.filter(([, c]) => c >= threshold)
			.sort(([, a], [, b]) => b - a)
			.map(([k]) => k);
	}

	function pickCategory(rows) {
		for (const k of ["period", "quarter", "year", "date", "label"]) {
			if (rows[0] && k in rows[0]) return k;
		}
		return "period";
	}

	const sortedRows = $derived(
		[...history].reverse() // dartlab response 는 최신 → 과거 순. 차트는 과거 → 최신 자연.
	);
	const categoryKey = $derived(sortedRows[0] ? pickCategory(sortedRows) : "period");
	const fields = $derived(
		pickedFields && pickedFields.length
			? pickedFields
			: detectFields(sortedRows)
	);

	// % 같은 단위 가진 metric 은 같은 차트, 절대값 metric 은 별도 — Phase 0 에서는
	// 1 차트에 다 표시. 향후 분리 가능.

	const spec = $derived({
		title,
		chartType,
		categories: sortedRows.map((r) => String(r[categoryKey] ?? "")),
		series: fields.slice(0, Math.min(maxSeries, COLORS.length)).map((field, i) => ({
			name: field,
			data: sortedRows.map((r) => (isNumeric(r[field]) ? r[field] : null)),
			color: COLORS[i],
			type: chartType,
		})),
		options: unit ? { unit } : {},
	});

	const hasData = $derived(spec.categories.length > 0 && spec.series.length > 0);
</script>

{#if hasData}
	<TrendChart {spec} />
{/if}
