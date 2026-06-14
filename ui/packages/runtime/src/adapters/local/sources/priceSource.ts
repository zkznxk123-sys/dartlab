// 로컬 price-events 소스 — /api/dartlab/price-events 의 disclosure 이벤트만 공급(비정기공시 레일).
// 주가 캔들 자체는 공개 gov HF 포트(publicPricePort)가 담당한다 — 로컬도 깃헙페이지 자산을 공유(백엔드 0).
import { getJson } from '../fetchJson';
import type { LocalCaches, PriceEventsPayload } from '../localTypes';

// price-events 1회 fetch 공유 (filing 포트가 비정기공시 이벤트로 소비) — disclosure 소스만, shock/regime 미요청.
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
