<!--
	CompanySwitcher — Dashboard 사이드바의 회사 선택 dropdown.
	Phase 0 seed (16 KOSPI Top), Phase E 에서 dlCall("Company.listing") 로 교체.
-->
<script>
	import { ChevronsUpDown, Check, Search } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { cn } from "$lib/utils.js";

	const dash = getDashboardStore();

	// 16 KOSPI Top — Phase E 교체 대상
	const COMPANIES = [
		{ stockCode: "005930", corpName: "삼성전자", sector: "반도체" },
		{ stockCode: "000660", corpName: "SK하이닉스", sector: "반도체" },
		{ stockCode: "035420", corpName: "NAVER", sector: "인터넷" },
		{ stockCode: "035720", corpName: "카카오", sector: "인터넷" },
		{ stockCode: "207940", corpName: "삼성바이오로직스", sector: "바이오" },
		{ stockCode: "005380", corpName: "현대차", sector: "자동차" },
		{ stockCode: "051910", corpName: "LG화학", sector: "화학" },
		{ stockCode: "006400", corpName: "삼성SDI", sector: "2차전지" },
		{ stockCode: "068270", corpName: "셀트리온", sector: "바이오" },
		{ stockCode: "012330", corpName: "현대모비스", sector: "자동차부품" },
		{ stockCode: "028260", corpName: "삼성물산", sector: "종합" },
		{ stockCode: "066570", corpName: "LG전자", sector: "가전" },
		{ stockCode: "003550", corpName: "LG", sector: "지주" },
		{ stockCode: "017670", corpName: "SK텔레콤", sector: "통신" },
		{ stockCode: "030200", corpName: "KT", sector: "통신" },
		{ stockCode: "036570", corpName: "엔씨소프트", sector: "게임" },
	];

	let open = $state(false);
	let query = $state("");

	const filtered = $derived(
		query
			? COMPANIES.filter(
					(c) =>
						c.corpName.includes(query) ||
						c.stockCode.includes(query) ||
						c.sector.includes(query)
				)
			: COMPANIES
	);

	const current = $derived(
		COMPANIES.find((c) => c.stockCode === dash.stockCode) || COMPANIES[3]
	);

	function select(c) {
		dash.setStockCode(c.stockCode);
		open = false;
		query = "";
	}

	function handleClickOutside(e) {
		const root = e.target.closest('[data-company-switcher-root]');
		if (!root) open = false;
	}
</script>

<svelte:window onclick={handleClickOutside} />

<div class="relative" data-company-switcher-root>
	<button
		type="button"
		class="w-full inline-flex items-center justify-between gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-left text-[13px] text-foreground hover:bg-muted transition-colors"
		aria-expanded={open}
		onclick={() => (open = !open)}
	>
		<div class="min-w-0 flex-1">
			<div class="truncate font-medium">{current.corpName}</div>
			<div class="text-[10px] text-muted-foreground font-mono">
				{current.stockCode} · {current.sector}
			</div>
		</div>
		<ChevronsUpDown size={14} class="text-muted-foreground shrink-0" />
	</button>

	{#if open}
		<div
			class="absolute left-0 right-0 top-full mt-1 z-50 rounded-md border border-border bg-popover shadow-md"
		>
			<div class="flex items-center gap-2 border-b border-border px-2.5 py-1.5">
				<Search size={14} class="text-muted-foreground shrink-0" />
				<input
					type="text"
					bind:value={query}
					placeholder="회사명 · 종목코드 · 섹터"
					class="flex-1 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
				/>
			</div>
			<ul class="max-h-72 overflow-auto py-1">
				{#each filtered as c}
					<li>
						<button
							type="button"
							class={cn(
								"flex items-center gap-2 w-full px-2.5 py-1.5 text-left text-[13px] hover:bg-muted",
								dash.stockCode === c.stockCode && "bg-secondary"
							)}
							onclick={() => select(c)}
						>
							<span class="flex-1 truncate">{c.corpName}</span>
							<span class="text-[10px] text-muted-foreground font-mono">{c.stockCode}</span>
							{#if dash.stockCode === c.stockCode}
								<Check size={12} class="text-primary" />
							{/if}
						</button>
					</li>
				{/each}
				{#if filtered.length === 0}
					<li class="px-2.5 py-2 text-[12px] text-muted-foreground">결과 없음</li>
				{/if}
			</ul>
		</div>
	{/if}
</div>
