// 백테스트 차트 레이어 — klinecharts 커스텀 지표 2종 (overlay 대량 생성 금지: 단일 draw 가 정답).
//   BT_TRADES: candle_pane 매수▲/매도▼ 마커. figures:[] → y축 range 무기여(캔들 스케일 무왜곡),
//              draw 는 O(가시봉) Map lookup + barSpace LOD 2단 — 트레이드 수와 무관한 paint 비용.
//   BT_EQUITY: 서브 페인 에쿼티 라인 2본 (전략 vs B&H, 시작=100).
// 결과는 모듈 Map 으로 publish — calc 가 timestamp 로 조회. applyBt 의 calcParams:[rev] 가 재계산 트리거.
import type { Candle } from '@dartlab/ui-contracts';
import type { BtResult } from '../lib/backtest';

export const BT_TRADES = 'BT_TRADES';
export const BT_EQUITY = 'BT_EQUITY';

const tradeMap = new Map<number, { side: 'B' | 'S'; px: number }>();
const eqMap = new Map<number, { eq: number | null; bh: number | null }>();
let mddTs: { peak: number; recover: number | null } | null = null; // 최대낙폭 창 (timestamp) — 에쿼티 페인 음영

const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));

/** 모듈 스코프 1회 등록 (klinecharts 동적 import 직후 호출 — 내부 가드로 멱등). */
let registered = false;
export function registerBtIndicators(kc: { registerIndicator: (t: unknown) => void }): void {
	if (registered) return;
	registered = true;
	kc.registerIndicator({
		name: BT_TRADES,
		shortName: 'BT',
		figures: [],
		calc: (list: { timestamp: number }[]) => list.map(() => ({})),
		draw: ({ ctx, kLineDataList, visibleRange, barSpace, xAxis, yAxis }: any): boolean => {
			if (!tradeMap.size || barSpace.bar < 2) return true; // LOD-1: 초줌아웃 = 마커 생략 (에쿼티가 성과 전달)
			const label = barSpace.bar >= 8; // LOD-2: 가격 라벨은 가시 ≤ ~200봉에서만
			const from = Math.max(0, visibleRange.from);
			const to = Math.min(kLineDataList.length, visibleRange.to);
			ctx.font = '10px monospace';
			for (let i = from; i < to; i++) {
				const d = kLineDataList[i];
				const m = tradeMap.get(d.timestamp);
				if (!m) continue;
				const x = xAxis.convertToPixel(i);
				const s = 4.5;
				ctx.beginPath();
				if (m.side === 'B') {
					const y = yAxis.convertToPixel(d.low) + 12;
					ctx.fillStyle = '#34d399';
					ctx.moveTo(x, y - s);
					ctx.lineTo(x - s, y + s);
					ctx.lineTo(x + s, y + s);
					ctx.closePath();
					ctx.fill();
					if (label) { ctx.fillStyle = '#8b919e'; ctx.textAlign = 'center'; ctx.fillText(m.px.toLocaleString('en-US', { maximumFractionDigits: 0 }), x, y + s + 11); }
				} else {
					const y = yAxis.convertToPixel(d.high) - 12;
					ctx.fillStyle = '#f0616f';
					ctx.moveTo(x, y + s);
					ctx.lineTo(x - s, y - s);
					ctx.lineTo(x + s, y - s);
					ctx.closePath();
					ctx.fill();
					if (label) { ctx.fillStyle = '#8b919e'; ctx.textAlign = 'center'; ctx.fillText(m.px.toLocaleString('en-US', { maximumFractionDigits: 0 }), x, y - s - 4); }
				}
			}
			return true; // 기본 figure 렌더 생략
		}
	});
	kc.registerIndicator({
		name: BT_EQUITY,
		shortName: 'BT EQ',
		precision: 1,
		figures: [
			{ key: 'eq', title: 'BT ', type: 'line' },
			{ key: 'bh', title: 'B&H ', type: 'line' }
		],
		calc: (list: { timestamp: number }[]) => list.map((d) => eqMap.get(d.timestamp) ?? {}),
		// 최대낙폭 창(피크→회복) 음영 — return false 로 기본 라인이 음영 위에 렌더 (ICHI 패턴)
		draw: ({ ctx, kLineDataList, visibleRange, xAxis, bounding }: any): boolean => {
			if (!mddTs) return false;
			const from = Math.max(0, visibleRange.from);
			const to = Math.min(kLineDataList.length, visibleRange.to);
			let x0: number | null = null;
			let x1: number | null = null;
			for (let i = from; i < to; i++) {
				const ts = kLineDataList[i]?.timestamp;
				if (ts == null || ts < mddTs.peak || (mddTs.recover != null && ts > mddTs.recover)) continue;
				const x = xAxis.convertToPixel(i);
				if (x0 == null) x0 = x;
				x1 = x;
			}
			if (x0 != null && x1 != null) {
				ctx.fillStyle = 'rgba(240,97,111,0.10)';
				ctx.fillRect(x0, 0, Math.max(1, x1 - x0), bounding.height);
			}
			return false;
		}
	});
}

