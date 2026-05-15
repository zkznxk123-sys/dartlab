<!--
	Credit Hub — Company.credit (dCR 독립 신용등급, 7축 + 종합 등급).
	axes: grade (등급) · repayment · leverage · liquidity · cashflow ·
	      business · reliability · disclosure
-->
<script>
	import { Shield } from "lucide-svelte";
	import EngineHub from "$lib/dashboard/sections/EngineHub.svelte";

	const CORE_AXES = [
		"grade",
		"repayment",
		"leverage",
		"liquidity",
		"cashflow",
		"business",
		"reliability",
		"disclosure",
	];
</script>

<EngineHub
	apiRef="Company.credit"
	title="Credit — dCR 독립 신용등급 (7축)"
	icon={Shield}
	coreAxes={CORE_AXES}
	descLabel="채무상환·자본구조·유동성·현금흐름·사업안정성·재무신뢰성·공시리스크 + 종합 등급"
/>
