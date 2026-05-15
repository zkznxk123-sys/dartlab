<!--
	DashboardShell — shadcn 토큰 기반. 4 탭 (IS/BS/CF/Ratios) FinancialView 단일 진입.
	좌측 사이드바는 App.svelte 가 mount 하는 외부 Sidebar 가 4 탭 navigation 담당.
-->
<script>
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import FinancialView from "$lib/dashboard/views/FinancialView.svelte";
	import CompanySwitcher from "$lib/dashboard/CompanySwitcher.svelte";
	import ModeToggle from "$lib/dashboard/ModeToggle.svelte";
	import LoadingBar from "$lib/dashboard/LoadingBar.svelte";
	import AskFromDashboardButton from "$lib/dashboard/AskFromDashboardButton.svelte";
	import PeriodToggle from "$lib/dashboard/PeriodToggle.svelte";
	import { prefetchCompany } from "$lib/dashboard/data/financialFetcher.js";

	const dash = getDashboardStore();

	const SECTIONS = {
		is: { label: "손익계산서", desc: "매출·이익률·비용 구조" },
		bs: { label: "재무상태표", desc: "자산·부채·자본·레버리지" },
		cf: { label: "현금흐름표", desc: "영업·투자·재무·잉여현금흐름" },
		ratios: { label: "재무비율", desc: "수익성·안정성·효율성·성장성" },
	};

	const current = $derived(SECTIONS[dash.section] || SECTIONS.is);

	$effect(() => {
		const sc = dash.stockCode;
		if (!sc) return;
		prefetchCompany(sc).catch(() => {});
	});
</script>

<div class="h-full flex flex-col min-h-0 relative bg-background text-foreground">
	<LoadingBar />
	<header class="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-card">
		<div class="flex items-baseline gap-2 min-w-0">
			<h2 class="text-base font-semibold tracking-tight">{current.label}</h2>
			<span class="text-[11px] text-muted-foreground truncate">{current.desc}</span>
		</div>
		<div class="flex-1"></div>
		<PeriodToggle />
		<CompanySwitcher />
		<ModeToggle />
		<AskFromDashboardButton />
	</header>

	<main class="flex-1 min-h-0 overflow-auto p-4 flex flex-col gap-3">
		<FinancialView section={dash.section} stockCode={dash.stockCode} mode={dash.mode} />
	</main>
</div>
