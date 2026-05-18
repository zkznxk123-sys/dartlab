// kind=candle — TradingView lightweight-charts 기반 OHLC + volume + SMA overlay.
//
// 입력 spec.series 패턴:
//   - open/high/low/close (4 시리즈) → 캔들스틱 main pane
//   - sma20/sma60 (있으면) → main pane line overlay
//   - volume → 하단 separate pane (price scale 0)
//
// dark/light 토큰 감지 = document.documentElement.classList 'dark' 확인.

import { useEffect, useRef } from 'react';
import {
	createChart,
	CandlestickSeries,
	HistogramSeries,
	LineSeries,
	type IChartApi,
	type Time,
} from 'lightweight-charts';

import type { RechartsSpec } from '../api/client';

interface Props {
	spec: RechartsSpec;
	height?: number;
}

function seriesByKey(spec: RechartsSpec, key: string) {
	return spec.series.find((s) => s.key === key);
}

export function CandleChart({ spec, height = 400 }: Props) {
	const containerRef = useRef<HTMLDivElement | null>(null);
	const chartRef = useRef<IChartApi | null>(null);

	useEffect(() => {
		const container = containerRef.current;
		if (!container) return;

		const isDark = document.documentElement.classList.contains('dark');
		const chart = createChart(container, {
			width: container.clientWidth,
			height,
			localization: {
				locale: 'ko-KR',
				priceFormatter: (p: number) => Math.round(p).toLocaleString('ko-KR'),
			},
			layout: {
				background: { color: 'transparent' },
				textColor: isDark ? '#cbd5e1' : '#475569',
				fontSize: 11,
			},
			grid: {
				vertLines: { color: isDark ? '#1e293b' : '#e2e8f0' },
				horzLines: { color: isDark ? '#1e293b' : '#e2e8f0' },
			},
			rightPriceScale: {
				borderColor: isDark ? '#334155' : '#cbd5e1',
				scaleMargins: { top: 0.05, bottom: 0.25 },
			},
			timeScale: {
				borderColor: isDark ? '#334155' : '#cbd5e1',
				timeVisible: false,
				secondsVisible: false,
			},
			crosshair: { mode: 1 },
		});
		chartRef.current = chart;

		const open = seriesByKey(spec, 'open');
		const high = seriesByKey(spec, 'high');
		const low = seriesByKey(spec, 'low');
		const close = seriesByKey(spec, 'close');
		const sma20 = seriesByKey(spec, 'sma20');
		const sma60 = seriesByKey(spec, 'sma60');
		const volume = seriesByKey(spec, 'volume');

		if (open && high && low && close) {
			const candleSeries = chart.addSeries(CandlestickSeries, {
				upColor: '#ef4444', // KR convention — 빨강 상승
				downColor: '#2563eb', // 파랑 하락
				borderUpColor: '#ef4444',
				borderDownColor: '#2563eb',
				wickUpColor: '#ef4444',
				wickDownColor: '#2563eb',
				priceFormat: {
					type: 'custom',
					minMove: 1,
					formatter: (p: number) => Math.round(p).toLocaleString('ko-KR'),
				},
			});
			const candleData = spec.categories
				.map((t, i) => ({
					time: t as Time,
					open: open.data[i],
					high: high.data[i],
					low: low.data[i],
					close: close.data[i],
				}))
				.filter(
					(d) =>
						d.time &&
						d.open != null &&
						d.high != null &&
						d.low != null &&
						d.close != null,
				) as Array<{ time: Time; open: number; high: number; low: number; close: number }>;
			candleSeries.setData(candleData);
		}

		if (sma20) {
			const s = chart.addSeries(LineSeries, {
				color: '#10b981',
				lineWidth: 1,
				priceLineVisible: false,
				lastValueVisible: false,
			});
			s.setData(
				spec.categories
					.map((t, i) => ({ time: t as Time, value: sma20.data[i] }))
					.filter((d) => d.time && d.value != null) as Array<{ time: Time; value: number }>,
			);
		}

		if (sma60) {
			const s = chart.addSeries(LineSeries, {
				color: '#f59e0b',
				lineWidth: 1,
				priceLineVisible: false,
				lastValueVisible: false,
			});
			s.setData(
				spec.categories
					.map((t, i) => ({ time: t as Time, value: sma60.data[i] }))
					.filter((d) => d.time && d.value != null) as Array<{ time: Time; value: number }>,
			);
		}

		if (volume) {
			const volSeries = chart.addSeries(HistogramSeries, {
				color: isDark ? '#475569' : '#cbd5e1',
				priceFormat: { type: 'volume' },
				priceScaleId: '',
			});
			volSeries.priceScale().applyOptions({
				scaleMargins: { top: 0.8, bottom: 0 },
			});
			volSeries.setData(
				spec.categories
					.map((t, i) => ({ time: t as Time, value: volume.data[i], color: undefined }))
					.filter((d) => d.time && d.value != null) as Array<{ time: Time; value: number }>,
			);
		}

		chart.timeScale().fitContent();

		const onResize = () => {
			if (container) chart.applyOptions({ width: container.clientWidth });
		};
		window.addEventListener('resize', onResize);

		return () => {
			window.removeEventListener('resize', onResize);
			chart.remove();
			chartRef.current = null;
		};
	}, [spec, height]);

	return <div ref={containerRef} className="h-full w-full" style={{ height }} />;
}
