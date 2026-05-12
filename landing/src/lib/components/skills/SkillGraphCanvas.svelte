<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import type { GraphPayload, GraphNode } from '$lib/skills/graphData';
	import { buildForceSimulation, buildHierarchy } from '$lib/skills/graphData';
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
		const base = node.isEntry ? 10 : 6;
		return base + Math.min(8, node.inDegree * 0.3);
	}

	function renderForce() {
		const { nodes, links, simulation: sim } = buildForceSimulation(graph, { width, height });
		simulation = sim;
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
</script>

<div class="graph-wrap">
	<svg bind:this={svgEl} {width} {height} viewBox="0 0 {width} {height}">
		<g class="edges">
			{#each positionedLinks as link}
				{@const style = edgeStyleByKind[link.kind] ?? edgeStyleByKind.knowledge}
				<line
					x1={link.source?.x ?? 0}
					y1={link.source?.y ?? 0}
					x2={link.target?.x ?? 0}
					y2={link.target?.y ?? 0}
					stroke={style.stroke}
					stroke-width={style.width}
					stroke-dasharray={style.dash}
					opacity="0.4"
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
					stroke={node.isEntry ? '#111' : '#fff'}
					stroke-width={node.isEntry ? 2.5 : 1.2}
					opacity={visible ? 1 : 0.15}
					onclick={() => onNodeClick(node)}
					onmouseenter={() => (hoverNode = node)}
					onmouseleave={() => (hoverNode = null)}
					style="cursor: pointer"
				/>
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
	}
	.tooltip {
		position: absolute;
		top: 12px;
		right: 12px;
		background: rgba(15, 23, 42, 0.92);
		color: #f8fafc;
		padding: 12px 16px;
		border-radius: 8px;
		max-width: 320px;
		pointer-events: none;
		font-size: 13px;
		line-height: 1.5;
	}
	.tip-title {
		font-weight: 600;
		margin-bottom: 4px;
	}
	.tip-id {
		font-family: monospace;
		font-size: 11px;
		color: #94a3b8;
		margin-bottom: 8px;
	}
	.tip-purpose {
		color: #cbd5e1;
	}
</style>
