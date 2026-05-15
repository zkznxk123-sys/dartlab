<!--
	Analysis Hub — EngineHub wrapper for Company.analysis (financial 14 axes).
-->
<script>
	import { BarChart3 } from "lucide-svelte";
	import EngineHub from "$lib/dashboard/sections/EngineHub.svelte";

	const CORE_AXES = [
		"수익구조",
		"비용구조",
		"수익성",
		"성장성",
		"이익품질",
		"자산구조",
		"자금조달",
		"안정성",
		"효율성",
		"현금흐름",
		"자본배분",
		"투자효율",
		"종합평가",
		"재무정합성",
	];
</script>

<EngineHub
	apiRef="Company.analysis"
	title="Analysis — 재무 14 axes (financial)"
	icon={BarChart3}
	coreAxes={CORE_AXES}
	descLabel="손익·재무상태·현금흐름·비율의 의미 그룹별 분석"
/>
