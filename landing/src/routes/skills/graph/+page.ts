import { loadGraph } from '$lib/skills/graphData';

export const prerender = true;

export function load() {
	return {
		graph: loadGraph()
	};
}
