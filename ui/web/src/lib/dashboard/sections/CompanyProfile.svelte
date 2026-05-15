<!--
	Company > Profile — Editorial 톤. 회사 메타 (sector/industry/stage) + 인력 분석.
	Hero: 섹터/단계/역할 · 신뢰도
	KPI: 직원수 / 평균급여 / 직원당매출 / 최고보수
	동향: 급여 vs 매출 성장률 괴리 (warning if gap > 5pp)
	다양성: 남녀격차
-->
<script>
	import { onMount, untrack } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { dlCall } from "$lib/api/dlCall.js";
	import { loadWorkforce } from "$lib/dashboard/data/loaders.js";
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let workforce = $state({ row: {} });
	let industry = $state(null);
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		try {
			const [w, i] = await Promise.all([
				loadWorkforce(dash.stockCode),
				dlCall("Company.industry", { target: dash.stockCode }).catch(() => null),
			]);
			if (w.ok) workforce = { row: w.data.rows[0] || {} };
			if (i) industry = i.data;
		} catch (e) {
			error = { message: e?.message || String(e) };
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		dash.stockCode;
		untrack(() => fetchAll());
	});

	onMount(() => fetchAll());

	const w = $derived(workforce.row || {});
	const empCount = $derived(w["직원수"]);
	const avgSalary = $derived(w["평균급여_만원"]); // 만원 단위
	const genderGap = $derived(w["남녀격차"]); // %
	const tenure = $derived(w["근속_년"]);
	const revPerEmp = $derived(w["직원당매출_억"]); // 억
	const salaryGrowth = $derived(w["급여성장률"]); // %
	const revGrowth = $derived(w["매출성장률"]); // %
	const divergence = $derived(w["급여매출괴리"]); // pp
	const topPay = $derived(w["최고보수_억"]); // 억
	const disclosedCount = $derived(w["공개인원"]);

	// 급여/매출 괴리: 급여 성장이 매출 성장보다 5pp 이상 높으면 경고
	const divergenceWarn = $derived(isFiniteNum(divergence) && divergence < -3);

	function fmtSalary(manwon) {
		if (!isFiniteNum(manwon)) return "—";
		if (manwon >= 10000) return (manwon / 10000).toFixed(2) + "억";
		return manwon.toLocaleString() + "만";
	}

	function fmtPct(v, digits = 1) {
		if (!isFiniteNum(v)) return "—";
		const sign = v > 0 ? "+" : "";
		return sign + v.toFixed(digits) + "%";
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Hero: 산업 분류 + 신뢰도 -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-3">
			<div class="ed-eyebrow">Industry Profile</div>
			{#if industry?.confidence !== undefined}
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					classification confidence {(industry.confidence * 100).toFixed(0)}% · source {industry.source || "—"}
				</div>
			{/if}
		</div>
		{#if loading}
			<div class="flex gap-6"><div class="editorial-skeleton h-12 w-32"></div><div class="editorial-skeleton h-12 w-40"></div></div>
		{:else if industry}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">산업</div>
					<div class="text-[18px] font-medium mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{industry.industryName || industry.industry || "—"}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">단계</div>
					<div class="text-[18px] font-medium mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{industry.stageName || industry.stage || "—"}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">역할</div>
					<div class="text-[14px] mt-1" style="color: var(--ed-text-2);">{industry.role || "—"}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">위치</div>
					<div class="text-[14px] mt-1" style="color: var(--ed-text-2);">{industry.stream || "—"}</div>
				</div>
			</div>
		{:else}
			<div class="text-[12px]" style="color: var(--ed-text-3);">산업 분류 데이터 없음</div>
		{/if}
	</div>

	<!-- Workforce KPI strip 4 -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
		<div class="ed-card">
			<div class="ed-eyebrow">직원 수</div>
			<div class="ed-num text-[28px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
				{isFiniteNum(empCount) ? empCount.toLocaleString() : "—"}<span class="text-[12px]" style="color: var(--ed-text-3);"> 명</span>
			</div>
		</div>
		<div class="ed-card">
			<div class="ed-eyebrow">평균 급여</div>
			<div class="ed-num text-[28px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
				{fmtSalary(avgSalary)}
			</div>
			<div class="text-[10px] mt-1" style="color: var(--ed-text-3);">연봉 (만원)</div>
		</div>
		<div class="ed-card">
			<div class="ed-eyebrow">직원당 매출</div>
			<div class="ed-num text-[28px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
				{isFiniteNum(revPerEmp) ? revPerEmp.toFixed(1) + "억" : "—"}
			</div>
		</div>
		<div class="ed-card">
			<div class="ed-eyebrow">최고 보수</div>
			<div class="ed-num text-[28px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
				{isFiniteNum(topPay) ? topPay.toFixed(1) + "억" : "—"}
			</div>
			<div class="text-[10px] mt-1" style="color: var(--ed-text-3);">공개 {disclosedCount ?? "—"}명</div>
		</div>
	</div>

	<!-- 급여 vs 매출 성장 괴리 -->
	{#if isFiniteNum(salaryGrowth) || isFiniteNum(revGrowth)}
		<div class="ed-card" style="border-color: {divergenceWarn ? 'var(--ed-down)' : 'var(--ed-line)'};">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow" style="color: {divergenceWarn ? 'var(--ed-down)' : 'var(--ed-text-3)'};">급여 vs 매출 성장률 괴리</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					gap {fmtPct(divergence)} {divergenceWarn ? "· 매출 대비 급여 성장 둔화" : "· 정상"}
				</div>
			</div>
			<div class="grid grid-cols-2 gap-6">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">급여 성장률</div>
					<div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(salaryGrowth) && salaryGrowth < 0 ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{fmtPct(salaryGrowth)}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">매출 성장률</div>
					<div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(revGrowth) && revGrowth > 0 ? 'var(--ed-up)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{fmtPct(revGrowth)}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- 다양성 + 근속 -->
	<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
		<div class="ed-card">
			<div class="ed-eyebrow mb-2">남녀 급여 격차</div>
			{#if isFiniteNum(genderGap)}
				<div class="flex items-baseline gap-3">
					<div class="ed-num text-[32px]" style="color: {genderGap > 30 ? 'var(--ed-down)' : genderGap > 15 ? 'var(--ed-text-2)' : 'var(--ed-up)'}; font-family: var(--font-display);">
						{genderGap.toFixed(1)}%
					</div>
					<div class="text-[11px]" style="color: var(--ed-text-3);">
						{genderGap > 30 ? "큰 격차 — 다양성 약" : genderGap > 15 ? "보통" : "균형"}
					</div>
				</div>
				<div class="mt-3 h-1.5 rounded-full overflow-hidden" style="background: var(--ed-line);">
					<div class="h-full rounded-full" style="width: {Math.min(100, genderGap * 2)}%; background: {genderGap > 30 ? 'var(--ed-down)' : 'var(--ed-text-2)'};"></div>
				</div>
			{:else}
				<div class="text-[12px]" style="color: var(--ed-text-3);">데이터 없음</div>
			{/if}
		</div>
		<div class="ed-card">
			<div class="ed-eyebrow mb-2">평균 근속</div>
			{#if isFiniteNum(tenure)}
				<div class="ed-num text-[32px]" style="color: var(--ed-text); font-family: var(--font-display);">
					{tenure.toFixed(1)}<span class="text-[14px]" style="color: var(--ed-text-3);"> 년</span>
				</div>
			{:else}
				<div class="text-[14px] mt-1" style="color: var(--ed-text-3);">데이터 미공시</div>
			{/if}
		</div>
	</div>

	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
		</div>
	{/if}
</div>
