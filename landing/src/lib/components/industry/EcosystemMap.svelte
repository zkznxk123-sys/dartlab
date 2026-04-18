<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let cleanupFns: Array<() => void> = [];
	onDestroy(() => {
		for (const fn of cleanupFns) fn();
	});

	interface NodeDatum {
		id: string;
		label: string;
		industry: string;
		industryName: string;
		stage: string;
		revenue: number;
		size: number;
		color: string;
		isIndustry?: boolean;
		nodeCount?: number;
		x?: number;
		y?: number;
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
		edgeCount?: number;
	}

	interface Props {
		nodes: NodeDatum[];
		links: LinkDatum[];
		isAtlas?: boolean;
		onNodeClick?: (node: NodeDatum | null) => void;
		onNodeHover?: (node: NodeDatum | null) => void;
	}

	let { nodes, links, isAtlas = false, onNodeClick, onNodeHover }: Props = $props();

	let container: HTMLDivElement | null = $state(null);
	let graph: any = $state(null);
	let currentZoom = $state(1);
	let hoveredNode: NodeDatum | null = $state(null);
	let industryLabels: Array<{ name: string; color: string; x: number; y: number; count: number; totalRev: number; radius: number }> =
		$state([]);
	let companyLabels: Array<{ id: string; name: string; x: number; y: number; rev: number }> = $state([]);

	function updateLabels() {
		if (!graph || !container) return;
		const positions = graph.getNodePositions();
		if (!positions) return;

		const zoom = currentZoom;

		// 산업별 집계
		const byIndustry: Record<
			string,
			{ xs: number[]; ys: number[]; name: string; color: string; totalRev: number }
		> = {};
		// 개별 회사 (줌 레벨에 따라 top N)
		const rendered: typeof companyLabels = [];
		const sortedByRev = [...nodes].sort((a, b) => (b.revenue || 0) - (a.revenue || 0));

		// atlas 뷰 (34개 산업): 모두 항상 라벨 표시. companies/industry: 줌에 따라 top N
		const topN = isAtlas
			? nodes.length
			: zoom < 1.5
				? 10
				: zoom < 3
					? 50
					: zoom < 5
						? 200
						: zoom < 8
							? 500
							: 1500;

		for (const n of nodes) {
			const pos = positions[n.id];
			if (!pos) continue;

			if (!byIndustry[n.industry]) {
				byIndustry[n.industry] = { xs: [], ys: [], name: n.industryName, color: n.color, totalRev: 0 };
			}
			byIndustry[n.industry].xs.push(pos.x);
			byIndustry[n.industry].ys.push(pos.y);
			byIndustry[n.industry].totalRev += n.revenue || 0;
		}

		// 산업 라벨
		const indLabels: typeof industryLabels = [];
		for (const [_id, d] of Object.entries(byIndustry)) {
			if (d.xs.length < 3) continue;
			const sx = [...d.xs].sort((a, b) => a - b);
			const sy = [...d.ys].sort((a, b) => a - b);
			const cx = sx[Math.floor(sx.length / 2)];
			const cy = sy[Math.floor(sy.length / 2)];
			const screen = graph.spaceToScreenPosition([cx, cy]);
			if (!screen) continue;
			// 반지름: 노드 좌표 분산으로 클러스터 크기 추정
			const maxDx = Math.max(...d.xs) - Math.min(...d.xs);
			const maxDy = Math.max(...d.ys) - Math.min(...d.ys);
			// 스크린 좌표 기준 반지름 (edge에서 다른 점으로 변환)
			const edgeScreen = graph.spaceToScreenPosition([cx + maxDx / 2, cy]);
			const screenRadius = edgeScreen ? Math.abs(edgeScreen[0] - screen[0]) + 10 : 40;

			indLabels.push({
				name: d.name,
				color: d.color,
				x: screen[0],
				y: screen[1],
				count: d.xs.length,
				totalRev: d.totalRev,
				radius: screenRadius,
			});
		}
		industryLabels = indLabels;

		// 회사 라벨 (매출 상위 N)
		if (topN > 0) {
			const visibleIds = new Set(sortedByRev.slice(0, topN).map((n) => n.id));
			for (const n of nodes) {
				if (!visibleIds.has(n.id)) continue;
				const pos = positions[n.id];
				if (!pos) continue;
				const screen = graph.spaceToScreenPosition([pos.x, pos.y]);
				if (!screen) continue;
				rendered.push({ id: n.id, name: n.label, x: screen[0], y: screen[1], rev: n.revenue || 0 });
			}
		}
		companyLabels = rendered;
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
			nodeSize: (n: NodeDatum) => {
				if (n.isIndustry) return Math.max(10, Math.min(40, n.size * 2));
				return Math.max(3, Math.min(14, n.size * 1.5));
			},
			nodeColor: (n: NodeDatum) => n.color,
			nodeGreyoutOpacity: 0.12,
			linkColor: (l: LinkDatum) => {
				if (l.type === 'supplier') return l.amount ? '#fbbf24' : '#f97316';
				if (l.type === 'customer') return '#60a5fa';
				if (l.type === 'investor') return '#a78bfa';
				return '#6b7280';
			},
			linkWidth: (l: LinkDatum) => {
				if (l.edgeCount) {
					return Math.max(2.5, Math.min(9, 1.2 + Math.log2(l.edgeCount + 1) * 1.3));
				}
				if (!l.amount) return 1.5;
				return Math.max(1.5, Math.min(7, 1.5 + Math.log10(l.amount + 1) * 0.8));
			},
			// companies: 줌 아웃 시 엣지 짧아 숨김, 줌 인하면 화면상 길어져 표시
			linkGreyoutOpacity: isAtlas ? 0.25 : 0.35,
			linkArrows: false,
			linkVisibilityDistanceRange: isAtlas ? [300, 2000] : [30, 400],
			linkVisibilityMinTransparency: isAtlas ? 0.75 : 0.1,
			curvedLinks: true,
			curvedLinkSegments: 16,
			simulation: {
				repulsion: isAtlas ? 1.0 : 0.1,
				gravity: isAtlas ? 0.15 : 0.0,
				linkDistance: isAtlas ? 10 : 2,
				friction: isAtlas ? 0.85 : 0.98,
				decay: isAtlas ? 1000 : 200,
				onTick: () => updateLabels(),
			},
			events: {
				onClick: (node: NodeDatum | undefined) => {
					onNodeClick?.(node ?? null);
					if (node && graph) {
						graph.zoomToNodeById(node.id, 700, 6, false);
					}
				},
				onNodeMouseOver: (node: NodeDatum) => {
					hoveredNode = node;
					onNodeHover?.(node);
				},
				onNodeMouseOut: () => {
					hoveredNode = null;
					onNodeHover?.(null);
				},
				onZoom: () => {
					if (graph) {
						currentZoom = graph.getZoomLevel();
						updateLabels();
					}
				},
			},
		});

		graph.setData(nodes, links);

		// fit view after initial simulation
		setTimeout(() => graph?.fitView(400), 1200);

		// raf 루프로 라벨 위치 갱신 (simulation tick 외 팬/줌 시에도)
		let rafId: number;
		const tick = () => {
			updateLabels();
			rafId = requestAnimationFrame(tick);
		};
		rafId = requestAnimationFrame(tick);

		// ResizeObserver
		const ro = new ResizeObserver(() => {
			if (canvas && container) {
				canvas.width = container.clientWidth;
				canvas.height = container.clientHeight;
			}
		});
		ro.observe(container);

		cleanupFns.push(() => {
			cancelAnimationFrame(rafId);
			ro.disconnect();
			graph?.destroy?.();
		});
	});

	// props(nodes/links) 변경 시 Cosmograph 데이터 재설정
	// currentZoom은 의존성에서 제외 (onZoom에서 별도 처리)
	$effect(() => {
		if (!graph) return;
		void nodes;
		void links;
		// companies 뷰에서는 onZoom 콜백이 엣지 토글 담당
		graph.setData(nodes, isAtlas ? links : []);
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
	<!-- 라벨 오버레이 -->
	<svg class="label-overlay" xmlns="http://www.w3.org/2000/svg">
		<!-- 산업 클러스터 배경 (줌 아웃~중간) -->
		{#if currentZoom < 6 && !isAtlas}
			{#each industryLabels as label (label.name)}
				<circle
					cx={label.x}
					cy={label.y}
					r={label.radius}
					fill={label.color}
					opacity={currentZoom < 2 ? 0.04 : 0.06}
					stroke={label.color}
					stroke-width="0.5"
					stroke-opacity="0.15"
				/>
			{/each}
		{/if}
		<!-- 산업 클러스터 라벨 (줌 아웃~중간) -->
		{#if currentZoom < 4}
			{#each industryLabels as label (label.name)}
				<g transform="translate({label.x}, {label.y})">
					<text
						class="industry-label"
						text-anchor="middle"
						dominant-baseline="central"
						font-size={Math.max(16, Math.min(36, 14 + Math.log2(label.count) * 3))}
						fill={label.color}
						opacity={currentZoom < 2 ? 0.95 : currentZoom < 3 ? 0.7 : 0.4}
					>
						{label.name}
					</text>
					<text
						class="industry-sub"
						text-anchor="middle"
						dominant-baseline="central"
						y={Math.max(18, Math.min(28, 14 + Math.log2(label.count) * 2))}
						font-size="10"
						fill="#94a3b8"
						opacity={currentZoom < 2 ? 0.8 : 0.4}
					>
						{label.count}사 · {label.totalRev >= 1e13
							? `${(label.totalRev / 1e12).toFixed(0)}조`
							: label.totalRev >= 1e11
								? `${(label.totalRev / 1e12).toFixed(1)}조`
								: `${Math.round(label.totalRev / 1e8)}억`}
					</text>
				</g>
			{/each}
		{/if}

		<!-- 회사 라벨 (줌 인 상태) -->
		{#if currentZoom >= 2}
			{#each companyLabels as label (label.id)}
				<text
					class="company-label"
					x={label.x}
					y={label.y - 10}
					text-anchor="middle"
					font-size={Math.min(13, 8 + currentZoom * 0.3)}
					opacity={currentZoom < 4 ? 0.7 : 0.95}
				>
					{label.name}
				</text>
			{/each}
		{/if}
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

	<div class="zoom-indicator" title="마우스 휠 / 트랙패드로 확대·축소">
		{currentZoom.toFixed(1)}×
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
		stroke-width: 4px;
		stroke-linejoin: round;
		transition: opacity 0.2s;
	}
	.industry-sub {
		font-family: 'Pretendard Variable', sans-serif;
		font-weight: 500;
		paint-order: stroke fill;
		stroke: #050811;
		stroke-width: 3px;
		stroke-linejoin: round;
		transition: opacity 0.2s;
	}
	.company-label {
		font-family: 'Pretendard Variable', sans-serif;
		font-weight: 500;
		fill: #f1f5f9;
		paint-order: stroke fill;
		stroke: #050811;
		stroke-width: 2.5px;
		stroke-linejoin: round;
		transition: opacity 0.2s;
		pointer-events: none;
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
		background: rgba(15, 18, 25, 0.85);
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 6px 10px;
		font-size: 11px;
		color: #94a3b8;
		font-family: monospace;
		backdrop-filter: blur(8px);
		cursor: help;
		z-index: 4;
	}
</style>
