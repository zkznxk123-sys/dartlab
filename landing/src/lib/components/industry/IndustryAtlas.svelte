<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		forceSimulation,
		forceManyBody,
		forceCollide,
		forceCenter,
		forceLink,
		forceX,
		forceY
	} from 'd3-force';

	interface IndustryNode {
		id: string;
		name: string;
		revenue: number; // 억 단위
		nodeCount: number;
		color: string;
		stageMix?: Record<string, number>;
		stages?: any[];
	}

	interface FlowEdge {
		fromIndustry: string;
		toIndustry: string;
		edgeCount: number;
		amount: number;
	}

	interface Props {
		industries: IndustryNode[];
		flows: FlowEdge[];
		onSelect?: (ind: IndustryNode) => void;
	}

	let { industries, flows, onSelect }: Props = $props();

	let container: HTMLDivElement | null = $state(null);
	let w = $state(1200);
	let h = $state(800);
	let simNodes: any[] = $state([]);
	let simLinks: any[] = $state([]);
	let hovered: string | null = $state(null);
	let simulation: any = null;

	function radius(nodeCount: number): number {
		// area ∝ nodeCount, min 18, max 90
		return Math.max(18, Math.min(90, 9 + Math.sqrt(nodeCount) * 4.5));
	}

	function build() {
		if (!container) return;
		const rect = container.getBoundingClientRect();
		w = rect.width;
		h = rect.height;

		// 원형 배치 초기화 (nodeCount 큰 순으로 시계방향)
		const sorted = [...industries].sort((a, b) => b.nodeCount - a.nodeCount);
		const R = Math.min(w, h) * 0.33;
		simNodes = sorted.map((ind, i) => {
			const theta = (i / sorted.length) * Math.PI * 2 - Math.PI / 2;
			return {
				...ind,
				r: radius(ind.nodeCount),
				x: w / 2 + R * Math.cos(theta),
				y: h / 2 + R * Math.sin(theta)
			};
		});

		const byId = new Map(simNodes.map((n: any) => [n.id, n]));
		simLinks = flows
			.filter((f) => byId.has(f.fromIndustry) && byId.has(f.toIndustry))
			.map((f) => ({
				source: f.fromIndustry,
				target: f.toIndustry,
				edgeCount: f.edgeCount,
				amount: f.amount
			}));

		// 허브 산업 식별 (연결 차수 상위 20%)
		const degree = new Map<string, number>();
		for (const l of simLinks) {
			degree.set(l.source, (degree.get(l.source) || 0) + 1);
			degree.set(l.target, (degree.get(l.target) || 0) + 1);
		}
		const degreeValues = [...degree.values()].sort((a, b) => b - a);
		const hubThreshold = degreeValues[Math.floor(degreeValues.length * 0.2)] || 0;
		for (const n of simNodes) {
			n.degree = degree.get(n.id) || 0;
			n.isHub = n.degree >= hubThreshold && n.degree > 0;
		}

		simulation?.stop();
		simulation = forceSimulation(simNodes)
			.force(
				'charge',
				forceManyBody<any>()
					.strength((d: any) => -d.r * 28)
					.distanceMax(600)
			)
			.force(
				'collide',
				forceCollide<any>()
					.radius((d: any) => d.r + 14)
					.strength(1.0)
					.iterations(4)
			)
			.force('center', forceCenter(w / 2, h / 2).strength(0.02))
			.force('x', forceX(w / 2).strength(0.025))
			.force('y', forceY(h / 2).strength(0.035))
			.force(
				'link',
				forceLink<any, any>(simLinks)
					.id((d: any) => d.id)
					.distance(200)
					.strength(0.05)
			)
			.alphaDecay(0.018)
			.on('tick', () => {
				// reassign to trigger reactivity
				simNodes = [...simNodes];
				simLinks = [...simLinks];
			});
	}

	onMount(() => {
		build();
		const ro = new ResizeObserver(() => build());
		if (container) ro.observe(container);
		return () => {
			ro.disconnect();
			simulation?.stop();
		};
	});

	onDestroy(() => {
		simulation?.stop();
	});

	$effect(() => {
		// rebuild on data change
		if (industries && flows && container) build();
	});

	function formatRev(amountEok: number): string {
		// amount is in 억원
		if (amountEok >= 10000) return `${(amountEok / 10000).toFixed(1)}조`;
		return `${Math.round(amountEok).toLocaleString()}억`;
	}

	function edgeWidth(e: any): number {
		return Math.max(2.5, Math.min(10, 1.2 + Math.log2((e.edgeCount || 1) + 1) * 1.3));
	}

	function isConnected(nodeId: string): boolean {
		if (!hovered) return true;
		if (nodeId === hovered) return true;
		return simLinks.some(
			(l: any) =>
				(l.source.id === hovered && l.target.id === nodeId) ||
				(l.target.id === hovered && l.source.id === nodeId)
		);
	}

	function edgeConnected(l: any): boolean {
		if (!hovered) return true;
		return l.source.id === hovered || l.target.id === hovered;
	}
</script>

