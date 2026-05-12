// Skill Graph 시각화 데이터 변환 — d3-hierarchy 트리 + d3-force simulation.
import graphPayload from '$skills/graph.json';
import * as d3 from 'd3-force';
import { hierarchy, tree } from 'd3-hierarchy';

export interface GraphNode {
	id: string;
	title: string;
	category: string;
	purpose: string;
	inDegree: number;
	outDegree: number;
	cluster: string | null;
	isEntry: boolean;
	isLeaf: boolean;
	isOrphan: boolean;
	audiences: string[];
}

export interface GraphEdge {
	src: string;
	dst: string;
	kind: 'successor' | 'predecessor' | 'linkedRecipe' | 'knowledge' | 'source';
}

export interface GraphPayload {
	nodes: GraphNode[];
	edges: GraphEdge[];
	entries: string[];
	cycles: string[][];
	orphans: string[];
	unreachable: string[];
}

export function loadGraph(): GraphPayload {
	return graphPayload as GraphPayload;
}

// d3-hierarchy 트리 변환 — 카테고리 → cluster → skill 3 단계 트리.
export function buildHierarchy(graph: GraphPayload, opts: { width: number; height: number }) {
	const byCategory: Record<string, Record<string, GraphNode[]>> = {};
	for (const node of graph.nodes) {
		const cat = node.category;
		const cl = node.cluster ?? cat;
		byCategory[cat] ??= {};
		byCategory[cat][cl] ??= [];
		byCategory[cat][cl].push(node);
	}

	type TreeNode = { name: string; children?: TreeNode[]; node?: GraphNode };
	const root: TreeNode = {
		name: 'DartLab Skill OS',
		children: Object.entries(byCategory).map(([cat, clusters]) => ({
			name: cat,
			children: Object.entries(clusters).map(([cl, nodes]) => ({
				name: cl,
				children: nodes.map((n) => ({ name: n.title || n.id, node: n }))
			}))
		}))
	};

	const layout = tree<TreeNode>().size([opts.height - 80, opts.width - 240]);
	const rootHierarchy = hierarchy<TreeNode>(root, (d) => d.children);
	layout(rootHierarchy);
	return rootHierarchy;
}

// d3-force simulation 셋업 — 257 노드, knowledge 점선/linkedRecipe 굵은선.
export function buildForceSimulation(
	graph: GraphPayload,
	opts: { width: number; height: number }
) {
	const nodes = graph.nodes.map((n) => ({ ...n }));
	const links = graph.edges
		.filter((e) => e.kind === 'successor' || e.kind === 'linkedRecipe' || e.kind === 'knowledge')
		.map((e) => ({ source: e.src, target: e.dst, kind: e.kind }));

	const sim = d3
		.forceSimulation(nodes as d3.SimulationNodeDatum[])
		.force(
			'link',
			d3
				.forceLink(links as d3.SimulationLinkDatum<d3.SimulationNodeDatum>[])
				.id((d: any) => d.id)
				.distance(60)
				.strength(0.4)
		)
		.force('charge', d3.forceManyBody().strength(-200))
		.force('collide', d3.forceCollide(28))
		.force('center', d3.forceCenter(opts.width / 2, opts.height / 2));

	return { nodes, links, simulation: sim };
}
