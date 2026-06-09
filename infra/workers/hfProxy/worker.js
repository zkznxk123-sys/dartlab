// HF 데이터셋 parquet 레인지 프록시 Cloudflare Worker (무료 티어).
//
// 정적 프런트(GitHub Pages)는 HF `resolve/main` 을 직접 range-fetch 한다. 콜드 HF CDN 은 엣지
// 캐시 미스 시 간헐 403/429/5xx 를 돌려주는데(프런트 로그에 'Failed to load resource: 403'),
// 이 Worker 가 그 사이에서:
//   1) 403/429/5xx 를 엣지에서 재시도 흡수 (프런트 fetchResilient 와 이중 방어, 서버측이라 왕복 빠름),
//   2) HF resolve/main URL 을 단일 SSOT 로 — 프런트는 VITE_DARTLAB_HF_RESOLVE=https://<worker>/hf 한 줄로 전체 전환,
//   3) CF 글로벌 네트워크 경로로 first-byte 개선.
//
// hyparquet 이 의존하는 헤더(Range / Content-Range / Accept-Ranges / Content-Length / x-linked-size / 206)
// 를 그대로 보존·재발급한다 (landing/src/lib/data/hfRange.ts 가 이 헤더로 파일 크기·청크를 읽음).
//
// 캐싱 정책: 레인지(206) 응답은 *브라우저 캐시* 에 맡긴다(URL+Range 키로 정확). 부분응답을 CF Cache API
// 에 직접 put 하면 잘못된 바이트를 돌려줄 위험이 있어 하지 않는다. parquet 은 파이프라인이 새 파일로
// 교체하므로 사실상 immutable → 장기 브라우저 캐시 안전. (후속 확장: 작은 인덱스 parquet 만 R2 미러.)
//
// 무료 티어: Workers 10만 req/day. nodejs_compat 불필요(순수 fetch). 배포·전환은 README.md.

const UPSTREAM = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
const PASS_HEADERS = ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'ETag', 'Last-Modified', 'x-linked-size'];

export default {
	async fetch(req, env) {
		// CORS allowlist: 프로덕션 origin(env.ALLOW_ORIGIN) + 로컬 dev(localhost/127.0.0.1). 일치 시 그 origin echo.
		const reqOrigin = req.headers.get('Origin') || '';
		const allowOrigin =
			reqOrigin && (reqOrigin === env.ALLOW_ORIGIN || /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(reqOrigin))
				? reqOrigin
				: env.ALLOW_ORIGIN || '*';
		const cors = {
			'Access-Control-Allow-Origin': allowOrigin,
			'Vary': 'Origin',
			'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
			'Access-Control-Allow-Headers': 'Range, If-Range, If-None-Match',
			'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges, ETag, x-linked-size',
			'Access-Control-Max-Age': '86400'
		};
		if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
		if (req.method !== 'GET' && req.method !== 'HEAD') return new Response('method not allowed', { status: 405, headers: cors });

		const url = new URL(req.url);
		const m = url.pathname.match(/^\/hf\/(.+)$/);
		if (!m) return new Response('not found — use /hf/<dataset-path>', { status: 404, headers: cors });
		const path = m[1].replace(/^\/+/, '').replace(/\.\.+/g, ''); // 경로 정규화 (상위 디렉터리 탈출 차단)
		const upstreamUrl = `${UPSTREAM}/${path}`;

		const fwd = new Headers();
		const range = req.headers.get('Range'); if (range) fwd.set('Range', range);
		const ifRange = req.headers.get('If-Range'); if (ifRange) fwd.set('If-Range', ifRange);
		const inm = req.headers.get('If-None-Match'); if (inm) fwd.set('If-None-Match', inm);

		let up = null;
		for (let attempt = 0; attempt < 4; attempt++) {
			up = await fetch(upstreamUrl, { method: req.method, headers: fwd });
			if (up.ok || up.status === 206 || up.status === 304) break;
			if (up.status !== 403 && up.status !== 429 && up.status < 500) break;
			await new Promise((r) => setTimeout(r, 180 * (attempt + 1)));
		}

		const h = new Headers();
		for (const k of PASS_HEADERS) { const v = up.headers.get(k); if (v) h.set(k, v); }
		if (!h.has('Accept-Ranges')) h.set('Accept-Ranges', 'bytes');
		// x-linked-size: HF LFS 실제 파일 크기. 없으면 Content-Range 총길이 또는 200 의 Content-Length 로 보강.
		if (!h.has('x-linked-size')) {
			const cr = h.get('Content-Range');
			const total = cr ? cr.split('/')[1] : null;
			if (total && total !== '*') h.set('x-linked-size', total);
			else if (up.status === 200 && h.get('Content-Length')) h.set('x-linked-size', h.get('Content-Length'));
		}
		h.set('Cache-Control', 'public, max-age=86400');
		for (const [k, v] of Object.entries(cors)) h.set(k, v);

		return new Response(req.method === 'HEAD' ? null : up.body, { status: up.status, headers: h });
	}
};
