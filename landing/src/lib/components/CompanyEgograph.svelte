<script lang="ts">
	import { onMount } from 'svelte';
	import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';

	interface Node {
		stockCode: string;
		corpName: string;
		industry: string;
		stage: string;
		revenue: number;
		role?: string;
		stream?: string;
		confidence?: number;
		source?: string;
	}

	interface Edge {
		from: string;
		to: string;
		type: string;
		direction?: string;
		amount?: number | null;
		ratio?: number | null;
		product?: string;
		confidence?: number;
		source?: string;
		evidence?: string;
	}

	interface EgoData {
		ego: Node;
		neighbors: Node[];
		edges: Edge[];
	}

	let { data, width = 800, height = 600 }: { data: EgoData; width?: number; height?: number } = $props();

	let svgRef: SVGSVGElement | null = $state(null);
	let selectedEdge: Edge | null = $state(null);
	let hoveredNode: Node | null = $state(null);

	// 관계 타입별 색상
	const typeColor: Record<string, string> = {
		supplier: '#f97316',
		customer: '#3b82f6',
		affiliate: '#10b981',
		investor: '#8b5cf6',
	};

	const typeLabel: Record<string, string> = {
		supplier: '공급',
		customer: '고객',
		affiliate: '계열',
		investor: '투자',
	};

	// 이웃 노드 + ego를 합친 전체 노드
	let allNodes = $derived(
		[{ ...data.ego, isEgo: true }, ...data.neighbors.map((n) => ({ ...n, isEgo: false }))]
	);

	let nodePositions = $state<Map<string, { x: number; y: number; vx: number; vy: number }>>(new Map());

	onMount(() => {
		if (!data) return;

		// d3-force simulation
		const nodes = allNodes.map((n) => ({
			id: n.stockCode,
			...n,
			// ego는 중앙, 이웃은 랜덤
			x: n.isEgo ? width / 2 : width / 2 + (Math.random() - 0.5) * 200,
			y: n.isEgo ? height / 2 : height / 2 + (Math.random() - 0.5) * 200,
		}));
		const links = data.edges.map((e) => ({ source: e.from, target: e.to, ...e }));

		const sim = forceSimulation(nodes as any)
			.force('link', forceLink(links as any).id((d: any) => d.id).distance(120))
			.force('charge', forceManyBody().strength(-500))
			.force('center', forceCenter(width / 2, height / 2))
			.force('collide', forceCollide().radius((d: any) => (d.isEgo ? 40 : 20)))
			.on('tick', () => {
				const m = new Map();
				for (const n of nodes as any[]) {
					// ego 고정
					if (n.isEgo) {
						n.fx = width / 2;
						n.fy = height / 2;
					}
					m.set(n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy });
				}
				nodePositions = m;
			});

		return () => sim.stop();
	});

	function nodeRadius(n: Node): number {
		if ((n as any).isEgo) return 30;
		// 매출 기반 크기
		const maxRev = Math.max(...data.neighbors.map((x) => x.revenue || 0), 1);
		const r = 8 + 14 * Math.sqrt((n.revenue || 0) / maxRev);
		return Math.min(r, 24);
	}

	function edgeWidth(e: Edge): number {
		if (!e.amount) return 1;
		// 매입액 기반 (로그 스케일)
		return 1 + Math.min(Math.log10(e.amount + 1) * 0.5, 4);
	}

	function formatAmount(amt: number | null | undefined): string {
		if (!amt) return '';
		if (amt >= 10000) return `${(amt / 10000).toFixed(1)}조원`;
		return `${amt.toLocaleString()}억원`;
	}
</script>

