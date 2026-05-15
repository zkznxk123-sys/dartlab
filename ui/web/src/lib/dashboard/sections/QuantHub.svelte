<!--
	Quant Hub — Company.quant 48 axes 중 핵심 8 axis (기술적 + 팩터).
-->
<script>
	import { TrendingUp } from "lucide-svelte";
	import EngineHub from "$lib/dashboard/sections/EngineHub.svelte";

	// dartlab quant axes (48 중 dashboard 핵심 8): 기술적 5 + 팩터 3
	const CORE_AXES = [
		"indicators", // 45 기술적 지표 DataFrame
		"signals", // 매매 신호 이벤트
		"verdict", // 종합 기술적 판단
		"momentum", // 12-1 모멘텀 + 52w 신고가
		"volatility", // GARCH(1,1) HAR-RV
		"Z스코어", // Altman Z
		"F스코어", // Piotroski F
		"M스코어", // Beneish M
	];
</script>

<EngineHub
	apiRef="Company.quant"
	title="Quant — 기술적 지표 · 팩터 · 모멘텀"
	icon={TrendingUp}
	coreAxes={CORE_AXES}
	descLabel="주가 · 거래 · 변동성 · 팩터 신호 (Company.quant 48 axes 중 핵심 8)"
/>