/** 결과 → 모듈 Map 교체. null = 해제. (최신 1슬롯 — 과거 런 캐시 금지) */
export function publishBt(result: BtResult | null, candles: Candle[]): void {
	tradeMap.clear();
	eqMap.clear();
	mddTs = null;
	if (!result) return;
	for (const tr of result.trades) {
		tradeMap.set(toMs(tr.entryT), { side: 'B', px: tr.entryPx });
		if (tr.exitT && tr.exitPx != null) tradeMap.set(toMs(tr.exitT), { side: 'S', px: tr.exitPx });
	}
	for (let i = result.startIdx; i < candles.length; i++) {
		eqMap.set(toMs(candles[i].t), { eq: result.equity[i], bh: result.bhEquity[i] });
	}
	const w = result.mddWindow;
	if (w && candles[w.peakIdx]) {
		mddTs = { peak: toMs(candles[w.peakIdx].t), recover: w.recoverIdx != null && candles[w.recoverIdx] ? toMs(candles[w.recoverIdx].t) : null };
	}
}

// 차트 인스턴스별 생성 여부 추적 — 회사전환에도 인스턴스는 영속하므로 WeakMap 으로 충분.
const created = new WeakMap<object, boolean>();

/** 지표 2종 생성(미존재 시) + calcParams:[rev] override 로 재계산 트리거. */
export function applyBt(chart: any, rev: number): void {
	if (!created.get(chart)) {
		const a = chart.createIndicator({ name: BT_TRADES }, true, { id: 'candle_pane' });
		// lines 배열은 기본값과 deep-merge 되지 않는다 — dashedValue/smooth/style 까지 완전 지정 (누락 = 내부 draw 크래시).
		const b = chart.createIndicator(
			{
				name: BT_EQUITY,
				styles: {
					lines: [
						{ color: '#fb923c', size: 1.4, style: 'solid', smooth: false, dashedValue: [2, 2] },
						{ color: '#8b919e', size: 1, style: 'dashed', smooth: false, dashedValue: [4, 4] }
					]
				}
			},
			false,
			{ id: 'pane_BT', height: 96, minHeight: 64, dragEnabled: true }
		);
		created.set(chart, !!(a || b));
	}
	try {
		chart.overrideIndicator({ name: BT_TRADES, calcParams: [rev] }, 'candle_pane');
		chart.overrideIndicator({ name: BT_EQUITY, calcParams: [rev] }, 'pane_BT');
	} catch { /* */ }
}

/** 지표 2종 제거 + Map 비움. */
export function clearBt(chart: any): void {
	publishBt(null, []);
	if (!created.get(chart)) return;
	created.delete(chart);
	try { chart.removeIndicator('candle_pane', BT_TRADES); } catch { /* */ }
	try { chart.removeIndicator('pane_BT', BT_EQUITY); } catch { /* */ }
}
