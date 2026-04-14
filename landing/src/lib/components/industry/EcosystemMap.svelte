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
	let industryLabels: Array<{ name: string; color: string; x: number; y: number; count: number }> = $state([]);

	function updateIndustryLabels() {
		if (!graph || !container) return;
		const positions = graph.getNodePositions(); // {id: {x, y}}
		if (!positions) return;

		// 산업별 노드 좌표 수집
		const byIndustry: Record<string, { xs: number[]; ys: number[]; name: string; color: string }> = {};
		for (const n of nodes) {
			const pos = positions[n.id];
			if (!pos) continue;
			if (!byIndustry[n.industry]) {
				byIndustry[n.industry] = { xs: [], ys: [], name: n.industryName, color: n.color };
			}
			byIndustry[n.industry].xs.push(pos.x);
			byIndustry[n.industry].ys.push(pos.y);
		}

		// 각 산업 중심(median)으로 계산 + 화면 좌표 변환
		const labels: typeof industryLabels = [];
		for (const [_id, d] of Object.entries(byIndustry)) {
			if (d.xs.length < 5) continue; // 너무 적은 산업은 제외
			const sx = [...d.xs].sort((a, b) => a - b);
			const sy = [...d.ys].sort((a, b) => a - b);
			const cx = sx[Math.floor(sx.length / 2)];
			const cy = sy[Math.floor(sy.length / 2)];
			// space 좌표 → 화면 좌표
			const screen = graph.spaceToScreenPosition([cx, cy]);
			if (!screen) continue;
			labels.push({
				name: d.name,
				color: d.color,
				x: screen[0],
				y: screen[1],
				count: d.xs.length,
			});
		}
		industryLabels = labels;
	}

	onMount(async () => {
		if (!container) return;

		// dynamic import to code-split Cosmos out of main bundle
		const { Graph } = await import('@cosmograph/cosmos');

		const canvas = document.createElement('canvas');
		container.appendChild(canvas);

		graph = new Graph(canvas, {
			spaceSize: 4096,
			backgroundColor: '#050811',
			pointSize: 5,
			pointColor: (n: NodeDatum) => n.color,
			pointGreyoutOpacity: 0.08,
			linkColor: (l: LinkDatum) => {
				if (l.type === 'supplier') return l.amount ? '#fb923c' : '#7c4a1e';
				if (l.type === 'customer') return '#60a5fa';
				if (l.type === 'investor') return '#a78bfa';
				return '#374151'; // affiliate
			},
			linkWidth: (l: LinkDatum) => {
				if (!l.amount) return 0.3;
				return Math.min(0.3 + Math.log10(l.amount + 1) * 0.2, 2);
			},
			linkGreyoutOpacity: 0.05,
			linkArrows: false,
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
				if (graph) {
					currentZoom = graph.getZoomLevel();
					updateIndustryLabels();
				}
			},
			onSimulationTick: () => updateIndustryLabels(),
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
	<!-- 산업 클러스터 라벨 오버레이 -->
	<svg class="label-overlay" xmlns="http://www.w3.org/2000/svg">
		{#each industryLabels as label (label.name)}
			<g transform="translate({label.x}, {label.y})">
				<text
					class="industry-label"
					text-anchor="middle"
					dominant-baseline="central"
					font-size={Math.max(14, Math.min(32, 12 + Math.log2(label.count) * 3))}
					fill={label.color}
					opacity={currentZoom < 3 ? 0.9 : 0.3}
				>
					{label.name}
				</text>
			</g>
		{/each}
	</svg>

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
		background: #050811;
	}
	:global(.ecosystem-container canvas) {
		display: block;
		width: 100%;
		height: 100%;
	}
	.label-overlay {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}
	.industry-label {
		font-family: 'Pretendard Variable', sans-serif;
		font-weight: 700;
		letter-spacing: -0.02em;
		paint-order: stroke fill;
		stroke: #050811;
		stroke-width: 3px;
		stroke-linejoin: round;
		transition: opacity 0.3s;
	}
	.hover-chip {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 9999px;
		padding: 8px 16px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
		font-size: 13px;
		color: #f1f5f9;
		display: flex;
		gap: 8px;
		align-items: center;
		pointer-events: none;
		white-space: nowrap;
	}
	.hover-chip .industry {
		color: #a78bfa;
		font-size: 11px;
		padding: 2px 6px;
		background: rgba(167, 139, 250, 0.15);
		border-radius: 4px;
	}
	.hover-chip .stage {
		color: #34d399;
		font-size: 11px;
		padding: 2px 6px;
		background: rgba(52, 211, 153, 0.15);
		border-radius: 4px;
	}
	.hover-chip .revenue {
		color: #fb923c;
		font-weight: 600;
	}
	.zoom-indicator {
		position: absolute;
		top: 16px;
		right: 16px;
		background: rgba(15, 18, 25, 0.8);
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 4px 10px;
		font-size: 11px;
		color: #94a3b8;
		font-family: monospace;
		backdrop-filter: blur(8px);
	}
</style>
