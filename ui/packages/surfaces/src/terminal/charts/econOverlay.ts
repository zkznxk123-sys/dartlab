// 경제지표 캔들 오버레이 — Bloomberg식 "보이지 않는 독립축"을 페인 내부에 구현.
//   figures: [] → klinecharts y축 range 계산(figures[].key 만 참조)에 0 기여 = 캔들 스케일 무왜곡.
//   draw: 가시범위 기준 시리즈별 min-max 자기정규화 폴리라인 — 팬/줌마다 자동 re-fit (Bloomberg normalized).
//   tooltip: 리베이스 허구 숫자가 아닌 원시값(1,385원 · 3.50%) 표기.
// 비율 rebase(v/v₀·close₀)는 0 교차 시리즈(T10Y2Y·YoY)에서 수학적으로 붕괴 — 기각 근거.
// 날짜 정렬: 캔들 날짜축에 two-pointer forward-fill (첫 관측 전 = 결측, look-ahead 방지).
import type { MacroPoint, MacroSeriesDef } from '@dartlab/ui-contracts';
import type { Lang } from '../lib/types';

export const ECON_INDICATOR = 'ECON';
// 캔들 상승 #34d399 / 하락 #f0616f / 마커 amber #fb923c 와 충돌하지 않는 고정 팔레트.
export const ECON_COLORS: Record<string, string> = {
	USDKRW: '#60a5fa',
	BASE_RATE: '#c084fc',
	CPI: '#f472b6',
	EXPORT: '#a3e635',
	CLI: '#2dd4bf',
	DGS10: '#818cf8',
	FEDFUNDS: '#38bdf8',
	T10Y2Y: '#94a3b8',
	CPIAUCSL: '#e879f9',
	PCOPPUSDM: '#facc15'
};

export interface EconExtend {
	lang: Lang;
	series: { def: MacroSeriesDef; points: MacroPoint[] }[];
}
type EconDatum = Record<string, number>; // seriesId → forward-fill 값. 결측 = 키 없음.

const tsToYmd = (ts: number): string => {
	const d = new Date(ts);
	return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, '0')}${String(d.getUTCDate()).padStart(2, '0')}`;
};

const fmt = (v: number, def: MacroSeriesDef): string =>
	`${v.toLocaleString('en-US', { minimumFractionDigits: def.digits ?? 2, maximumFractionDigits: def.digits ?? 2 })}${def.unit === 'pt' ? '' : def.unit}`;

let registered = false;
export function registerEconIndicator(kc: { registerIndicator: (t: unknown) => void }): void {
	if (registered) return;
	registered = true;
	kc.registerIndicator({
		name: ECON_INDICATOR,
		shortName: 'ECON',
		figures: [], // ⛔ 축 range 기여 0 — calcRange 는 figures[].key 만 본다
		calc: (dataList: { timestamp: number }[], indicator: { extendData?: EconExtend | null }): EconDatum[] => {
			const ext = indicator.extendData;
			const out: EconDatum[] = dataList.map(() => ({}));
			if (!ext?.series?.length) return out;
			const ymds = dataList.map((k) => tsToYmd(k.timestamp));
			for (const { def, points } of ext.series) {
				let j = 0;
				let v: number | null = null;
				for (let i = 0; i < out.length; i++) {
					while (j < points.length && points[j].d <= ymds[i]) v = points[j++].v;
					if (v != null) out[i][def.id] = v; // 첫 관측 전 = 결측 (백필 금지)
				}
			}
			return out;
		},
		draw: ({ ctx, indicator, visibleRange, bounding, xAxis }: any): boolean => {
			const ext = indicator.extendData as EconExtend | null;
			const result = indicator.result as EconDatum[];
			if (!ext?.series?.length || !result?.length) return true;
			const from = Math.max(0, visibleRange.from);
			const to = Math.min(result.length, visibleRange.to);
			const padY = bounding.height * 0.08;
			const top = bounding.top + padY;
			const h = bounding.height - padY * 2;
			for (const { def } of ext.series) {
				let lo = Infinity;
				let hi = -Infinity;
				for (let i = from; i < to; i++) {
					const v = result[i]?.[def.id];
					if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
				}
				if (lo === Infinity) continue;
				const span = hi - lo; // 평탄 구간(기준금리 동결) = 페인 중앙 수평선
				ctx.strokeStyle = ECON_COLORS[def.id] ?? '#8b919e';
				ctx.lineWidth = 1.5;
				ctx.setLineDash([]);
				ctx.beginPath();
				let started = false;
				for (let i = from; i < to; i++) {
					const v = result[i]?.[def.id];
					if (v == null) continue;
					const x = xAxis.convertToPixel(i);
					const y = span === 0 ? top + h / 2 : top + ((hi - v) / span) * h;
					if (started) ctx.lineTo(x, y);
					else { ctx.moveTo(x, y); started = true; }
				}
				ctx.stroke();
			}
			return true; // 기본 figure 렌더 생략 (그릴 figure 도 없음)
		},
		createTooltipDataSource: ({ indicator, crosshair }: any) => {
			const ext = indicator.extendData as EconExtend | null;
			const result = indicator.result as EconDatum[];
			const i = crosshair?.dataIndex ?? result.length - 1;
			const values = (ext?.series ?? []).flatMap(({ def }) => {
				const v = result[i]?.[def.id];
				if (v == null) return [];
				const color = ECON_COLORS[def.id] ?? '#8b919e';
				return [{ title: { text: `${ext!.lang === 'en' ? def.en : def.kr} `, color }, value: { text: fmt(v, def), color } }];
			});
			return { name: 'ECON', calcParamsText: '', values, icons: [] };
		}
	});
}
