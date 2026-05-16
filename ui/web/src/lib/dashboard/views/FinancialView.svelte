<script>
	import { untrack } from "svelte";
	import * as Tabs from "$lib/ui/tabs";
	import ChartCard from "../components/ChartCard.svelte";
	import DataTable from "../components/DataTable.svelte";
	import KpiCard from "../components/KpiCard.svelte";
	import { fetchView, refsFor } from "../data/financialFetcher.js";

	let { stockCode = "035720", mode = "annual" } = $props();

	const SECTIONS = ["is", "bs", "cf", "ratios"];

	let payloads = $state({ is: {}, bs: {}, cf: {}, ratios: {} });
	let loading = $state({ is: false, bs: false, cf: false, ratios: false });
	let error = $state({ is: null, bs: null, cf: null, ratios: null });
	let activeTab = $state("is");

	$effect(() => {
		const sc = stockCode;
		const md = mode;
		const sec = activeTab;
		if (!sc || !sec) return;

		untrack(() => {
			loading[sec] = true;
			error[sec] = null;
		});

		const controller = new AbortController();
		let canceled = false;

		fetchView(sec, sc, md, controller.signal)
			.then((res) => {
				if (canceled) return;
				payloads[sec] = res;
				loading[sec] = false;
			})
			.catch((e) => {
				if (canceled) return;
				error[sec] = e?.message || "데이터 로드 실패";
				loading[sec] = false;
			});

		return () => {
			canceled = true;
			controller.abort();
		};
	});

	function rowOf(data, key) {
		return data?.rows?.find?.((r) => r.key === key);
	}
	function lastVal(arr) {
		return arr && arr.length ? arr[arr.length - 1] : null;
	}

	const isKpis = $derived.by(() => {
		const ov = payloads.is?.isOverview;
		if (!ov?.data?.rows?.length) return [];
		const periods = ov.data.periods || [];
		const li = periods.length - 1;
		const pi = periods.length - 2;
		const rev = rowOf(ov.data, "revenue");
		const op = rowOf(ov.data, "operatingIncome");
		const ni = rowOf(ov.data, "netIncome");
		const opm = rowOf(ov.data, "operatingMargin");
		const yoy = (vs) =>
			!vs || vs[li] == null || vs[pi] == null || vs[pi] === 0 ? null : ((vs[li] - vs[pi]) / Math.abs(vs[pi])) * 100;
		return [
			{ label: "매출액", value: rev?.values?.[li], unit: rev?.unit, delta: yoy(rev?.values), deltaLabel: "YoY" },
			{ label: "영업이익", value: op?.values?.[li], unit: op?.unit, delta: yoy(op?.values), deltaLabel: "YoY" },
			{ label: "당기순이익", value: ni?.values?.[li], unit: ni?.unit, delta: yoy(ni?.values), deltaLabel: "YoY" },
			{ label: "영업이익률", value: opm?.values?.[li], unit: "%", delta: opm?.values?.[li] - opm?.values?.[pi], deltaLabel: "pp" },
		];
	});

	const bsKpis = $derived.by(() => {
		const ov = payloads.bs?.bsOverview;
		const lv = payloads.bs?.bsLeverage;
		if (!ov?.data?.rows?.length) return [];
		const li = (ov.data.periods || []).length - 1;
		return [
			{ label: "자산총계", value: rowOf(ov.data, "assets")?.values?.[li], unit: "원" },
			{ label: "부채총계", value: rowOf(ov.data, "liabilities")?.values?.[li], unit: "원" },
			{ label: "자본총계", value: rowOf(ov.data, "equity")?.values?.[li], unit: "원" },
			{ label: "유동비", value: lastVal(lv?.data?.currentRatio), unit: "%" },
		];
	});

	const cfKpis = $derived.by(() => {
		const ov = payloads.cf?.cfOverview;
		if (!ov?.data?.rows?.length) return [];
		const li = (ov.data.periods || []).length - 1;
		return [
			{ label: "영업CF", value: rowOf(ov.data, "cfOperating")?.values?.[li], unit: "원" },
			{ label: "투자CF", value: rowOf(ov.data, "cfInvesting")?.values?.[li], unit: "원" },
			{ label: "재무CF", value: rowOf(ov.data, "cfFinancing")?.values?.[li], unit: "원" },
			{ label: "FCF", value: rowOf(ov.data, "fcf")?.values?.[li], unit: "원" },
		];
	});

	const ratioKpis = $derived.by(() => {
		const p = payloads.ratios?.ratiosProfitability?.data;
		const s = payloads.ratios?.ratiosStability?.data;
		return [
			{ label: "ROE", value: lastVal(p?.roe), unit: "%" },
			{ label: "ROA", value: lastVal(p?.roa), unit: "%" },
			{ label: "부채비", value: lastVal(s?.debtRatio), unit: "%" },
			{ label: "유동비", value: lastVal(s?.currentRatio), unit: "%" },
		];
	});
