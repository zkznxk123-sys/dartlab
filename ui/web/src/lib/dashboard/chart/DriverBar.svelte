<!--
	DriverBar — driver contribution 분해 (수익성 axis 의 drivers nested array).
	각 driver = { factor, contribution_pp, share_pct }
	horizontal bar, 양수=up 색, 음수=down 색. 라벨 좌측 + bar + 우측 숫자.
-->
<script>
	import { isFiniteNum, fmtPp } from "./util.js";

	let {
		drivers = [],
		label = "",
		height = "auto",
	} = $props();

	const valid = $derived(
		drivers.filter((d) => isFiniteNum(d?.contribution_pp))
	);
	const maxAbs = $derived(
		valid.length === 0 ? 1 : Math.max(...valid.map((d) => Math.abs(d.contribution_pp)))
	);
</script>

<div class="w-full flex flex-col gap-1.5">
	{#if label}
		<div class="ed-eyebrow">{label}</div>
	{/if}
	<ul class="flex flex-col gap-1.5">
		{#each valid as d}
			{@const pct = (Math.abs(d.contribution_pp) / maxAbs) * 100}
			{@const positive = d.contribution_pp > 0}
			<li class="grid grid-cols-[140px_1fr_70px] items-center gap-3 text-[11.5px]">
				<span class="truncate" style="color: var(--ed-text-2);" title={d.factor}>{d.factor}</span>
				<div class="relative h-3 rounded-sm" style="background: var(--ed-surface-2);">
					<div
						class="absolute top-0 bottom-0 rounded-sm"
						style="
							left: {positive ? '50%' : `${50 - pct / 2}%`};
							width: {pct / 2}%;
							background: {positive ? 'var(--ed-up)' : 'var(--ed-down)'};
							opacity: 0.85;
						"
					></div>
					<div class="absolute top-0 bottom-0 left-1/2 w-px" style="background: var(--ed-text-3); opacity: 0.5;"></div>
				</div>
				<span class="ed-num text-right" style="color: {positive ? 'var(--ed-up)' : 'var(--ed-down)'};">
					{fmtPp(d.contribution_pp)}
				</span>
			</li>
		{/each}
		{#if valid.length === 0}
			<li class="text-[11px]" style="color: var(--ed-text-3);">drivers 데이터 없음</li>
		{/if}
	</ul>
</div>
