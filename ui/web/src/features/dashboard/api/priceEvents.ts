// L6 — /api/dartlab/price-events TanStack Query hook + 타입.
// dartwings DisclosureSection schema 확장 — 3 source (disclosure / news_rss / news_gdelt) + shocks + regime band.

import { useQuery } from '@tanstack/react-query';

export type EventSource = 'all' | 'disclosure' | 'news_rss' | 'news_gdelt';

export interface DisclosureItem {
	title: string;
	rceptNo: string;
	url: string;
	discType: string;
}

export interface NewsItem {
	title: string;
	source: string;
	url: string;
	sentiment_score: number | null;
	sentiment_label: string | null;
	themes?: string[];
}

export interface DayEvents {
	disclosures?: DisclosureItem[];
	news_rss?: NewsItem[];
	news_gdelt?: NewsItem[];
}

export interface ShockEvent {
	date: string;
	ar: number;
	z_score: number;
	direction: 'up' | 'down';
	is_significant: boolean;
}

export interface RegimeBand {
	start: string;
	end: string;
	label: string;
	score: number;
}

export interface PriceEventsPayload {
	stockCode: string;
	corpName: string | null;
	market: string;
	start: string;
	end: string;
	ohlc: number[][]; // [ts, open, high, low, close, volume]
	events: Record<string, DayEvents>;
	shocks: ShockEvent[];
	regime_band: RegimeBand[];
}

export interface PriceEventsParams {
	stockCode: string;
	start?: string;
	end?: string;
	market?: 'KR' | 'US';
	sources?: EventSource;
	discType?: string;
	keyword?: string;
	includeShocks?: boolean;
	includeRegime?: boolean;
}

export async function fetchPriceEvents(params: PriceEventsParams): Promise<PriceEventsPayload> {
	const q = new URLSearchParams();
	q.set('stockCode', params.stockCode);
	if (params.start) q.set('start', params.start);
	if (params.end) q.set('end', params.end);
	q.set('market', params.market ?? 'KR');
	q.set('sources', params.sources ?? 'all');
	q.set('discType', params.discType ?? 'all');
	if (params.keyword) q.set('keyword', params.keyword);
	q.set('includeShocks', String(params.includeShocks ?? true));
	q.set('includeRegime', String(params.includeRegime ?? true));
	const res = await fetch(`/api/dartlab/price-events?${q.toString()}`);
	if (!res.ok) throw new Error(`price-events fetch 실패: ${res.status}`);
	return (await res.json()) as PriceEventsPayload;
}

export const priceEventsKeys = {
	all: ['priceEvents'] as const,
	byParams: (params: PriceEventsParams) => ['priceEvents', params] as const,
};

export function usePriceEvents(params: PriceEventsParams) {
	return useQuery({
		queryKey: priceEventsKeys.byParams(params),
		queryFn: () => fetchPriceEvents(params),
		staleTime: 5 * 60 * 1000,
		enabled: !!params.stockCode && params.stockCode.length === 6,
	});
}
