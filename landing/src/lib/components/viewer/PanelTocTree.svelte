<script lang="ts">
	// 목차 — chapter > sectionLeaf 트리. landing 디자인 언어(다크 네이비 + 오렌지 액센트).
	import type { PanelTocResponse } from '$lib/viewer/types';

	let {
		toc,
		activeSectionKey,
		onpick
	}: { toc: PanelTocResponse; activeSectionKey: string | undefined; onpick: (sectionKey: string) => void } = $props();
</script>

<nav class="toc-tree">
	{#each toc.chapters as ch (ch.chapter)}
		<div class="chapter">
			<div class="chapter-label">{ch.chapter}</div>
			<div class="sections">
				{#each ch.sections as sec (sec.sectionKey)}
					<button
						type="button"
						class="section"
						class:active={sec.sectionKey === activeSectionKey}
						onclick={() => onpick(sec.sectionKey)}
						title={sec.sectionLeaf}
					>
						<span class="section-name">{sec.sectionLeaf}</span>
					</button>
				{/each}
			</div>
		</div>
	{/each}
</nav>

<style>
	.toc-tree {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.chapter-label {
		padding: 5px 6px 3px;
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #64748b;
	}
	.sections {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.section {
		display: block;
		width: 100%;
		text-align: left;
		padding: 5px 8px;
		border: 1px solid transparent;
		border-radius: 5px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
		transition: background 0.12s, color 0.12s, border-color 0.12s;
	}
	.section:hover {
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
	}
	.section.active {
		background: rgba(251, 146, 60, 0.1);
		border-color: rgba(251, 146, 60, 0.5);
		color: #f8fafc;
		font-weight: 600;
	}
	.section-name {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
