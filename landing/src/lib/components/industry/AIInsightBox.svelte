<script lang="ts">
	interface Insight {
		narrative?: string;
		strengths?: string[];
		weaknesses?: string[];
		sector?: string;
		source?: string;
	}

	interface BlogVerdict {
		verdict?: string;
		direction?: string;
		confidence?: string;
		archetype?: string;
		strengths?: string[];
		weaknesses?: string[];
	}

	let {
		insight,
		blogVerdict,
	}: { insight?: Insight | null; blogVerdict?: BlogVerdict | null } = $props();

	let mainVerdict = $derived(
		blogVerdict?.verdict || insight?.narrative?.split('\n')[0] || ''
	);
	let strengths = $derived(blogVerdict?.strengths?.length ? blogVerdict.strengths : insight?.strengths || []);
	let weaknesses = $derived(
		blogVerdict?.weaknesses?.length ? blogVerdict.weaknesses : insight?.weaknesses || []
	);
</script>

{#if mainVerdict || strengths.length || weaknesses.length}
	<div class="ai-insight">
		<header>
			<span class="badge">AI 분석</span>
			{#if blogVerdict?.archetype}
				<span class="archetype">{blogVerdict.archetype}</span>
			{/if}
			{#if blogVerdict?.direction}
				<span class="direction direction-{blogVerdict.direction}">{blogVerdict.direction}</span>
			{/if}
		</header>

		{#if mainVerdict}
			<p class="verdict">{mainVerdict}</p>
		{/if}

		<div class="pros-cons">
			{#if strengths.length}
				<div class="col">
					<h4>강점</h4>
					<ul>
						{#each strengths.slice(0, 4) as s}
							<li>{s}</li>
						{/each}
					</ul>
				</div>
			{/if}
			{#if weaknesses.length}
				<div class="col">
					<h4>약점</h4>
					<ul>
						{#each weaknesses.slice(0, 4) as w}
							<li>{w}</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.ai-insight {
		background: linear-gradient(135deg, #0f1219 0%, #1a1f2b 100%);
		border: 1px solid #1e2433;
		border-radius: 12px;
		padding: 20px;
		color: #f1f5f9;
	}
	header {
		display: flex;
		gap: 8px;
		align-items: center;
		margin-bottom: 12px;
	}
	.badge {
		background: linear-gradient(90deg, #ea4647, #fb923c);
		color: white;
		font-size: 11px;
		font-weight: 600;
		padding: 3px 10px;
		border-radius: 4px;
	}
	.archetype {
		color: #a78bfa;
		font-size: 12px;
		padding: 2px 8px;
		background: rgba(167, 139, 250, 0.15);
		border-radius: 4px;
	}
	.direction {
		font-size: 12px;
		padding: 2px 8px;
		border-radius: 4px;
	}
	.direction-개선 {
		background: rgba(52, 211, 153, 0.15);
		color: #34d399;
	}
	.direction-악화 {
		background: rgba(248, 113, 113, 0.15);
		color: #f87171;
	}
	.direction-유지 {
		background: rgba(148, 163, 184, 0.15);
		color: #94a3b8;
	}
	.verdict {
		margin: 0 0 16px;
		font-size: 15px;
		line-height: 1.6;
		color: #f1f5f9;
		font-weight: 500;
	}
	.pros-cons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}
	.col h4 {
		font-size: 11px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 8px;
	}
	.col ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.col li {
		font-size: 13px;
		padding: 4px 0 4px 14px;
		position: relative;
		color: #cbd5e1;
		line-height: 1.5;
	}
	.col:nth-child(1) li::before {
		content: '+';
		position: absolute;
		left: 0;
		color: #34d399;
		font-weight: 700;
	}
	.col:nth-child(2) li::before {
		content: '−';
		position: absolute;
		left: 0;
		color: #f87171;
		font-weight: 700;
	}
	@media (max-width: 640px) {
		.pros-cons {
			grid-template-columns: 1fr;
		}
	}
</style>
