<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import type { GraphPayload, GraphNode, GraphRegion } from '$lib/skills/graphData';
	import { buildCategoryRegions, buildForceSimulation, buildHierarchy } from '$lib/skills/graphData';
	import { colorOf, edgeStyleByKind } from '$lib/skills/categoryColors';

	type Props = {
		graph: GraphPayload;
		mode?: 'tree' | 'force';
		width?: number;
		height?: number;
		filterCategory?: string;
		query?: string;
	};

	let {
		graph,
		mode = 'force',
		width = 1200,
		height = 800,
		filterCategory = 'all',
		query = ''
	}: Props = $props();

	let svgEl: SVGSVGElement;
	let simulation: any = null;
	let positionedNodes = $state<any[]>([]);
	let positionedLinks = $state<any[]>([]);
	let regions = $state<GraphRegion[]>([]);
	let hoverNode = $state<GraphNode | null>(null);

	function nodeMatchesFilter(node: GraphNode): boolean {
		if (filterCategory !== 'all' && node.category !== filterCategory) return false;
		if (query) {
			const q = query.toLowerCase();
			return (
				node.id.toLowerCase().includes(q) ||
				node.title.toLowerCase().includes(q) ||
				node.purpose.toLowerCase().includes(q)
			);
		}
		return true;
	}

	function nodeRadius(node: GraphNode): number {
		const baseRadius = node.isEntry ? 8 : 4.5;
		return baseRadius + Math.min(6, node.inDegree * 0.22);
	}

	function showNodeLabel(node: GraphNode): boolean {
		if (!nodeMatchesFilter(node)) return false;
		return Boolean(query) || filterCategory !== 'all' || node.isEntry || node.inDegree >= 18;
	}

	function renderForce() {
		const { nodes, links, simulation: sim } = buildForceSimulation(graph, { width, height });
		simulation = sim;
		regions = buildCategoryRegions(graph, { width, height });
		positionedNodes = [...nodes];
		positionedLinks = [...links];
		sim.on('tick', () => {
			positionedNodes = [...nodes];
			positionedLinks = [...links];
		});
	}

	function renderTree() {
		const root = buildHierarchy(graph, { width, height });
		const nodes: any[] = [];
		const links: any[] = [];
		root.each((d: any) => {
			if (d.data.node) {
				nodes.push({ ...d.data.node, x: d.y + 120, y: d.x + 40 });
			}
			if (d.parent && d.data.node) {
				links.push({ source: { x: d.parent.y + 120, y: d.parent.x + 40 }, target: { x: d.y + 120, y: d.x + 40 }, kind: 'successor' });
			}
		});
		positionedNodes = nodes;
		positionedLinks = links;
		regions = [];
	}

	$effect(() => {
		if (simulation) simulation.stop();
		if (mode === 'force') renderForce();
		else renderTree();
	});

	onDestroy(() => {
		if (simulation) simulation.stop();
	});

	function onNodeClick(node: GraphNode) {
		goto(`${base}/skills/${node.id}`);
	}

	function onNodeKeydown(event: KeyboardEvent, node: GraphNode) {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		onNodeClick(node);
	}
</script>

<div class="graph-wrap">
	<svg bind:this={svgEl} {width} {height} viewBox="0 0 {width} {height}">
		{#if mode === 'force'}
			<g class="regions">
				{#each regions as region}
					<rect
						x={region.x}
						y={region.y}
						width={region.width}
						height={region.height}
						rx="10"
						fill={colorOf(region.id)}
						opacity="0.055"
						stroke={colorOf(region.id)}
						stroke-width="1"
						stroke-opacity="0.28"
					/>
					<text x={region.x + 16} y={region.y + 26} class="region-title" fill={colorOf(region.id)}>
						{region.title}
					</text>
					<text x={region.x + 16} y={region.y + 45} class="region-count">
						{region.count} skills
					</text>
				{/each}
			</g>
		{/if}
		<g class="edges">
			{#each positionedLinks as link}
				{@const style = edgeStyleByKind[link.kind] ?? edgeStyleByKind.knowledge}
				{@const sourceVisible = link.source ? nodeMatchesFilter(link.source) : true}
				{@const targetVisible = link.target ? nodeMatchesFilter(link.target) : true}
				<line
					x1={link.source?.x ?? 0}
					y1={link.source?.y ?? 0}
					x2={link.target?.x ?? 0}
					y2={link.target?.y ?? 0}
					stroke={style.stroke}
					stroke-width={style.width}
					stroke-dasharray={style.dash}
					opacity={sourceVisible && targetVisible ? 0.22 : 0.035}
				/>
			{/each}
		</g>
		<g class="nodes">
			{#each positionedNodes as node}
				{@const visible = nodeMatchesFilter(node)}
				<circle
					cx={node.x ?? width / 2}
					cy={node.y ?? height / 2}
					r={nodeRadius(node)}
					fill={colorOf(node.category)}
					stroke={node.isEntry ? '#f1f3f7' : '#0f0f10'}
					stroke-width={node.isEntry ? 2.2 : 1}
					opacity={visible ? 0.96 : 0.08}
					role="button"
					tabindex="0"
					aria-label={`${node.title} skill 열기`}
					onclick={() => onNodeClick(node)}
					onkeydown={(event) => onNodeKeydown(event, node)}
					onmouseenter={() => (hoverNode = node)}
					onmouseleave={() => (hoverNode = null)}
					style="cursor: pointer"
				/>
			{/each}
		</g>
		<g class="labels">
			{#each positionedNodes as node}
				{#if showNodeLabel(node)}
					<text x={(node.x ?? width / 2) + nodeRadius(node) + 5} y={(node.y ?? height / 2) + 4}>
						{node.title}
					</text>
				{/if}
			{/each}
		</g>
	</svg>
	{#if hoverNode}
		<div class="tooltip">
			<div class="tip-title">{hoverNode.title}</div>
			<div class="tip-id">{hoverNode.id}</div>
			<div class="tip-purpose">{hoverNode.purpose}</div>
		</div>
	{/if}
</div>

<style>
	.graph-wrap {
		position: relative;
		width: 100%;
		overflow: hidden;
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-lg);
		background: var(--dl-bg-deep);
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
	}
	.region-title {
		font-family: var(--dl-font-mono);
		font-size: 13px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
	.region-count {
		font-family: var(--dl-font-mono);
		font-size: 11px;
		fill: var(--dl-ink-dim);
	}
	.labels text {
		font-family: var(--dl-font-ui);
		font-size: 10px;
		font-weight: 600;
		fill: var(--dl-ink-mute);
		paint-order: stroke;
		stroke: var(--dl-bg-deep);
		stroke-width: 3px;
	}
	.tooltip {
		position: absolute;
		top: 12px;
		right: 12px;
		background: rgba(37, 39, 45, 0.96);
		color: var(--dl-ink-print);
		padding: 12px 16px;
		border: 1px solid var(--dl-line-strong);
		border-radius: var(--dl-r-md);
		max-width: 320px;
		pointer-events: none;
		font-size: 13px;
		line-height: 1.5;
		box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
	}
	.tip-title {
		font-weight: 600;
		margin-bottom: 4px;
	}
	.tip-id {
		font-family: monospace;
		font-size: 11px;
		color: var(--dl-ink-dim);
		margin-bottom: 8px;
	}
	.tip-purpose {
		color: var(--dl-ink-mute);
	}
</style>
