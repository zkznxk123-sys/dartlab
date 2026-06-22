<script lang="ts">
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import Footer from '$lib/components/sections/Footer.svelte';
	import { categoryDefinitions, getCategoryPath } from '$lib/blog/posts';

	let { children } = $props();

	let currentPath = $derived(page.url.pathname.replace(base, ''));
	let currentCategory = $derived(page.data.currentCategory);
</script>

<div class="dl-blog">
	<Header context="blog" />

	<div class="dl-blog-body">
		<aside class="dl-blog-sidebar">
			<div class="dl-blog-sidebar-inner">
				<nav class="dl-blog-category-nav">
					<span class="dl-blog-nav-label">Categories</span>
					<a href="{base}/blog/" class="dl-blog-category-link" class:active={currentPath === '/blog' || currentPath === '/blog/'}>
						All Posts
					</a>
					{#each categoryDefinitions.filter((c) => !('hidden' in c) || !c.hidden) as category}
						<a
							href="{base}{getCategoryPath(category.id)}"
							class="dl-blog-category-link"
							class:active={currentCategory === category.id || currentPath === getCategoryPath(category.id) || currentPath.startsWith(`${getCategoryPath(category.id)}/`)}
						>
							{category.label}
						</a>
					{/each}
				</nav>
			</div>
		</aside>

		<main class="dl-blog-main">
			{@render children()}
		</main>
	</div>

	<Footer />
</div>

<style>
	:global(body) {
		margin: 0;
		background: var(--dl-mkt-bg);
		color: var(--dl-ink-print);
	}

	.dl-blog {
		min-height: 100vh;
		--shell-max-width: 1400px;
		--sidebar-width: 220px;
		--page-gutter: 1.5rem;
		--rail-gap: 2rem;
		padding-top: 48px;
	}

	.dl-blog-body {
		max-width: var(--shell-max-width);
		margin: 0 auto;
		display: grid;
		grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
		gap: var(--rail-gap);
		padding: 1.5rem var(--page-gutter) 6rem;
	}

	.dl-blog-sidebar {
		display: block;
		align-self: stretch;
		height: 100%;
	}

	.dl-blog-sidebar-inner {
		position: sticky;
		top: 64px;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.25rem 0;
	}

	.dl-blog-nav-label {
		display: block;
		font-size: 0.6875rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--dl-ink-dim);
		padding: 0.375rem 0.5rem;
	}

	.dl-blog-category-nav {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.dl-blog-category-link {
		display: flex;
		align-items: center;
		padding: 0.375rem 0.625rem;
		font-size: 0.8125rem;
		color: var(--dl-ink-mute);
		text-decoration: none;
		border-radius: 6px;
		transition: color 0.12s, background 0.12s;
		border-left: 2px solid transparent;
		margin-left: 0.25rem;
	}

	.dl-blog-category-link:hover {
		color: var(--dl-ink-print);
		background: var(--dl-mkt-card-2);
	}

	.dl-blog-category-link.active {
		color: var(--dl-ink-print);
		font-weight: 600;
		border-left-color: var(--dl-red);
		background: rgba(234, 70, 71, 0.05);
	}

	.dl-blog-main {
		min-width: 0;
	}

	@media (max-width: 960px) {
		.dl-blog-body {
			grid-template-columns: 1fr;
			gap: 1rem;
			padding: 1.5rem 0.75rem 4rem;
			max-width: 100%;
			min-width: 0;
		}

		.dl-blog-sidebar {
			max-width: 100%;
			min-width: 0;
			overflow: hidden;
		}

		.dl-blog-sidebar-inner {
			position: static;
			max-width: 100%;
			min-width: 0;
			overflow: hidden;
		}

		.dl-blog-category-nav {
			flex-direction: row;
			flex-wrap: nowrap;
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
			gap: 0;
			max-width: 100%;
			min-width: 0;
		}

		.dl-blog-nav-label { display: none; }

		.dl-blog-category-link {
			white-space: nowrap;
			border-left: none;
			margin-left: 0;
			border-bottom: 2px solid transparent;
			border-radius: 0;
			padding: 0.5rem 0.75rem;
		}

		.dl-blog-category-link.active {
			border-left-color: transparent;
			border-bottom-color: var(--dl-red);
		}
	}

	@media (max-width: 480px) {
		.dl-blog-body {
			padding: 1rem 0.5rem 3rem;
			gap: 0.75rem;
		}
		.dl-blog-main {
			min-width: 0;
			max-width: 100%;
			overflow-x: hidden;
		}
	}
</style>
