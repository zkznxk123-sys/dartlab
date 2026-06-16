<script lang="ts">
	import type { RailSection, RailSectionKey } from '$lib/siteSignals/types';

	let {
		sections,
		active,
		onpick
	}: {
		sections: RailSection[];
		active: RailSectionKey;
		onpick: (key: RailSectionKey) => void;
	} = $props();
</script>

<nav class="signal-rail" aria-label="사이트 신호 목차">
	<div class="rail-group">
		<div class="rail-label">site signals</div>
		{#each sections as section (section.key)}
			<button
				type="button"
				class="rail-item"
				class:active={active === section.key}
				onclick={() => onpick(section.key)}
				title={section.label}
			>
				<span class="rail-kicker">{section.kicker}</span>
				<span class="rail-name">{section.label}</span>
			</button>
		{/each}
	</div>
</nav>

<style>
	.signal-rail {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.rail-label {
		padding: 5px 6px 3px;
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0;
		color: #64748b;
	}
	.rail-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.rail-item {
		display: grid;
		grid-template-columns: 68px minmax(0, 1fr);
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 6px 8px;
		border: 1px solid transparent;
		border-radius: 5px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		cursor: pointer;
		text-align: left;
	}
	.rail-item:hover {
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
	}
	.rail-item.active {
		background: rgba(251, 146, 60, 0.1);
		border-color: rgba(251, 146, 60, 0.5);
		color: #f8fafc;
	}
	.rail-kicker {
		color: #64748b;
		font-size: 10px;
		white-space: nowrap;
	}
	.rail-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 12px;
		font-weight: 600;
	}
</style>
