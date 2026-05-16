<!--
	DashboardShell — shadcn 토큰 기반. FinancialView (내부 4 탭) 단일 진입.
	좌측 Sidebar = 재무제표 1 항목.
-->
<script>
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import FinancialView from "$lib/dashboard/views/FinancialView.svelte";
	import CompanySwitcher from "$lib/dashboard/CompanySwitcher.svelte";
	import ModeToggle from "$lib/dashboard/ModeToggle.svelte";
	import LoadingBar from "$lib/dashboard/LoadingBar.svelte";
	import AskFromDashboardButton from "$lib/dashboard/AskFromDashboardButton.svelte";
	import PeriodToggle from "$lib/dashboard/PeriodToggle.svelte";

	const dash = getDashboardStore();
	// prefetchCompany 는 FinancialView 의 첫 fetch 가 자동 캐시 안착 — 별도 effect 불필요.
</script>

<div class="h-full flex flex-col min-h-0 relative bg-background text-foreground">
	<LoadingBar />
	<header class="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-card">
		<h2 class="text-base font-semibold tracking-tight">재무제표</h2>
		<div class="flex-1"></div>
		<PeriodToggle />
		<CompanySwitcher />
		<ModeToggle />
		<AskFromDashboardButton />
	</header>

	<main class="flex-1 min-h-0 overflow-auto p-4">
		<FinancialView stockCode={dash.stockCode} mode={dash.mode} />
	</main>
</div>
