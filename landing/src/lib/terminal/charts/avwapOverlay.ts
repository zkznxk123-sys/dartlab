// 앵커드 VWAP — 앵커 시점부터 현재까지 (h+l+c)/3 거래량가중 평균 누적선 (기관 평단 추정).
// registerOverlay 기반: 매 paint 재계산이라 앵커 드래그·봉주기 전환·수정주가 토글 자동 추종.
// 측정룰러(MEASURE)도 본 파일 — 2점 구간 Δ가격·%·봉수·일수 즉석 표기, 영속 제외(선택 해제 시 제거).
import { viewCandles, viewIndexOf } from './seriesBus';

export const AVWAP_NAME = 'anchoredVWAP';
export const MEASURE_NAME = 'MEASURE';

let registered = false;
export function registerWorkOverlays(kc: { registerOverlay: (t: unknown) => void }): void {
	if (registered) return;
	registered = true;

	kc.registerOverlay({
		name: AVWAP_NAME,
		totalStep: 2, // 앵커 1점이면 완성
		needDefaultPointFigure: true,
		createPointFigures: ({ overlay, xAxis, yAxis }: any) => {
			const pt = overlay.points?.[0];
			if (pt?.timestamp == null) return [];
			const cs = viewCandles();
			if (!cs.length) return [];
			let i0 = viewIndexOf(pt.timestamp);
			if (i0 == null) {
				// 집계 전환 직후 등 timestamp 불일치 — 앵커 이후 첫 봉으로 근접 스냅
				i0 = cs.findIndex((k) => Date.UTC(+k.t.slice(0, 4), +k.t.slice(4, 6) - 1, +k.t.slice(6, 8)) >= pt.timestamp);
				if (i0 < 0) return [];
			}
			const coords: { x: number; y: number }[] = [];
			let pv = 0;
			let vv = 0;
			let last = 0;
			for (let i = i0; i < cs.length; i++) {
				const k = cs[i];
				pv += ((k.h + k.l + k.c) / 3) * k.v;
				vv += k.v;
				if (!vv) continue;
				last = pv / vv;
				coords.push({ x: xAxis.convertToPixel(i), y: yAxis.convertToPixel(last) });
			}
			if (coords.length < 2) return [];
			const end = coords[coords.length - 1];
			return [
				{ type: 'line', attrs: { coordinates: coords }, styles: { color: '#fbbf24', size: 1.5 } },
				{ type: 'text', attrs: { x: end.x, y: end.y - 4, text: `AVWAP ${Math.round(last).toLocaleString()}`, align: 'right', baseline: 'bottom' }, ignoreEvent: true, styles: { color: '#0b0e14', backgroundColor: '#fbbf24' } }
			];
		}
	});

	kc.registerOverlay({
		name: MEASURE_NAME,
		totalStep: 3, // 2점
		needDefaultPointFigure: true,
		createPointFigures: ({ overlay, coordinates }: any) => {
			if (!coordinates || coordinates.length < 2) return [];
			const [a, b] = coordinates;
			const [pa, pb] = overlay.points ?? [];
			const v0 = pa?.value ?? 0;
			const v1 = pb?.value ?? 0;
			const up = v1 >= v0;
			const pct = v0 ? (v1 / v0 - 1) * 100 : 0;
			const i0 = pa?.timestamp != null ? viewIndexOf(pa.timestamp) : undefined;
			const i1 = pb?.timestamp != null ? viewIndexOf(pb.timestamp) : undefined;
			const bars = i0 != null && i1 != null ? Math.abs(i1 - i0) : null;
			const days = pa?.timestamp != null && pb?.timestamp != null ? Math.round(Math.abs(pb.timestamp - pa.timestamp) / 86400000) : null;
			const col = up ? '#34d399' : '#f0616f';
			const label = `${up ? '+' : ''}${(v1 - v0).toLocaleString(undefined, { maximumFractionDigits: 0 })} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)${bars != null ? ` · ${bars}봉` : ''}${days != null ? ` · ${days}d` : ''}`;
			return [
				{
					type: 'rect',
					attrs: { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), width: Math.abs(b.x - a.x), height: Math.abs(b.y - a.y) },
					styles: { style: 'stroke_fill', color: up ? 'rgba(52,211,153,0.08)' : 'rgba(240,97,111,0.08)', borderColor: col, borderSize: 1, borderStyle: 'dashed', borderDashedValue: [3, 3] }
				},
				{ type: 'text', attrs: { x: (a.x + b.x) / 2, y: Math.min(a.y, b.y) - 5, text: label, align: 'center', baseline: 'bottom' }, ignoreEvent: true, styles: { color: '#0b0e14', backgroundColor: col } }
			];
		}
	});
}
