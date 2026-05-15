<!--
	EngineNav — Dashboard 사이드바 nav.
	Editorial 톤. dartlab L1.5 Company + L2 5 engines + L1.5 scan + L3 Story.
-->
<script>
	import {
		Building2,
		BarChart3,
		TrendingUp,
		Shield,
		Globe,
		Factory,
		BookOpen,
		Users,
		FileText,
		Filter,
	} from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";

	const dash = getDashboardStore();

	const GROUPS = [
		{
			label: "Company",
			items: [
				{ key: "company.profile", label: "Profile", icon: Building2 },
				{ key: "company.governance", label: "Governance", icon: Users },
				{ key: "company.filings", label: "Filings", icon: FileText },
			],
		},
		{
			label: "Engines",
			items: [
				{ key: "analysis", label: "Analysis", icon: BarChart3 },
				{ key: "quant", label: "Quant", icon: TrendingUp },
				{ key: "credit", label: "Credit", icon: Shield },
				{ key: "macro", label: "Macro", icon: Globe },
				{ key: "industry", label: "Industry", icon: Factory },
			],
		},
		{
			label: "Composed",
			items: [
				{ key: "story", label: "Story", icon: BookOpen },
			],
		},
		{
			label: "Discover",
			items: [
				{ key: "scan", label: "Scan", icon: Filter },
			],
		},
	];
</script>

<nav class="flex flex-col gap-1 py-2">
	{#each GROUPS as group}
		<div class="editorial-nav-group">
			<div class="editorial-nav-group-label">{group.label}</div>
			<ul class="flex flex-col gap-px">
				{#each group.items as item}
					{@const Icon = item.icon}
					<li>
						<button
							type="button"
							class="editorial-nav-item"
							class:active={dash.section === item.key}
							aria-current={dash.section === item.key ? "page" : undefined}
							onclick={() => dash.setSection(item.key)}
						>
							<Icon size={14} class="shrink-0" />
							<span class="flex-1 truncate">{item.label}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{/each}
</nav>
