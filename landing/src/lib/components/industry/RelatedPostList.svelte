<script lang="ts">
	import { base } from '$app/paths';

	interface BlogPost {
		slug: string;
		title: string;
		description: string;
		date: string;
		grade?: string;
		verdict?: string;
		direction?: string;
		thumbnail?: string;
	}

	let { posts }: { posts: BlogPost[] } = $props();
</script>

{#if posts.length > 0}
	<div class="related-posts">
		<h3>관련 분석 ({posts.length})</h3>
		<ul>
			{#each posts as post (post.slug)}
				<li>
					<a href="{base}/blog/{post.slug}" class="post-card">
						<div class="post-header">
							<span class="post-date">{post.date}</span>
							{#if post.grade}
								<span class="grade">{post.grade}</span>
							{/if}
							{#if post.direction}
								<span class="direction dir-{post.direction}">{post.direction}</span>
							{/if}
						</div>
						<div class="post-title">{post.title}</div>
						{#if post.verdict}
							<div class="post-verdict">{post.verdict}</div>
						{:else if post.description}
							<div class="post-desc">{post.description}</div>
						{/if}
					</a>
				</li>
			{/each}
		</ul>
	</div>
{/if}

<style>
	.related-posts {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 20px;
	}
	h3 {
		margin: 0 0 12px;
		font-size: 14px;
		color: #f1f5f9;
	}
	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 8px;
	}
	.post-card {
		display: block;
		padding: 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 8px;
		text-decoration: none;
		transition: border-color 0.2s, transform 0.1s;
	}
	.post-card:hover {
		border-color: #ea4647;
		transform: translateY(-1px);
	}
	.post-header {
		display: flex;
		gap: 6px;
		align-items: center;
		margin-bottom: 8px;
		flex-wrap: wrap;
	}
	.post-date {
		font-size: 11px;
		color: #64748b;
	}
	.grade {
		font-size: 10px;
		padding: 1px 6px;
		border-radius: 3px;
		background: rgba(251, 146, 60, 0.15);
		color: #fb923c;
		font-weight: 600;
	}
	.direction {
		font-size: 10px;
		padding: 1px 6px;
		border-radius: 3px;
	}
	.dir-개선 {
		background: rgba(52, 211, 153, 0.15);
		color: #34d399;
	}
	.dir-악화 {
		background: rgba(248, 113, 113, 0.15);
		color: #f87171;
	}
	.dir-유지 {
		background: rgba(148, 163, 184, 0.15);
		color: #94a3b8;
	}
	.post-title {
		font-size: 14px;
		color: #f1f5f9;
		font-weight: 600;
		line-height: 1.4;
		margin-bottom: 4px;
	}
	.post-verdict {
		font-size: 12px;
		color: #cbd5e1;
		line-height: 1.5;
	}
	.post-desc {
		font-size: 12px;
		color: #94a3b8;
		line-height: 1.5;
	}
</style>
