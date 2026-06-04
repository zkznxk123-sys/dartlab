<script lang="ts">
	// 목차 — chapter > sectionLeaf > blockLeaf 트리. ui/web PanelTocTree 이식.
	import type { PanelTocResponse } from '$lib/viewer/types';

	let {
		toc,
		activeSectionKey,
		onpick
	}: { toc: PanelTocResponse; activeSectionKey: string | undefined; onpick: (sectionKey: string) => void } = $props();
</script>

<nav class="space-y-2">
	{#each toc.chapters as ch (ch.chapter)}
		<div>
			<div class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{ch.chapter}</div>
			<div class="space-y-0.5">
				{#each ch.sections as sec (sec.sectionKey)}
					<button
						type="button"
						onclick={() => onpick(sec.sectionKey)}
						class="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors {sec.sectionKey ===
						activeSectionKey
							? 'bg-accent text-accent-foreground'
							: 'text-muted-foreground hover:bg-accent/50'}"
					>
						<span class="truncate">{sec.sectionLeaf}</span>
					</button>
				{/each}
			</div>
		</div>
	{/each}
</nav>
