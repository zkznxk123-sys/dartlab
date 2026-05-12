<script lang="ts">
	import SkillGraphCanvas from '$lib/components/skills/SkillGraphCanvas.svelte';
	import { categoryColor } from '$lib/skills/categoryColors';

	let { data } = $props();
	const graph = data.graph;

	let mode = $state<'tree' | 'force'>('force');
	let filterCategory = $state('all');
	let query = $state('');

	const categories = ['all', ...Object.keys(categoryColor).filter((c) =>
		['start', 'runtime', 'operation', 'engines'].includes(c)
	)];
</script>

<svelte:head>
	<title>Skill Graph · DartLab</title>
	<meta name="description" content="DartLab Skill OS 그래프 — 257 노드 + 1337 엣지를 클릭으로 탐색." />
</svelte:head>

<div class="graph-page">
	<header class="page-head">
		<h1>Skill Graph</h1>
		<p>
			257 sub-spec · {graph.entries.length} 진입점 · cycle {graph.cycles.length} · orphan {graph.orphans.length} ·
			unreachable {graph.unreachable.length} (maxHops 6)
		</p>
	</header>

	<div class="controls">
		<div class="control-group">
			<label>레이아웃</label>
			<button class:active={mode === 'force'} onclick={() => (mode = 'force')}>Force</button>
			<button class:active={mode === 'tree'} onclick={() => (mode = 'tree')}>Tree</button>
		</div>
		<div class="control-group">
			<label>카테고리</label>
			<select bind:value={filterCategory}>
				{#each categories as cat}
					<option value={cat}>{cat === 'all' ? '전체' : cat}</option>
				{/each}
			</select>
		</div>
		<div class="control-group">
			<label>검색</label>
			<input type="text" bind:value={query} placeholder="skill id · title · purpose" />
		</div>
	</div>

	<div class="legend">
		{#each ['start', 'runtime', 'operation', 'engines'] as cat}
			<span class="legend-item">
				<span class="dot" style="background: {categoryColor[cat]}"></span>
				{cat}
			</span>
		{/each}
		<span class="legend-item">실선 = successor / linkedRecipe</span>
		<span class="legend-item">점선 = knowledge</span>
	</div>

	<SkillGraphCanvas {graph} {mode} {filterCategory} {query} width={1200} height={760} />
</div>

<style>
	.graph-page {
		max-width: 1280px;
		margin: 0 auto;
		padding: 24px;
	}
	.page-head h1 {
		font-size: 28px;
		margin: 0 0 8px;
	}
	.page-head p {
		color: #64748b;
		margin: 0 0 24px;
		font-size: 14px;
	}
	.controls {
		display: flex;
		gap: 24px;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}
	.control-group {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.control-group label {
		font-size: 13px;
		color: #64748b;
	}
	.control-group button {
		padding: 4px 12px;
		border: 1px solid #cbd5e1;
		background: white;
		border-radius: 4px;
		cursor: pointer;
		font-size: 13px;
	}
	.control-group button.active {
		background: #0f172a;
		color: white;
		border-color: #0f172a;
	}
	.control-group select,
	.control-group input {
		padding: 4px 8px;
		border: 1px solid #cbd5e1;
		border-radius: 4px;
		font-size: 13px;
	}
	.legend {
		display: flex;
		gap: 16px;
		margin-bottom: 16px;
		font-size: 12px;
		color: #64748b;
		flex-wrap: wrap;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		display: inline-block;
	}
</style>
