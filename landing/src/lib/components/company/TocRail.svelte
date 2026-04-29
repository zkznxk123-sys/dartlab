<script lang="ts">
	let { activeSection, items }: { activeSection: string; items: Array<{ id: string; label: string }> } = $props();
</script>

<nav class="toc-rail" aria-label="Company 목차">
	<div class="track" aria-hidden="true"></div>
	<div class="toc-links">
		{#each items as item}
			<a class:active={activeSection === item.id} href="#{item.id}" aria-label={item.label}>
				<i></i>
			</a>
		{/each}
	</div>
	<div class="toc-panel" aria-hidden="true">
		{#each items as item}
			<div class:active={activeSection === item.id}>
				<span>{item.label}</span>
			</div>
		{/each}
	</div>
</nav>

<nav class="mobile-toc" aria-label="Company 모바일 목차">
	{#each items as item}
		<a class:active={activeSection === item.id} href="#{item.id}">{item.label}</a>
	{/each}
</nav>

<style>
	.toc-rail {
		position: fixed;
		top: 196px;
		right: 10px;
		z-index: 40;
		width: 26px;
		max-height: calc(100vh - 228px);
		padding: 10px 0;
		pointer-events: auto;
	}
	.track {
		position: absolute;
		top: 14px;
		right: 10px;
		bottom: 14px;
		width: 2px;
		border-radius: 999px;
		background: #1e2433;
	}
	.toc-links {
		position: relative;
		display: grid;
		gap: 4px;
	}
	.toc-links a {
		position: relative;
		display: grid;
		align-items: center;
		width: 26px;
		min-height: 24px;
		border-radius: 6px;
		color: #94a3b8;
		text-decoration: none;
		transition: background 0.15s ease, color 0.15s ease;
	}
	i {
		justify-self: end;
		width: 7px;
		height: 7px;
		border: 1px solid #64748b;
		border-radius: 999px;
		background: #050811;
		transition: width 0.15s ease, height 0.15s ease, background 0.15s ease, border-color 0.15s ease;
	}
	.toc-panel {
		position: absolute;
		top: 10px;
		right: 30px;
		display: grid;
		width: 194px;
		gap: 4px;
		opacity: 0;
		pointer-events: none;
		transform: translateX(6px);
		transition: opacity 0.14s ease, transform 0.14s ease;
	}
	.toc-panel div {
		display: flex;
		align-items: center;
		min-height: 24px;
		border: 1px solid rgba(30, 36, 51, 0.92);
		border-radius: 6px;
		background: rgba(5, 8, 17, 0.94);
		box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24);
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.2;
		padding: 0 10px;
		backdrop-filter: blur(14px);
	}
	.toc-panel span {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.toc-rail:hover .toc-panel,
	.toc-rail:focus-within .toc-panel {
		opacity: 1;
		transform: translateX(0);
	}
	.toc-links a.active {
		color: #f8fafc;
	}
	.toc-links a.active i {
		width: 8px;
		height: 22px;
		border-color: #fb923c;
		background: #fb923c;
	}
	.toc-links a:hover {
		background: rgba(7, 12, 21, 0.82);
		color: #f8fafc;
	}
	.toc-panel div.active {
		border-color: rgba(251, 146, 60, 0.5);
		color: #f8fafc;
	}
	.mobile-toc {
		display: none;
	}
	@media (max-width: 760px) {
		.toc-rail {
			display: none;
		}
		.mobile-toc {
			position: sticky;
			top: 56px;
			z-index: 32;
			display: flex;
			gap: 6px;
			overflow-x: auto;
			margin: 0 -12px 12px;
			border-bottom: 1px solid #1e2433;
			background: rgba(5, 8, 17, 0.95);
			padding: 8px 12px;
			backdrop-filter: blur(12px);
		}
		.mobile-toc a {
			flex: 0 0 auto;
			width: auto;
			min-height: auto;
			grid-template-columns: 1fr;
			border: 1px solid #263145;
			background: #070c15;
			color: #94a3b8;
			font-size: 12px;
			padding: 7px 10px;
		}
		.mobile-toc a.active {
			border-color: rgba(251, 146, 60, 0.65);
			color: #f8fafc;
		}
	}
</style>
