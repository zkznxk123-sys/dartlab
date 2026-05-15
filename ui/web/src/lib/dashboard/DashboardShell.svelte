<!--
	DashboardShell — Editorial Financial Terminal main wrapper.
	좌측 사이드바는 App.svelte 가 mount 하는 외부 Sidebar 담당.
	본 컴포넌트 = topbar(category/section/desc/stockCode) + main(section route) + toc rail.
-->
<script>
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { LayoutDashboard, Search } from "lucide-svelte";
	import CompanyProfile from "$lib/dashboard/sections/CompanyProfile.svelte";
	import CompanyGovernance from "$lib/dashboard/sections/CompanyGovernance.svelte";
	import CompanyFilings from "$lib/dashboard/sections/CompanyFilings.svelte";
	import AnalysisHub from "$lib/dashboard/sections/AnalysisHub.svelte";
	import QuantHub from "$lib/dashboard/sections/QuantHub.svelte";
	import CreditHub from "$lib/dashboard/sections/CreditHub.svelte";
	import MacroHub from "$lib/dashboard/sections/MacroHub.svelte";
	import IndustryHub from "$lib/dashboard/sections/IndustryHub.svelte";
	import StoryHub from "$lib/dashboard/sections/StoryHub.svelte";
	import AskFromDashboardButton from "$lib/dashboard/AskFromDashboardButton.svelte";

	const dash = getDashboardStore();

	const SECTIONS = {
		"company.profile": { label: "Profile", category: "Company", desc: "회사 메타 · 임원 · 시총 · 사업 description" },
		"company.governance": { label: "Governance", category: "Company", desc: "주주 · 임원 · 자사주 · 거버넌스 score" },
		"company.filings": { label: "Filings", category: "Company", desc: "DART 공시 timeline · 정기 · 수시" },
		analysis: { label: "Analysis", category: "Engine", desc: "재무 14 axes — 수익구조 · 수익성 · 현금흐름 · ..." },
		quant: { label: "Quant", category: "Engine", desc: "주가 · 시장 · 시계열 · 캔들 · 변동성 · forecast" },
		credit: { label: "Credit", category: "Engine", desc: "dCR · 7축 가중 · 부도위험 · metrics gauge" },
		macro: { label: "Macro", category: "Engine", desc: "거시 환경 — 금리 · 환율 · 사이클 · sentiment · scenario" },
		industry: { label: "Industry", category: "Engine", desc: "동종업계 · peer rank · 공급망 network" },
		story: { label: "Story", category: "Composed", desc: "perspective 별 6 막 narrative" },
		scan: { label: "Scan", category: "Discover", desc: "다중 종목 멀티 axis 스크리너" },
	};

	const current = $derived(SECTIONS[dash.section] || { label: dash.section, category: "", desc: "" });
</script>

<div class="editorial editorial-grain h-full flex flex-col min-h-0 relative">
	<header class="editorial-topbar">
		<div class="flex items-center gap-2 min-w-0">
			<LayoutDashboard size={14} class="shrink-0" style="color: var(--ed-text-3);" />
			<span class="ed-eyebrow whitespace-nowrap">{current.category}</span>
			<span class="text-[11px]" style="color: var(--ed-text-3);">/</span>
			<h2 class="ed-display text-[15px] font-semibold whitespace-nowrap" style="color: var(--ed-text);">
				{current.label}
			</h2>
		</div>
		<div class="flex-1 flex items-center gap-2 min-w-0 px-4">
			<div class="flex items-center gap-2 px-2.5 py-1 rounded border text-[11px] select-none w-full max-w-[420px]"
				style="border-color: var(--ed-line); color: var(--ed-text-3); background: var(--ed-surface);">
				<Search size={12} class="shrink-0" />
				<span class="truncate">{current.desc}</span>
			</div>
		</div>
		<div class="flex items-center gap-2 shrink-0">
			<div class="ed-num text-[11px]" style="color: var(--ed-text-3);">{dash.stockCode}</div>
			<AskFromDashboardButton />
		</div>
	</header>

	<div class="flex-1 min-h-0 flex">
		<main class="editorial-main editorial-stagger flex-1 min-w-0">
			{#if dash.section === "company.profile"}
				<CompanyProfile />
			{:else if dash.section === "company.governance"}
				<CompanyGovernance />
			{:else if dash.section === "company.filings"}
				<CompanyFilings />
			{:else if dash.section === "analysis"}
				<AnalysisHub />
			{:else if dash.section === "quant"}
				<QuantHub />
			{:else if dash.section === "credit"}
				<CreditHub />
			{:else if dash.section === "macro"}
				<MacroHub />
			{:else if dash.section === "industry"}
				<IndustryHub />
			{:else if dash.section === "story"}
				<StoryHub />
			{:else if dash.section === "scan"}
				<div class="ed-card">
					<div class="ed-eyebrow mb-2">Discover</div>
					<h2 class="mb-2">Scan — 다중 종목 스크리너</h2>
					<p style="color: var(--ed-text-2); font-size: 13px;">
						Phase G 에서 landing 의 scan workbench 를 복제 + dlCall scan.* 호출로 강화. (현재 placeholder)
					</p>
				</div>
			{:else}
				<div class="ed-card">
					<div class="ed-eyebrow mb-2">Unknown section</div>
					<p style="color: var(--ed-text-2);">section <span class="ed-num">{dash.section}</span> · stockCode <span class="ed-num">{dash.stockCode}</span></p>
				</div>
			{/if}
		</main>

		<aside class="editorial-toc hidden xl:block w-[180px] shrink-0">
			<div class="ed-eyebrow mb-3">On this page</div>
			<div class="text-[11px]" style="color: var(--ed-text-3);">
				본 section 의 anchor 목록은 Phase C~G 에서 자동 수집.
			</div>
		</aside>
	</div>
</div>
