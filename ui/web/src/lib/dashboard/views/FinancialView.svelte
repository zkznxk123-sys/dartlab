<script>
	import ChartCard from "../components/ChartCard.svelte";
	import DataTable from "../components/DataTable.svelte";
	import KpiCard from "../components/KpiCard.svelte";
	import { fetchView, refsFor } from "../data/financialFetcher.js";

	let { section = "is", stockCode = "035720", mode = "annual" } = $props();

	let payloads = $state({});
	let loading = $state(false);
	let error = $state(null);

	$effect(() => {
		const sc = stockCode;
		const sec = section;
		const md = mode;
		const refs = refsFor(sec);
		const initial = {};
		refs.forEach((n) => (initial[n] = null));
		payloads = initial;
		loading = true;
		error = null;
		let aborted = false;
		const controller = new AbortController();
		fetchView(sec, sc, md, controller.signal)
			.then((res) => {
				if (aborted) return;
				payloads = res;
				loading = false;
			})
			.catch((e) => {
				if (aborted) return;
				error = e?.message || "데이터 로드 실패";
				loading = false;
			});
		return () => {
			aborted = true;
			controller.abort();
		};
	});

	const kpis = $derived.by(() => {
		if (section !== "is") return [];
		const ov = payloads.isOverview;
		if (!ov?.data?.rows?.length) return [];
		const periods = ov.data.periods || [];
		const last = periods.length - 1;
		const prev = periods.length - 2;
		const rev = ov.data.rows.find((r) => r.key === "revenue");
		const op = ov.data.rows.find((r) => r.key === "operatingIncome");
		const ni = ov.data.rows.find((r) => r.key === "netIncome");
		const opm = ov.data.rows.find((r) => r.key === "operatingMargin");
		function yoy(values) {
			if (!values || values[last] == null || values[prev] == null || values[prev] === 0) return null;
			return ((values[last] - values[prev]) / Math.abs(values[prev])) * 100;
		}
		return [
			{ label: "매출액", value: rev?.values?.[last], unit: rev?.unit, delta: yoy(rev?.values), deltaLabel: "YoY" },
			{ label: "영업이익", value: op?.values?.[last], unit: op?.unit, delta: yoy(op?.values), deltaLabel: "YoY" },
			{ label: "당기순이익", value: ni?.values?.[last], unit: ni?.unit, delta: yoy(ni?.values), deltaLabel: "YoY" },
			{ label: "영업이익률", value: opm?.values?.[last], unit: "%", delta: opm?.values?.[last] - opm?.values?.[prev], deltaLabel: "pp" },
		];
	});

	const bsKpis = $derived.by(() => {
		if (section !== "bs") return [];
		const ov = payloads.bsOverview;
		const lv = payloads.bsLeverage;
		if (!ov?.data?.rows?.length) return [];
		const periods = ov.data.periods || [];
		const last = periods.length - 1;
		const rowOf = (k) => ov.data.rows.find((r) => r.key === k);
		const a = rowOf("assets")?.values?.[last];
		const l = rowOf("liabilities")?.values?.[last];
		const eq = rowOf("equity")?.values?.[last];
		const cash = rowOf("cash")?.values?.[last];
		return [
			{ label: "자산총계", value: a, unit: "원" },
			{ label: "부채총계", value: l, unit: "원" },
			{ label: "자본총계", value: eq, unit: "원" },
			{ label: "유동비", value: lv?.data?.currentRatio?.[lv?.data?.currentRatio?.length - 1], unit: "%" },
		];
	});

	const cfKpis = $derived.by(() => {
		if (section !== "cf") return [];
		const ov = payloads.cfOverview;
		if (!ov?.data?.rows?.length) return [];
		const periods = ov.data.periods || [];
		const last = periods.length - 1;
		const rowOf = (k) => ov.data.rows.find((r) => r.key === k);
		return [
			{ label: "영업CF", value: rowOf("cfOperating")?.values?.[last], unit: "원" },
			{ label: "투자CF", value: rowOf("cfInvesting")?.values?.[last], unit: "원" },
			{ label: "재무CF", value: rowOf("cfFinancing")?.values?.[last], unit: "원" },
			{ label: "잉여현금흐름", value: rowOf("fcf")?.values?.[last], unit: "원" },
		];
	});

	const ratioKpis = $derived.by(() => {
		if (section !== "ratios") return [];
		const p = payloads.ratiosProfitability?.data;
		const s = payloads.ratiosStability?.data;
		const last = (arr) => (arr && arr.length ? arr[arr.length - 1] : null);
		return [
			{ label: "ROE", value: last(p?.roe), unit: "%" },
			{ label: "ROA", value: last(p?.roa), unit: "%" },
			{ label: "부채비", value: last(s?.debtRatio), unit: "%" },
			{ label: "유동비", value: last(s?.currentRatio), unit: "%" },
		];
	});

	const visibleKpis = $derived(section === "is" ? kpis : section === "bs" ? bsKpis : section === "cf" ? cfKpis : ratioKpis);
