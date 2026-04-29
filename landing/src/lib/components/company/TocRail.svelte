<script lang="ts">
	let { activeSection, items }: { activeSection: string; items: Array<{ id: string; label: string }> } = $props();
</script>

<nav class="toc" aria-label="Company 목차">
	<div class="toc-title">TOC</div>
	{#each items as item}
		<a class:active={activeSection === item.id} href="#{item.id}">{item.label}</a>
	{/each}
</nav>

<style>
	.toc {
		position: fixed;
		top: 118px;
		right: 0;
		z-index: 20;
		display: grid;
		gap: 2px;
		width: 42px;
		overflow: hidden;
		border: 1px solid #1e2433;
		border-right: 0;
		border-radius: 8px 0 0 8px;
		background: rgba(5, 8, 17, 0.88);
		padding: 8px 6px;
		transition: width 0.16s ease;
		backdrop-filter: blur(10px);
	}
	.toc:hover,
	.toc:focus-within {
		width: 154px;
	}
	.toc-title {
		color: #fb923c;
		font-size: 10px;
		font-weight: 800;
		text-align: center;
	}
	a {
		display: block;
		overflow: hidden;
		border-radius: 5px;
		color: #94a3b8;
		font-size: 12px;
		padding: 6px 8px;
		text-decoration: none;
		white-space: nowrap;
	}
	a.active,
	a:hover {
		background: rgba(234, 70, 71, 0.14);
		color: #f8fafc;
	}
	@media (max-width: 760px) {
		.toc {
			display: none;
		}
	}
</style>
