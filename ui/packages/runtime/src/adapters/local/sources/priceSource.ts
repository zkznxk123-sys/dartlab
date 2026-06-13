// 로컬 price 포트 — /api/dartlab/price-events 의 OHLC → Candle[]. (ui/web 브리지 candlesFromPrice 포팅,
// 단 합성 캔들 fallback 제거 — 빈 응답은 [] 정직 표기, initial 은 null 반환.)
import type { Candle, CompanyPrices, PricePort } from '@dartlab/ui-contracts';
import { getJson } from '../fetchJson';
import type { LocalCaches, PriceEventsPayload } from '../localTypes';

// price-events 1회 fetch 공유 (price·filing 포트가 같은 응답 소비) — disclosure 소스만, shock/regime 미요청.
export function loadPriceEvents(
	apiBase: string,
	caches: LocalCaches,
	code: string
): Promise<PriceEventsPayload | null> {
	const c = code.trim();
	let p = caches.priceEvents.get(c);
	if (!p) {
		const qs = new URLSearchParams({
			stockCode: c,
			market: 'KR',
			sources: 'disclosure',
			discType: 'all',
			includeShocks: 'false',
			includeRegime: 'false'
		});
		p = getJson<PriceEventsPayload>(apiBase, `/api/dartlab/price-events?${qs.toString()}`);
		caches.priceEvents.set(c, p);
	}
	return p;
}

function compactDate(d: Date): string {
	return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

function ymdFromTs(ts: number): string {
	const ms = ts > 10_000_000_000 ? ts : ts * 1000;
	const d = new Date(ms);
	if (!Number.isFinite(d.getTime())) return '';
	return compactDate(d);
}

function candlesFromEvents(payload: PriceEventsPayload | null): Candle[] {
	return (payload?.ohlc ?? [])
		.map((row): Candle | null => {
			const ts = row[0] ?? 0;
			const o = row[1] ?? 0;
			const h = row[2] ?? 0;
			const l = row[3] ?? 0;
			const c = row[4] ?? 0;
			const v = row[5] ?? 0;
			const t = ymdFromTs(ts);
			if (!t || !Number.isFinite(c) || c <= 0) return null;
			return { t, o: o || c, h: h || c, l: l || c, c, v: v || 0 };
		})
		.filter((x): x is Candle => x != null)
		.sort((a, b) => a.t.localeCompare(b.t));
}

export function localPricePort(apiBase: string, caches: LocalCaches): PricePort {
	const candlesFor = async (code: string): Promise<Candle[]> => {
		const payload = await loadPriceEvents(apiBase, caches, code);
		const candles = candlesFromEvents(payload);
		caches.loadedCandles.set(code.trim(), candles);
		return candles;
	};
	return {
		async initial(code, year) {
			const candles = await candlesFor(code);
			if (!candles.length) return null;
			const oldestYear = Math.min(year - 1, Number(candles[0]?.t.slice(0, 4)) || year);
			return { candles, oldestYear } satisfies CompanyPrices;
		},
		// 로컬 서버는 연도별 추가 로드 API 없음 — 1회 price-events 가 전 구간(365일). 해당 없음 = [].
		async older() {
			return [];
		},
		// 동기 계약 — initial/govCandles 가 적재한 캐시 동기 반환. 미로드는 [].
		loaded(code) {
			return caches.loadedCandles.get(code.trim()) ?? [];
		},
		async govCandles(code) {
			const candles = await candlesFor(code);
			return candles.length ? candles : null;
		},
		// 전 종목 최근 캔들 묶음 — 로컬 단일회사 fetch 모델이라 미지원. null = 미지원 정직 표기.
		async govRecent() {
			return null;
		}
	};
}
