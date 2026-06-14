<script lang="ts">
	// 업종 분포 미니 곡선 + 회사 위치 마커.
	// 정규(Gaussian) 가정 아님 — p10~p90 5분위점에서 국소밀도(꼬리 포함)를 추정해
	// 실제 왜도(skew)를 반영한다. 회사값은 도메인 밖이어도 항상 보이게 포함.
	import type { Lang } from '../lib/types';

	let {
		band,
		value,
		p,
		unit = '',
		lang = 'kr',
		w = 150,
		h = 30
	}: {
		band: { p10: number; p25: number; median: number; p75: number; p90: number };
		value: number | null;
		p: number; // 0~100 백분위 (lowerBetter 이미 반영 — 높을수록 우수)
		unit?: string;
		lang?: Lang;
		w?: number; // 너비(중간패널 컴팩트 = 작게)
		h?: number;
	} = $props();

	const W = $derived(w);
	const H = $derived(h);
	const PAD = 3;

	const lo = $derived(Math.min(band.p10, value ?? band.p10));
	const hi = $derived(Math.max(band.p90, value ?? band.p90));
	const span = $derived(hi - lo || 1);
	function sx(v: number): number {
		return PAD + ((v - lo) / span) * (W - 2 * PAD);
	}

	// 5분위점 + 누적확률 → 국소밀도(중앙차분) → 최대로 정규화한 높이.
	const pts = $derived.by(() => {
		const xs = [band.p10, band.p25, band.median, band.p75, band.p90];
		const cum = [0.1, 0.25, 0.5, 0.75, 0.9];
		const dens = xs.map((_, i) => {
			const a = Math.max(0, i - 1);
			const b = Math.min(xs.length - 1, i + 1);
			const dw = xs[b] - xs[a] || 1;
			return (cum[b] - cum[a]) / dw;
		});
		const maxD = Math.max(...dens) || 1;
		return xs.map((x, i) => ({ x: sx(x), h: (dens[i] / maxD) * (H - 2 * PAD - 2) }));
	});

	const areaPath = $derived.by(() => {
		const base = H - PAD;
		if (!pts.length) return '';
		let d = `M ${pts[0].x.toFixed(1)} ${base}`;
		for (const pt of pts) d += ` L ${pt.x.toFixed(1)} ${(base - pt.h).toFixed(1)}`;
		d += ` L ${pts[pts.length - 1].x.toFixed(1)} ${base} Z`;
		return d;
	});

	const markX = $derived(value != null ? sx(value) : null);
	const tone = $derived(p >= 66 ? 'up' : p <= 33 ? 'dn' : 'mid');
	const tip = $derived(
		`${lang === 'en' ? 'peers' : '업종'} p10 ${band.p10.toFixed(1)} · ${lang === 'en' ? 'med' : '중앙'} ${band.median.toFixed(1)} · p90 ${band.p90.toFixed(1)}${unit && unit !== '%' ? '' : unit}`
	);
</script>

<svg class="dc" width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={tip} style={`height:${H}px`}>
	<title>{tip}</title>
	<path class="dcArea" d={areaPath} vector-effect="non-scaling-stroke" />
	<line class="dcMed" x1={sx(band.median)} x2={sx(band.median)} y1={PAD} y2={H - PAD} vector-effect="non-scaling-stroke" />
	{#if markX != null}
		<line class={'dcMark ' + tone} x1={markX} x2={markX} y1="0" y2={H} vector-effect="non-scaling-stroke" />
	{/if}
</svg>

<style>
	.dc {
		display: block;
		width: 100%;
		overflow: visible;
	}
	.dcArea {
		fill: rgba(139, 148, 158, 0.18);
		stroke: rgba(139, 148, 158, 0.5);
		stroke-width: 1;
	}
	.dcMed {
		stroke: rgba(139, 148, 158, 0.45);
		stroke-width: 1;
		stroke-dasharray: 2 2;
	}
	.dcMark {
		stroke-width: 2;
	}
	.dcMark.up {
		stroke: #3fb950;
	}
	.dcMark.dn {
		stroke: #f85149;
	}
	.dcMark.mid {
		stroke: #d29922;
	}
</style>
