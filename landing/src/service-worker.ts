/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * dartlab Service Worker — HF parquet 캐시 (PR-α).
 *
 * 책임:
 *   1. HF dataset URL prefix (https://huggingface.co/datasets/eddmpython/dartlab-data/) intercept
 *   2. cache-first + stale-while-revalidate (TTL 6h)
 *   3. Range request 도 cache slice 로 응답 — DuckDB-WASM 의 partial parquet read 가속
 *   4. Same-origin static asset 은 통과 (SvelteKit 가 알아서 처리)
 *
 * 효과:
 *   - 첫 방문: HF parquet full prefetch (50~100MB) → Cache Storage
 *   - 재방문: Cache hit, network 0
 *   - DuckDB-WASM Range 요청 → SW 가 cache 의 full Response 에서 slice 응답 (200ms → 5ms)
 *
 * SvelteKit 가 자동 register (kit.serviceWorker default = true). base path 자동 처리.
 */

declare const self: ServiceWorkerGlobalScope;

const CACHE_PARQUET = 'dartlab-scan-parquet-v1';
const TTL_MS = 6 * 60 * 60 * 1000;
const HF_PREFIX = 'https://huggingface.co/datasets/eddmpython/dartlab-data/';

self.addEventListener('install', (event) => {
	// 즉시 활성화 — 새 SW 가 기존 SW 대신 take over
	event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			// 오래된 dartlab-scan-* cache 삭제 (스키마 v2 등으로 bump 시 cleanup)
			const keys = await caches.keys();
			await Promise.all(
				keys
					.filter((k) => k.startsWith('dartlab-scan-') && k !== CACHE_PARQUET)
					.map((k) => caches.delete(k))
			);
			await self.clients.claim();
		})()
	);
});

self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	if (!req.url.startsWith(HF_PREFIX)) return;

	event.respondWith(handleHfRequest(req));
});

/** HF parquet 요청 처리 — Range request 도 cache 에서 slice. */
async function handleHfRequest(req: Request): Promise<Response> {
	const cache = await caches.open(CACHE_PARQUET);
	// cache key 는 Range 빠진 URL — full body 한 번만 저장.
	const fullKey = new Request(req.url, { method: 'GET' });
	let fullResp = await cache.match(fullKey);

	const isFresh = (resp: Response | undefined): boolean => {
		if (!resp) return false;
		const ts = Number(resp.headers.get('x-cache-ts')) || 0;
		return Date.now() - ts < TTL_MS;
	};

	// cache miss 또는 stale 이면 full prefetch
	if (!fullResp || !isFresh(fullResp)) {
		try {
			fullResp = await prefetchAndStore(cache, fullKey);
		} catch (err) {
			console.warn('[scan-sw] HF prefetch 실패 — passthrough', err);
			return fetch(req);
		}
	}

	// Range 요청 — cache 의 full body 에서 slice
	const rangeHeader = req.headers.get('range');
	if (rangeHeader && rangeHeader.startsWith('bytes=')) {
		return sliceRange(fullResp, rangeHeader);
	}

	// 풀 GET — cached response 그대로 (header 정리)
	return cleanResponse(fullResp);
}

async function prefetchAndStore(cache: Cache, fullKey: Request): Promise<Response> {
	const resp = await fetch(fullKey);
	if (!resp.ok) throw new Error(`HF ${resp.status} ${resp.statusText}`);

	// Response body 는 한번 read 하면 사라짐 — clone 후 metadata 추가하여 store.
	const buf = await resp.clone().arrayBuffer();
	const headers = new Headers(resp.headers);
	headers.set('x-cache-ts', String(Date.now()));
	headers.set('content-length', String(buf.byteLength));
	const stored = new Response(buf, {
		status: 200,
		statusText: 'OK',
		headers
	});
	try {
		await cache.put(fullKey, stored.clone());
	} catch (err) {
		// quota exceeded — 무시 (browser LRU 가 알아서 evict)
		console.warn('[scan-sw] cache put 실패 (quota?)', err);
	}
	return stored;
}

/** Range header 파싱 → cache 의 full body 에서 slice 응답. */
async function sliceRange(fullResp: Response, rangeHeader: string): Promise<Response> {
	const match = rangeHeader.match(/^bytes=(\d+)-(\d*)$/);
	if (!match) return cleanResponse(fullResp);

	const buf = await fullResp.clone().arrayBuffer();
	const total = buf.byteLength;
	const start = Number(match[1]);
	const end = match[2] === '' ? total - 1 : Math.min(Number(match[2]), total - 1);

	if (start >= total || start > end) {
		return new Response(null, {
			status: 416,
			statusText: 'Range Not Satisfiable',
			headers: { 'content-range': `bytes */${total}` }
		});
	}

	const sliced = buf.slice(start, end + 1);
	return new Response(sliced, {
		status: 206,
		statusText: 'Partial Content',
		headers: {
			'content-range': `bytes ${start}-${end}/${total}`,
			'content-length': String(sliced.byteLength),
			'accept-ranges': 'bytes',
			'access-control-allow-origin': '*'
		}
	});
}

/** Response 의 internal x-cache-ts 헤더 제거 후 clone. */
function cleanResponse(resp: Response): Response {
	const headers = new Headers(resp.headers);
	headers.delete('x-cache-ts');
	return new Response(resp.clone().body, {
		status: resp.status,
		statusText: resp.statusText,
		headers
	});
}

export {};