</script>

{#if error}
	<div class="text-sm text-destructive p-4">{error}</div>
{/if}

<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
	{#each visibleKpis as k}
		<KpiCard label={k.label} value={k.value} unit={k.unit} delta={k.delta} deltaLabel={k.deltaLabel} />
	{/each}
</div>

{#if section === "is"}
	<div class="grid grid-cols-1 gap-3">
		<DataTable title="손익계산서 총괄" subtitle={mode === "annual" ? "연간" : "분기 누적"} payload={payloads.isOverview} {loading} />
	</div>
	<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
		<ChartCard title="매출 추세" subtitle="YoY 성장률 overlay" payload={payloads.isRevenueTrend} {loading} />
		<ChartCard title="이익률 추세" subtitle="GPM · OPM · NPM" payload={payloads.isMarginTrend} {loading} />
	</div>
	<div class="grid grid-cols-1 gap-3">
		<ChartCard title="비용 구조" subtitle="매출원가 · 판관비 · R&D · 금융비용 (stacked)" payload={payloads.isCostStructure} {loading} />
	</div>
{:else if section === "bs"}
	<div class="grid grid-cols-1 gap-3">
		<DataTable title="재무상태표 총괄" payload={payloads.bsOverview} {loading} />
	</div>
	<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
		<ChartCard title="재무 구성" subtitle="자산 / 부채+자본" payload={payloads.bsComposition} {loading} height={340} />
		<ChartCard title="레버리지 추세" subtitle="D/E · D/A · 유동비" payload={payloads.bsLeverage} {loading} />
	</div>
{:else if section === "cf"}
	<div class="grid grid-cols-1 gap-3">
		<DataTable title="현금흐름표 총괄" payload={payloads.cfOverview} {loading} />
	</div>
	<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
		<ChartCard title="현금흐름 waterfall" subtitle="기초 → 영업+투자+재무 → 기말" payload={payloads.cfWaterfall} {loading} />
		<ChartCard title="잉여현금흐름" subtitle="영업CF − CapEx + CF/매출" payload={payloads.cfFreeCashFlow} {loading} />
	</div>
{:else if section === "ratios"}
	<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
		<ChartCard title="수익성 비율" subtitle="ROE · ROA · GPM · OPM · NPM" payload={payloads.ratiosProfitability} {loading} />
		<ChartCard title="안정성 비율" subtitle="유동비 · 당좌비 · 부채비 · 자기자본비" payload={payloads.ratiosStability} {loading} />
	</div>
	<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
		<ChartCard title="효율성 비율" subtitle="자산회전 · 재고회전 · DSO · DIO" payload={payloads.ratiosEfficiency} {loading} />
		<ChartCard title="성장성 비율" subtitle="매출 · 영업이익 · 순이익 YoY" payload={payloads.ratiosGrowth} {loading} />
	</div>
{/if}
