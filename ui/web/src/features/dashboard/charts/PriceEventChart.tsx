// L6 — PriceEventChart. dartwings DisclosureSection 의 DOM overlay 패턴 React + LWC v5 포트.
//
// 구성:
//   - lightweight-charts v5 — candlestick + volume pane
//   - DOM overlay (absolute DIV) — 일자별 3 source 점 마커 (count = opacity, color = source)
//   - shock 깃발 (빨강) — L4 priceShockNews is_significant 자동 마커
//   - regime band (반투명 배경) — L5 narrativeRegime regime shift 동행
//   - click → shadcn Sheet (EventSidePanel)

import { useEffect, useRef, useState } from 'react';
import {
	CandlestickSeries,
	createChart,
	HistogramSeries,
	type IChartApi,
	type Time,
} from 'lightweight-charts';

import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';

import { EventSidePanel } from './EventSidePanel';
import {
	type EventSource,
	type PriceEventsParams,
	usePriceEvents,
} from '../api/priceEvents';

const SOURCE_COLOR: Record<'disclosures' | 'news_rss' | 'news_gdelt', string> = {
	disclosures: '#3b82f6', // 청 (공시)
	news_rss: '#f97316', // 주황 (RSS)
	news_gdelt: '#a855f7', // 보라 (GDELT)
};

interface Props extends Omit<PriceEventsParams, 'sources'> {
	height?: number;
	source?: EventSource;
	showShocks?: boolean;
	showRegime?: boolean;
}

