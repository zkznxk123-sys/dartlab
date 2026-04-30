<script lang="ts">
	let { activeSection, items }: { activeSection: string; items: Array<{ id: string; label: string }> } = $props();
</script>

<nav class="toc-rail" aria-label="Company 목차">
	<div class="track" aria-hidden="true"></div>
	<div class="toc-links">
		{#each items as item, i}
			<a
				class:active={activeSection === item.id}
				href="#{item.id}"
				aria-label={item.label}
				style:top={`${(i / Math.max(1, items.length - 1)) * 100}%`}
			>
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
		top: 170px;
		right: 12px;
		z-index: 40;
		width: 18px;
		height: min(420px, calc(100vh - 220px));
		pointer-events: auto;
	}
	.track {
		position: absolute;
		top: 0;
		right: 6px;
		bottom: 0;
		width: 1px;
		border-radius: 999px;
		background: #1e2433;
	}
	.toc-links {
		position: absolute;
		inset: 0;
	}
	.toc-links a {
		position: absolute;
		right: 0;
		display: block;
		width: 18px;
		height: 24px;
		color: #94a3b8;
		text-decoration: none;
		transform: translateY(-50%);
	}
	i {
		position: absolute;
		top: 50%;
		right: 3px;
		width: 7px;
		height: 1px;
		border-radius: 999px;
		background: #334155;
		transform: translateY(-50%);
		transition: width 0.15s ease, height 0.15s ease, background 0.15s ease;
	}
	.toc-panel {
		position: absolute;
		top: -8px;
		right: 22px;
		display: grid;
		width: 220px;
		gap: 3px;
		border: 1px solid rgba(30, 36, 51, 0.92);
		border-radius: 7px;
		background: rgba(5, 8, 17, 0.96);
		padding: 6px;
		opacity: 0;
		pointer-events: none;
		transform: translateX(6px);
		transition: opacity 0.14s ease, transform 0.14s ease;
		backdrop-filter: blur(14px);
		box-shadow: 0 18px 42px rgba(0, 0, 0, 0.3);
	}
	.toc-panel div {
		display: flex;
		align-items: center;
		min-height: 25px;
		border-radius: 5px;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.2;
		padding: 0 8px;
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
		right: 0;
		width: 13px;
		height: 22px;
		background: #fb923c;
	}
	.toc-panel div.active {
		background: #0d1422;
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
