import { loadCurrentPriceTail, loadOneYearPriceTail } from './priceRuntime';
import type { PriceTailOptions } from './priceRuntime';

type PriceTrendMessage = {
	type: 'priceTrend';
	year?: number;
	currentTailRows?: number;
	previousTailRows?: number;
};

type PriceTrendOneYearMessage = {
	type: 'priceTrend1y';
};

type WorkerMessage = PriceTrendMessage | PriceTrendOneYearMessage;

let currentRows: Awaited<ReturnType<typeof loadCurrentPriceTail>>['rows'] | null = null;
let currentOptions: PriceTailOptions = {};
let currentStats: { bytes: number; requests: number; durationMs: number } | null = null;

self.onmessage = (event: MessageEvent<WorkerMessage>) => {
	const msg = event.data;
	if (msg.type === 'priceTrend') {
		void loadPriceTrend(msg);
		return;
	}
	if (msg.type === 'priceTrend1y') {
		void loadOneYearTrend();
	}
};

async function loadPriceTrend(msg: PriceTrendMessage) {
	try {
		const current = await loadCurrentPriceTail({
			year: msg.year,
			currentTailRows: msg.currentTailRows
		});
		postMessage({
			type: 'priceTrend',
			metrics: current.metrics,
			latestDate: current.latestDate,
			sourcePaths: current.sourcePaths,
			bytes: current.bytes,
			requests: current.requests,
			durationMs: current.durationMs,
			partial: true
		});
		currentRows = current.rows;
		currentOptions = {
			year: msg.year,
			previousTailRows: msg.previousTailRows
		};
		currentStats = {
			bytes: current.bytes,
			requests: current.requests,
			durationMs: current.durationMs
		};
	} catch (err) {
		postMessage({ type: 'priceTrend-error', error: err instanceof Error ? err.message : String(err) });
	}
}

async function loadOneYearTrend() {
	try {
		if (!currentRows || !currentStats) return;
		const oneYear = await loadOneYearPriceTail(currentRows, currentOptions);
		postMessage({
			type: 'priceTrend',
			metrics: oneYear.metrics,
			latestDate: oneYear.latestDate,
			sourcePaths: oneYear.sourcePaths,
			bytes: currentStats.bytes + oneYear.bytes,
			requests: currentStats.requests + oneYear.requests,
			durationMs: currentStats.durationMs + oneYear.durationMs,
			partial: false
		});
	} catch (err) {
		postMessage({ type: 'priceTrend-error', error: err instanceof Error ? err.message : String(err) });
	}
}
