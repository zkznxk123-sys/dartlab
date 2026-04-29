<script lang="ts">
	let { activeSection, items }: { activeSection: string; items: Array<{ id: string; label: string }> } = $props();
</script>

<nav class="toc-rail" aria-label="Company 목차">
	<div class="rail-mark" aria-hidden="true">목차</div>
	<div class="links">
		{#each items as item}
			<a class:active={activeSection === item.id} href="#{item.id}">
				<i></i>
				<span>{item.label}</span>
			</a>
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
		top: 218px;
		right: 0;
		z-index: 40;
		width: 40px;
		max-height: calc(100vh - 238px);
		overflow: hidden;
		border: 1px solid #1e2433;
		border-right: 0;
		border-radius: 8px 0 0 8px;
		background: rgba(5, 8, 17, 0.88);
		padding: 8px 6px;
		backdrop-filter: blur(14px);
		transition: width 0.16s ease, background 0.16s ease;
	}
	.toc-rail:hover,
	.toc-rail:focus-within {
		width: 220px;
		background: rgba(5, 8, 17, 0.97);
	}
	.rail-mark {
		overflow: hidden;
		color: #fb923c;
		font-size: 10px;
		font-weight: 900;
		text-align: center;
		white-space: nowrap;
	}
	.links {
		display: grid;
		gap: 2px;
		margin-top: 8px;
	}
	a {
		display: grid;
		grid-template-columns: 14px minmax(0, 1fr);
		gap: 8px;
		align-items: center;
		min-width: 204px;
		border-radius: 5px;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.25;
		padding: 7px 8px;
		text-decoration: none;
	}
	i {
		width: 4px;
		height: 18px;
		border-radius: 999px;
		background: #263145;
	}
	a.active,
	a:hover {
		background: rgba(251, 146, 60, 0.11);
		color: #f8fafc;
	}
	a.active i {
		background: #fb923c;
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
			min-width: auto;
			grid-template-columns: 1fr;
			border: 1px solid #263145;
			background: #070c15;
			padding: 7px 10px;
		}
	}
</style>