</script>

<Tabs.Root bind:value={activeTab} class="w-full">
	<Tabs.List>
		<Tabs.Trigger value="is">손익계산서</Tabs.Trigger>
		<Tabs.Trigger value="bs">재무상태표</Tabs.Trigger>
		<Tabs.Trigger value="cf">현금흐름표</Tabs.Trigger>
		<Tabs.Trigger value="ratios">재무비율</Tabs.Trigger>
	</Tabs.List>

	<Tabs.Content value="is" class="space-y-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			{#each isKpis as k}<KpiCard {...k} />{/each}
		</div>
		<DataTable title="손익계산서 총괄" payload={payloads.is?.isOverview} loading={loading.is} error={error.is} />
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
			<ChartCard title="매출 추세" subtitle="YoY overlay" payload={payloads.is?.isRevenueTrend} loading={loading.is} />
			<ChartCard title="이익률 추세" subtitle="GPM · OPM · NPM" payload={payloads.is?.isMarginTrend} loading={loading.is} />
		</div>
		<ChartCard title="비용 구조" subtitle="매출원가 · 판관비 · R&D · 금융비용" payload={payloads.is?.isCostStructure} loading={loading.is} />
	</Tabs.Content>

	<Tabs.Content value="bs" class="space-y-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			{#each bsKpis as k}<KpiCard {...k} />{/each}
		</div>
		<DataTable title="재무상태표 총괄" payload={payloads.bs?.bsOverview} loading={loading.bs} error={error.bs} />
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
			<ChartCard title="재무 구성" subtitle="자산 / 부채+자본" payload={payloads.bs?.bsComposition} loading={loading.bs} height={340} />
			<ChartCard title="레버리지 추세" subtitle="D/E · D/A · 유동비" payload={payloads.bs?.bsLeverage} loading={loading.bs} />
		</div>
	</Tabs.Content>

	<Tabs.Content value="cf" class="space-y-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			{#each cfKpis as k}<KpiCard {...k} />{/each}
		</div>
		<DataTable title="현금흐름표 총괄" payload={payloads.cf?.cfOverview} loading={loading.cf} error={error.cf} />
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
			<ChartCard title="현금흐름 waterfall" subtitle="기초 → 영업+투자+재무 → 기말" payload={payloads.cf?.cfWaterfall} loading={loading.cf} />
			<ChartCard title="잉여현금흐름" subtitle="영업CF − CapEx" payload={payloads.cf?.cfFreeCashFlow} loading={loading.cf} />
		</div>
	</Tabs.Content>

	<Tabs.Content value="ratios" class="space-y-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			{#each ratioKpis as k}<KpiCard {...k} />{/each}
		</div>
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
			<ChartCard title="수익성" subtitle="ROE · ROA · GPM · OPM · NPM" payload={payloads.ratios?.ratiosProfitability} loading={loading.ratios} error={error.ratios} />
			<ChartCard title="안정성" subtitle="유동비 · 당좌비 · 부채비 · 자기자본비" payload={payloads.ratios?.ratiosStability} loading={loading.ratios} />
			<ChartCard title="효율성" subtitle="자산회전 · DSO · DIO" payload={payloads.ratios?.ratiosEfficiency} loading={loading.ratios} />
			<ChartCard title="성장성" subtitle="매출 · 영업이익 · 순이익 YoY" payload={payloads.ratios?.ratiosGrowth} loading={loading.ratios} />
		</div>
	</Tabs.Content>
</Tabs.Root>
