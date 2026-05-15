<!--
	DashboardShell — Dashboard 모드의 메인 영역.
	dashboardStore.section 으로 라우팅. Phase 0 은 placeholder, Phase 1~7 에서
	각 section 의 실 컨텐츠 mount.
-->
<script>
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { LayoutDashboard, AlertCircle } from "lucide-svelte";
	import * as Card from "$lib/ui/card";
	import CompanyProfile from "$lib/dashboard/sections/CompanyProfile.svelte";
	import CompanyGovernance from "$lib/dashboard/sections/CompanyGovernance.svelte";
	import CompanyFilings from "$lib/dashboard/sections/CompanyFilings.svelte";
	import AnalysisHub from "$lib/dashboard/sections/AnalysisHub.svelte";
	import QuantHub from "$lib/dashboard/sections/QuantHub.svelte";
	import CreditHub from "$lib/dashboard/sections/CreditHub.svelte";
	import MacroHub from "$lib/dashboard/sections/MacroHub.svelte";
	import IndustryHub from "$lib/dashboard/sections/IndustryHub.svelte";
	import StoryHub from "$lib/dashboard/sections/StoryHub.svelte";

	const dash = getDashboardStore();

	const SECTION_LABELS = {
		"company.profile": {
			label: "Company · Profile",
			desc: "회사 메타 (CEO · 섹터 · 직원수 · 시총)",
		},
		"company.governance": {
			label: "Company · Governance",
			desc: "주요주주 · 임원 · 자사주 · 임직원",
		},
		"company.filings": {
			label: "Company · Filings",
			desc: "DART 공시 (정기 · 수시)",
		},
		analysis: {
			label: "Analysis",
			desc: "재무 22 axes — 수익구조 · 자금조달 · 자산구조 · 수익성 · 성장성 · 안정성 · 효율성 · ...",
		},
		quant: {
			label: "Quant",
			desc: "주가 · 시장 시계열 · 밸류에이션 · 캔들 · OHLCV",
		},
		credit: {
			label: "Credit",
			desc: "신용등급 · 부도위험 · Altman-Z",
		},
		macro: {
			label: "Macro",
			desc: "거시 환경 — 금리 · 환율 · 자산군 · 사이클 · sentiment · scenario",
		},
		industry: {
			label: "Industry",
			desc: "동종업계 비교 · peer 분포 · 공급망 network",
		},
		story: {
			label: "Story",
			desc: "관점별 묶음 — 투자 · 신용 · M&A · ESG · 거시충격",
		},
	};

	const current = $derived(SECTION_LABELS[dash.section] || { label: dash.section, desc: "" });
</script>

<div class="flex flex-col h-full min-h-0 bg-background">
	<header class="border-b border-border px-6 py-3 flex items-center justify-between">
		<div class="min-w-0">
			<h1 class="text-[16px] font-semibold text-foreground truncate">{current.label}</h1>
			<p class="text-[11px] text-muted-foreground mt-0.5 truncate">{current.desc}</p>
		</div>
		<div class="text-[11px] text-muted-foreground font-mono shrink-0">
			{dash.stockCode}
		</div>
	</header>

	<main class="flex-1 overflow-auto p-6">
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
		{:else}
			<Card.Root class="border-dashed">
				<Card.Header>
					<Card.Title class="flex items-center gap-2 text-[14px]">
						<LayoutDashboard size={16} />
						<span>{current.label}</span>
					</Card.Title>
					<Card.Description class="text-[12px]">
						본 섹션의 컨텐츠는 후속 Phase 에서 직조 (Phase 2~7).
					</Card.Description>
				</Card.Header>
				<Card.Content>
					<div class="flex items-start gap-2 rounded-md bg-muted/40 p-3 text-[12px] text-muted-foreground">
						<AlertCircle size={14} class="shrink-0 mt-0.5" />
						<div class="min-w-0">
							<div class="font-medium text-foreground mb-0.5">{current.label}</div>
							<div>{current.desc}</div>
							<div class="mt-2 font-mono text-[10px] text-muted-foreground">
								section <span class="text-primary">{dash.section}</span> ·
								stockCode <span class="text-primary">{dash.stockCode}</span> ·
								period <span class="text-primary">{dash.period}</span>
							</div>
						</div>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}
	</main>
</div>