<div bind:this={container} class="atlas-container">
	<svg width={w} height={h} viewBox="0 0 {w} {h}">
		<defs>
			<filter id="flow-glow" x="-50%" y="-50%" width="200%" height="200%">
				<feGaussianBlur stdDeviation="2" result="blur" />
				<feMerge>
					<feMergeNode in="blur" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
			<filter id="hub-glow" x="-50%" y="-50%" width="200%" height="200%">
				<feGaussianBlur stdDeviation="4" result="blur" />
				<feMerge>
					<feMergeNode in="blur" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
			<marker
				id="arrow"
				markerWidth="8"
				markerHeight="8"
				refX="6"
				refY="4"
				orient="auto"
				markerUnits="strokeWidth"
			>
				<path d="M0,0 L0,8 L8,4 z" fill="#fbbf24" />
			</marker>
		</defs>

		<!-- 엣지: supplier flow -->
		<g class="flows" filter="url(#flow-glow)">
			{#each simLinks as l, i (i)}
				{@const sx = l.source.x ?? 0}
				{@const sy = l.source.y ?? 0}
				{@const tx = l.target.x ?? 0}
				{@const ty = l.target.y ?? 0}
				{@const mx = (sx + tx) / 2}
				{@const my = (sy + ty) / 2 - Math.abs(tx - sx) * 0.18}
				<path
					d="M{sx},{sy} Q{mx},{my} {tx},{ty}"
					fill="none"
					stroke="#fbbf24"
					stroke-width={edgeWidth(l)}
					stroke-linecap="round"
					opacity={edgeConnected(l) ? (hovered ? 0.95 : 0.7) : 0.12}
					marker-end="url(#arrow)"
				/>
			{/each}
		</g>

		<!-- 노드 -->
		<g class="nodes">
			{#each simNodes as n (n.id)}
				<g
					class="node"
					class:dim={!isConnected(n.id)}
					transform="translate({n.x ?? 0}, {n.y ?? 0})"
					onmouseenter={() => (hovered = n.id)}
					onmouseleave={() => (hovered = null)}
					onclick={() => onSelect?.(n)}
					role="button"
					tabindex="0"
					onkeydown={(e: KeyboardEvent) => e.key === 'Enter' && onSelect?.(n)}
				>
					<!-- 허브 glow -->
					{#if n.isHub}
						<circle
							r={n.r + 4}
							fill="none"
							stroke={n.color}
							stroke-width="1.5"
							opacity="0.5"
							filter="url(#hub-glow)"
						/>
					{/if}
					<!-- 외곽 링(hover 강조) -->
					{#if hovered === n.id}
						<circle r={n.r + 8} fill="none" stroke={n.color} stroke-width="2.5" opacity="0.9" />
					{/if}
					<circle
						r={n.r}
						fill={n.color}
						fill-opacity={hovered === n.id ? 0.95 : 0.85}
						stroke={n.isHub ? '#f8fafc' : n.color}
						stroke-width={n.isHub ? 2.5 : 1.5}
					/>
					<!-- 산업명 -->
					<text
						class="ind-label"
						text-anchor="middle"
						dominant-baseline="central"
						y={-4}
						font-size={Math.max(11, Math.min(16, n.r * 0.28))}
					>
						{n.name}
					</text>
					<!-- 회사 수 + 매출 -->
					<text
						class="ind-sub"
						text-anchor="middle"
						dominant-baseline="central"
						y={Math.max(11, Math.min(16, n.r * 0.28)) * 0.85 + 2}
						font-size={Math.max(9, Math.min(12, n.r * 0.2))}
					>
						{n.nodeCount}사 · {formatRev(n.revenue)}
					</text>
				</g>
			{/each}
		</g>
	</svg>

	<!-- 범례 -->
	<div class="legend">
		<div class="legend-item">
			<span class="legend-swatch flow"></span>
			<span>공급 플로우 — 굵기 = 거래 수</span>
		</div>
		<div class="legend-item">
			<span class="legend-swatch node"></span>
			<span>원 크기 = 소속 회사 수</span>
		</div>
		<div class="legend-note">산업 클릭 → 내부 드릴다운</div>
	</div>
</div>

<style>
	.atlas-container {
		position: relative;
		width: 100%;
		height: 100%;
		background: radial-gradient(
				ellipse at center,
				rgba(30, 41, 59, 0.3) 0%,
				transparent 70%
			),
			#050811;
		overflow: hidden;
	}
	svg {
		display: block;
	}
	.node {
		cursor: pointer;
		transition: opacity 0.2s;
	}
	.node.dim {
		opacity: 0.25;
	}
	.node:hover circle {
		filter: brightness(1.15);
	}
	.ind-label {
		font-family: 'Pretendard Variable', sans-serif;
		font-weight: 700;
		fill: #f8fafc;
		paint-order: stroke fill;
		stroke: rgba(5, 8, 17, 0.85);
		stroke-width: 3px;
		stroke-linejoin: round;
		letter-spacing: -0.02em;
		pointer-events: none;
		user-select: none;
	}
	.ind-sub {
		font-family: 'Pretendard Variable', sans-serif;
		font-weight: 500;
		fill: rgba(248, 250, 252, 0.85);
		paint-order: stroke fill;
		stroke: rgba(5, 8, 17, 0.85);
		stroke-width: 2.5px;
		stroke-linejoin: round;
		pointer-events: none;
		user-select: none;
	}
	.legend {
		position: absolute;
		left: 16px;
		bottom: 16px;
		background: rgba(15, 18, 25, 0.85);
		border: 1px solid #1e2433;
		border-radius: 8px;
		padding: 10px 12px;
		font-size: 11px;
		color: #cbd5e1;
		backdrop-filter: blur(8px);
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.legend-swatch {
		display: inline-block;
		width: 18px;
		height: 4px;
		border-radius: 2px;
	}
	.legend-swatch.flow {
		background: #fb923c;
	}
	.legend-swatch.node {
		background: linear-gradient(to right, #0ea5e9, #f97316);
		height: 10px;
		border-radius: 50%;
		width: 10px;
	}
	.legend-note {
		margin-top: 4px;
		color: #64748b;
		font-size: 10px;
	}
</style>
