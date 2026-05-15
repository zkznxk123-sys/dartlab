<!--
	EngineNav — Dashboard 모드의 사이드바 nav.
	dartlab L1.5 Company + L2 5 engines + L3 Story 와 1:1 정렬.
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
	} from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { cn } from "$lib/utils.js";

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
			items: [{ key: "story", label: "Story", icon: BookOpen }],
		},
	];
</script>

<nav class="flex flex-col gap-3 py-1">
	{#each GROUPS as group}
		<div>
			<div class="px-3 mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
				{group.label}
			</div>
			<ul class="flex flex-col gap-0.5 px-2">
				{#each group.items as item}
					{@const Icon = item.icon}
					<li>
						<button
							type="button"
							class={cn(
								"flex items-center gap-2 w-full rounded px-2 py-1.5 text-left text-[13px] transition-colors",
								dash.section === item.key
									? "bg-secondary text-foreground"
									: "text-muted-foreground hover:bg-muted hover:text-foreground"
							)}
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
