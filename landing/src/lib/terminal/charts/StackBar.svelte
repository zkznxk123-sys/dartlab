<script lang="ts">
	import type { StackSeg } from '../data/types';
	import { fmtNum } from '../ui/helpers';

	interface Group {
		label: string;
		segs: StackSeg[];
	}
	interface Props {
		groups: Group[];
		unit?: string;
	}
	let { groups, unit = '조' }: Props = $props();
	const total = (segs: StackSeg[]) => segs.reduce((a, s) => a + (s.v > 0 ? s.v : 0), 0);
	// 범례 = 전 그룹 세그먼트 유니크 (색 기준)
	const legend = $derived(
		(() => {
			const seen = new Map<string, StackSeg>();
			for (const g of groups) for (const s of g.segs) if (!seen.has(s.kr)) seen.set(s.kr, s);
			return [...seen.values()];
		})()
	);
</script>

<div class="stackWrap">
	{#each groups as g (g.label)}
		{@const t = total(g.segs)}
		<div class="stackRow">
			<span class="stackLbl">{g.label}</span>
			<div class="stackBar">
				{#each g.segs as s (s.kr)}
					{#if s.v > 0}<span class="stackSeg" style={`width:${(s.v / t) * 100}%;background:${s.color}`} title={`${s.kr} ${fmtNum(s.v, 1)}${unit} (${((s.v / t) * 100).toFixed(0)}%)`}></span>{/if}
				{/each}
			</div>
			<span class="stackTot mono">{fmtNum(t, 0)}{unit}</span>
		</div>
	{/each}
	<div class="stackLegend">
		{#each legend as s (s.kr)}<span class="slItem"><span class="slDot" style={`background:${s.color}`}></span>{s.kr}</span>{/each}
	</div>
</div>