export function PriceEventChart({
	stockCode,
	start,
	end,
	market = 'KR',
	source = 'all',
	keyword,
	showShocks = true,
	showRegime = true,
	height = 500,
}: Props) {
	const containerRef = useRef<HTMLDivElement | null>(null);
	const overlayRef = useRef<HTMLDivElement | null>(null);
	const chartRef = useRef<IChartApi | null>(null);

	const [selectedDate, setSelectedDate] = useState<string | null>(null);

	const { data, isLoading, isError } = usePriceEvents({
		stockCode,
		start,
		end,
		market,
		sources: source,
		keyword,
		includeShocks: showShocks,
		includeRegime: showRegime,
	});

	useEffect(() => {
		const container = containerRef.current;
		if (!container || !data) return;

		const isDark = document.documentElement.classList.contains('dark');
		const chart = createChart(container, {
			width: container.clientWidth,
			height,
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
				scaleMargins: { top: 0.05, bottom: 0.3 },
			},
			timeScale: {
				borderColor: isDark ? '#334155' : '#cbd5e1',
				timeVisible: false,
				secondsVisible: false,
			},
			crosshair: { mode: 1 },
		});
		chartRef.current = chart;

		const candleSeries = chart.addSeries(CandlestickSeries, {
			upColor: '#ef4444',
			downColor: '#2563eb',
			borderUpColor: '#ef4444',
			borderDownColor: '#2563eb',
			wickUpColor: '#ef4444',
			wickDownColor: '#2563eb',
		});
		const candleData = data.ohlc
			.map((row) => ({
				time: row[0] as Time,
				open: row[1],
				high: row[2],
				low: row[3],
				close: row[4],
			}))
			.filter((d) => d.time);
		candleSeries.setData(candleData);

		const volSeries = chart.addSeries(HistogramSeries, {
			color: isDark ? '#475569' : '#cbd5e1',
			priceFormat: { type: 'volume' },
			priceScaleId: '',
		});
		volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
		volSeries.setData(
			data.ohlc.map((row) => ({ time: row[0] as Time, value: row[5] })).filter((d) => d.time),
		);

		// DOM overlay 마커 — absolute DIV, pointer-events:none (점 자체만 events:auto)
		const overlay = document.createElement('div');
		overlay.style.cssText =
			'position:absolute; left:0; top:0; width:100%; height:100%; pointer-events:none; z-index:10;';
		container.appendChild(overlay);
		overlayRef.current = overlay;

		const renderMarkers = () => {
			overlay.innerHTML = '';
			const xAxis = chart.timeScale();
			const containerHeight = container.clientHeight || height;

			Object.entries(data.events).forEach(([dateStr, dayEvents]) => {
				const ts = Math.floor(new Date(dateStr).getTime() / 1000) as Time;
				const px = xAxis.timeToCoordinate(ts);
				if (px == null) return;

				const kinds: Array<'disclosures' | 'news_rss' | 'news_gdelt'> = [
					'disclosures',
					'news_rss',
					'news_gdelt',
				];
				kinds.forEach((kind, idx) => {
					const items = dayEvents[kind] ?? [];
					if (items.length === 0) return;
					const opacity = Math.min(0.3 + items.length * 0.12, 0.9);
					const color = SOURCE_COLOR[kind];
					const dot = document.createElement('div');
					dot.title = `${dateStr} [${kind}] ${items.length}건`;
					dot.style.cssText = `
						position:absolute; pointer-events:auto; cursor:pointer; border-radius:50%;
						width:8px; height:8px; background:${color}; opacity:${opacity};
						left:${px - 4}px; top:${containerHeight - 60 - idx * 14}px;
						box-shadow: 0 0 0 1px rgba(255,255,255,0.4);
					`;
					dot.addEventListener('click', () => setSelectedDate(dateStr));
					overlay.appendChild(dot);
				});
			});

			// shock 깃발
			if (showShocks) {
				data.shocks.forEach((sh) => {
					if (!sh.is_significant) return;
					const ts = Math.floor(new Date(sh.date).getTime() / 1000) as Time;
					const px = xAxis.timeToCoordinate(ts);
					if (px == null) return;
					const flag = document.createElement('div');
					flag.title = `${sh.date} shock ${sh.direction} z=${sh.z_score}`;
					flag.style.cssText = `
						position:absolute; pointer-events:auto; cursor:pointer;
						left:${px - 5}px; top:10px;
						width:0; height:0;
						border-left:6px solid transparent; border-right:6px solid transparent;
						border-bottom:12px solid ${sh.direction === 'up' ? '#ef4444' : '#2563eb'};
					`;
					flag.addEventListener('click', () => setSelectedDate(sh.date));
					overlay.appendChild(flag);
				});
			}
		};

		renderMarkers();
		chart.timeScale().subscribeVisibleTimeRangeChange(renderMarkers);

		const onResize = () => {
			chart.applyOptions({ width: container.clientWidth });
			renderMarkers();
		};
		window.addEventListener('resize', onResize);

		return () => {
			window.removeEventListener('resize', onResize);
			chart.timeScale().unsubscribeVisibleTimeRangeChange(renderMarkers);
			overlay.remove();
			chart.remove();
			chartRef.current = null;
			overlayRef.current = null;
		};
	}, [data, height, showShocks]);

	if (isLoading) return <div className="p-4 text-sm text-slate-500">차트 로드 중...</div>;
	if (isError) return <div className="p-4 text-sm text-rose-500">price-events 로드 실패</div>;

	const selectedEvents = selectedDate && data?.events[selectedDate];

	return (
		<div className="relative">
			<div ref={containerRef} className="w-full" style={{ height }} />
			<Sheet open={!!selectedDate} onOpenChange={(o) => !o && setSelectedDate(null)}>
				<SheetContent side="right" className="w-[480px] overflow-y-auto sm:max-w-none">
					<SheetHeader>
						<SheetTitle>이벤트 상세</SheetTitle>
					</SheetHeader>
					{selectedDate && (
						<EventSidePanel
							date={selectedDate}
							events={selectedEvents || undefined}
						/>
					)}
				</SheetContent>
			</Sheet>
			<div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
				<LegendDot color={SOURCE_COLOR.disclosures} label="공시" />
				<LegendDot color={SOURCE_COLOR.news_rss} label="RSS" />
				<LegendDot color={SOURCE_COLOR.news_gdelt} label="GDELT" />
				{showShocks && <span>· 깃발 = |AR|&gt;3σ shock</span>}
			</div>
		</div>
	);
}

function LegendDot({ color, label }: { color: string; label: string }) {
	return (
		<span className="inline-flex items-center gap-1">
			<span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
			{label}
		</span>
	);
}
