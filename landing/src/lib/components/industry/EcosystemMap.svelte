<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	interface NodeDatum {
		id: string;
		label: string;
		industry: string;
		industryName: string;
		stage: string;
		revenue: number;
		size: number;
		color: string;
	}

	interface LinkDatum {
		source: string;
		target: string;
		type: string;
		amount: number | null;
		ratio: number | null;
		product: string;
		confidence: number;
		source_tag: string;
	}

	interface Props {
		nodes: NodeDatum[];
		links: LinkDatum[];
		onNodeClick?: (node: NodeDatum | null) => void;
		onNodeHover?: (node: NodeDatum | null) => void;
	}

	let { nodes, links, onNodeClick, onNodeHover }: Props = $props();

	let container: HTMLDivElement | null = $state(null);
	let graph: any = $state(null);
	let currentZoom = $state(1);
	let hoveredNode: NodeDatum | null = $state(null);

	onMount(async () => {
		if (!container) return;

		// dynamic import to code-split Cosmos out of main bundle
		const { Graph } = await import('@cosmograph/cosmos');

		const canvas = document.createElement('canvas');
		container.appendChild(canvas);

		graph = new Graph(canvas, {
			spaceSize: 4096,
			backgroundColor: '#fafafa',
			pointSize: 4,
			pointColor: (n: NodeDatum) => n.color,
			pointGreyoutOpacity: 0.15,
			linkColor: (l: LinkDatum) => {
				if (l.type === 'supplier') return l.amount ? '#f97316' : '#fed7aa';
				if (l.type === 'customer') return '#3b82f6';
				if (l.type === 'investor') return '#8b5cf6';
				return '#d1d5db'; // affiliate
			},
			linkWidth: (l: LinkDatum) => {
				if (!l.amount) return 0.3;
				return Math.min(0.3 + Math.log10(l.amount + 1) * 0.2, 2);
			},
			linkGreyoutOpacity: 0.1,
			simulation: {
				repulsion: 1.0,
				gravity: 0.15,
				linkDistance: 10,
				friction: 0.85,
				decay: 1000,
			},
			onClick: (node: NodeDatum | undefined) => {
				onNodeClick?.(node ?? null);
				if (node && graph) {
					graph.zoomToNodeById(node.id, 700, 6, false);
				}
			},
			onPointMouseOver: (node: NodeDatum) => {
				hoveredNode = node;
				onNodeHover?.(node);
			},
			onPointMouseOut: () => {
				hoveredNode = null;
				onNodeHover?.(null);
			},
			onZoom: () => {
				if (graph) currentZoom = graph.getZoomLevel();
			},
		});

		graph.setData(nodes, links);

		// fit view after initial simulation
		setTimeout(() => graph?.fitView(400), 1200);

		// ResizeObserver
		const ro = new ResizeObserver(() => {
			if (canvas && container) {
				canvas.width = container.clientWidth;
				canvas.height = container.clientHeight;
			}
		});
		ro.observe(container);

		return () => {
			ro.disconnect();
			graph?.destroy?.();
		};
	});

	// 외부 제어 함수
	export function zoomToNode(id: string) {
		graph?.zoomToNodeById(id, 700, 6, false);
	}
	export function resetView() {
		graph?.fitView(700);
	}
	export function setSelection(ids: string[] | null) {
		if (!graph) return;
		if (ids && ids.length) graph.selectNodesByIds(ids);
		else graph.unselectNodes();
	}
</script>

<div bind:this={container} class="ecosystem-container">
	{#if hoveredNode}
		<div class="hover-chip">
			<strong>{hoveredNode.label}</strong>
			<span class="industry">{hoveredNode.industryName}</span>
			{#if hoveredNode.stage}
				<span class="stage">{hoveredNode.stage}</span>
			{/if}
			{#if hoveredNode.revenue > 0}
				<span class="revenue">
					{hoveredNode.revenue >= 1e12
						? `${(hoveredNode.revenue / 1e12).toFixed(1)}조`
						: `${Math.round(hoveredNode.revenue / 1e8).toLocaleString()}억`}원
				</span>
			{/if}
		</div>
	{/if}

	<div class="zoom-indicator">
		줌 {currentZoom.toFixed(1)}×
	</div>
</div>

<style>
	.ecosystem-container {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
		background: #fafafa;
	}
	:global(.ecosystem-container canvas) {
		display: block;
		width: 100%;
		height: 100%;
	}
	.hover-chip {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 9999px;
		padding: 8px 16px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		font-size: 13px;
		display: flex;
		gap: 8px;
		align-items: center;
		pointer-events: none;
		white-space: nowrap;
	}
	.hover-chip .industry {
		color: #6366f1;
		font-size: 11px;
		padding: 2px 6px;
		background: #eef2ff;
		border-radius: 4px;
	}
	.hover-chip .stage {
		color: #059669;
		font-size: 11px;
		padding: 2px 6px;
		background: #ecfdf5;
		border-radius: 4px;
	}
	.hover-chip .revenue {
		color: #d97706;
		font-weight: 600;
	}
	.zoom-indicator {
		position: absolute;
		top: 16px;
		right: 16px;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		padding: 4px 10px;
		font-size: 11px;
		color: #6b7280;
		font-family: monospace;
	}
</style>