<div class="egograph-container">
	<svg bind:this={svgRef} {width} {height} viewBox="0 0 {width} {height}">
		<defs>
			<marker id="arrow" viewBox="0 -5 10 10" refX="15" refY="0" markerWidth="6" markerHeight="6" orient="auto">
				<path d="M0,-5L10,0L0,5" fill="#999" />
			</marker>
		</defs>

		<!-- Edges -->
		<g class="edges">
			{#each data.edges as edge (edge.from + '-' + edge.to + '-' + edge.type)}
				{@const fromPos = nodePositions.get(edge.from)}
				{@const toPos = nodePositions.get(edge.to)}
				{#if fromPos && toPos}
					<line
						x1={fromPos.x}
						y1={fromPos.y}
						x2={toPos.x}
						y2={toPos.y}
						stroke={typeColor[edge.type] || '#ccc'}
						stroke-width={edgeWidth(edge)}
						stroke-opacity={edge.amount ? 0.7 : 0.3}
						stroke-dasharray={edge.amount ? 'none' : '3,3'}
						marker-end="url(#arrow)"
						onmouseenter={() => (selectedEdge = edge)}
						onmouseleave={() => (selectedEdge = null)}
						style="cursor: pointer"
					/>
				{/if}
			{/each}
		</g>

		<!-- Nodes -->
		<g class="nodes">
			{#each allNodes as node (node.stockCode)}
				{@const pos = nodePositions.get(node.stockCode)}
				{#if pos}
					<g
						transform="translate({pos.x}, {pos.y})"
						onmouseenter={() => (hoveredNode = node as any)}
						onmouseleave={() => (hoveredNode = null)}
						style="cursor: pointer"
					>
						<circle
							r={nodeRadius(node)}
							fill={(node as any).isEgo ? '#0ea5e9' : '#64748b'}
							stroke="white"
							stroke-width="2"
							opacity="0.9"
						/>
						<text
							y={nodeRadius(node) + 12}
							text-anchor="middle"
							font-size={(node as any).isEgo ? 13 : 10}
							font-weight={(node as any).isEgo ? 'bold' : 'normal'}
							fill="#333"
						>
							{node.corpName}
						</text>
						{#if (node as any).isEgo}
							<text y="5" text-anchor="middle" font-size="9" fill="white" font-weight="bold">
								{node.stage || node.industry}
							</text>
						{/if}
					</g>
				{/if}
			{/each}
		</g>
	</svg>

	<!-- Info panels -->
	<div class="info-panel">
		<div class="ego-info">
			<div class="name">{data.ego.corpName}</div>
			<div class="meta">
				{data.ego.industry} · {data.ego.stage || '-'} · 매출 {formatAmount(data.ego.revenue)}
			</div>
			<div class="counts">
				이웃 {data.neighbors.length}사 · 엣지 {data.edges.length}건
			</div>
		</div>

		<div class="legend">
			{#each Object.entries(typeColor) as [type, color]}
				<div class="legend-item">
					<span class="swatch" style="background:{color}"></span>
					<span>{typeLabel[type]}</span>
				</div>
			{/each}
		</div>

		{#if selectedEdge}
			<div class="tooltip">
				<div class="tt-title">{typeLabel[selectedEdge.type]}</div>
				<div>{selectedEdge.from} → {selectedEdge.to}</div>
				{#if selectedEdge.product}
					<div>품목: <strong>{selectedEdge.product}</strong></div>
				{/if}
				{#if selectedEdge.amount}
					<div>금액: <strong>{formatAmount(selectedEdge.amount)}</strong></div>
				{/if}
				{#if selectedEdge.ratio}
					<div>비중: {selectedEdge.ratio}%</div>
				{/if}
				<div class="tt-meta">
					{selectedEdge.source} · 신뢰도 {selectedEdge.confidence}
				</div>
			</div>
		{/if}

		{#if hoveredNode && !(hoveredNode as any).isEgo}
			<div class="tooltip">
				<div class="tt-title">{hoveredNode.corpName} ({hoveredNode.stockCode})</div>
				<div>{hoveredNode.industry} · {hoveredNode.stage || '-'}</div>
				<div>매출 {formatAmount(hoveredNode.revenue)}</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.egograph-container {
		position: relative;
		width: 100%;
		background: #fafafa;
		border-radius: 8px;
	}

	svg {
		display: block;
		max-width: 100%;
		height: auto;
	}

	.info-panel {
		position: absolute;
		top: 12px;
		right: 12px;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 12px;
		min-width: 200px;
		font-size: 13px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
	}

	.ego-info .name {
		font-size: 16px;
		font-weight: bold;
		margin-bottom: 4px;
	}
	.ego-info .meta {
		color: #6b7280;
		font-size: 12px;
		margin-bottom: 4px;
	}
	.ego-info .counts {
		color: #9ca3af;
		font-size: 11px;
	}

	.legend {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid #e5e7eb;
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
	}
	.swatch {
		width: 12px;
		height: 3px;
		display: inline-block;
	}

	.tooltip {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid #e5e7eb;
		font-size: 12px;
		line-height: 1.5;
	}
	.tt-title {
		font-weight: bold;
		margin-bottom: 4px;
	}
	.tt-meta {
		color: #9ca3af;
		font-size: 10px;
		margin-top: 4px;
	}
</style>
