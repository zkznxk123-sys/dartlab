<script lang="ts">
	import type { Lang, RadarAxis } from '../lib/types';

	interface Props {
		data: RadarAxis[];
		lang: Lang;
		size?: number;
		color?: string;
	}
	let { data, lang, size = 104, color = '#a78bfa' }: Props = $props();
	let canvas: HTMLCanvasElement | null = $state(null);

	$effect(() => {
		const cv = canvas;
		if (!cv) return;
		// 의존성 트래킹
		const d = data;
		const lg = lang;
		const dpr = window.devicePixelRatio || 1;
		cv.width = size * dpr;
		cv.height = size * dpr;
		cv.style.width = size + 'px';
		cv.style.height = size + 'px';
		const ctx = cv.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, size, size);
		const cx = size / 2;
		const cy = size / 2;
		const r = size / 2 - 16;
		const n = d.length;
		const ang = (i: number) => -Math.PI / 2 + (i / n) * Math.PI * 2;
		for (let g = 1; g <= 4; g++) {
			ctx.strokeStyle = g === 4 ? '#2a3142' : '#1b2130';
			ctx.beginPath();
			for (let i = 0; i <= n; i++) {
				const a = ang(i % n);
				const rr = (r * g) / 4;
				const x = cx + Math.cos(a) * rr;
				const y = cy + Math.sin(a) * rr;
				i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
			}
			ctx.stroke();
		}
		ctx.fillStyle = '#a7b2c2';
		ctx.font = '8px "Pretendard Variable",sans-serif';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'middle';
		d.forEach((ax, i) => {
			const a = ang(i);
			ctx.strokeStyle = '#1b2130';
			ctx.beginPath();
			ctx.moveTo(cx, cy);
			ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
			ctx.stroke();
			const lx = cx + Math.cos(a) * (r + 9);
			const ly = cy + Math.sin(a) * (r + 9);
			ctx.fillText(lg === 'en' ? ax.en : ax.kr, lx, ly);
		});
		ctx.beginPath();
		d.forEach((ax, i) => {
			const a = ang(i);
			const s = ax.s == null ? 0 : ax.s;
			const x = cx + Math.cos(a) * r * s;
			const y = cy + Math.sin(a) * r * s;
			i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
		});
		ctx.closePath();
		ctx.fillStyle = 'rgba(167, 139, 250, 0.22)';
		ctx.fill();
		ctx.strokeStyle = color;
		ctx.lineWidth = 1.5;
		ctx.stroke();
		d.forEach((ax, i) => {
			const a = ang(i);
			const s = ax.s == null ? 0 : ax.s;
			const x = cx + Math.cos(a) * r * s;
			const y = cy + Math.sin(a) * r * s;
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(x, y, 1.8, 0, 7);
			ctx.fill();
		});
	});
</script>

<canvas bind:this={canvas}></canvas>
