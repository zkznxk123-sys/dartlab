<script lang="ts">
	/**
	 * 인라인 SVG sparkline — 결과 테이블 행에 가격 시계열 미니 차트.
	 * 시작점 대비 끝점이 양수면 녹색, 음수면 빨강, 0 이면 중립.
	 */

	interface Props {
		values: number[];
		width?: number;
		height?: number;
	}

	let { values, width = 60, height = 18 }: Props = $props();

	const path = $derived.by(() => {
		if (!values || values.length < 2) return null;
		const min = Math.min(...values);
		const max = Math.max(...values);
		const range = max - min || 1;
		const stepX = (width - 2) / (values.length - 1);
		const pad = 1;
		const points = values.map((v, i) => {
			const x = pad + i * stepX;
			const y = pad + (height - 2) * (1 - (v - min) / range);
			return `${x.toFixed(1)},${y.toFixed(1)}`;
		});
		return 'M' + points.join(' L');
	});

	const tone = $derived.by(() => {
		if (!values || values.length < 2) return 'neutral';
		const first = values[0];
		const last = values[values.length - 1];
		if (last > first * 1.005) return 'up';
		if (last < first * 0.995) return 'down';
		return 'neutral';
	});

	const stroke = $derived(tone === 'up' ? '#34d399' : tone === 'down' ? '#f87171' : '#94a3b8');
</script>

{#if path}
	<svg {width} {height} class="sparkline" aria-hidden="true">
		<path d={path} fill="none" stroke={stroke} stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round" />
	</svg>
{:else}
	<span class="empty">—</span>
{/if}

<style>
	.sparkline {
		display: block;
	}
	.empty {
		font-size: 11px;
		color: #475569;
	}
</style>
