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
// 캐싱 정책 2층:
//   - 레인지(206) 응답은 *브라우저 캐시* 에 맡긴다(URL+Range 키로 정확). 부분응답 CF Cache put 금지.
//   - 전체 GET(Range 없음 — 프론트 소형 parquet 통파일 경로)은 *엣지 캐시*(caches.default) —
//     콜드 HF first-byte ~2s 를 글로벌 엣지 히트 수십 ms 로. TTL 은 파일 갱신 주기별
//     (recent.parquet 10분[일일 갱신 tail] / 그 외 1시간).
//
// 무료 티어: Workers 10만 req/day. nodejs_compat 불필요(순수 fetch). 배포·전환은 README.md.

const UPSTREAM = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
const PASS_HEADERS = ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'ETag', 'Last-Modified', 'x-linked-size'];

function cacheControlFor(path) {
	if (path.endsWith('recent.parquet')) return 'public, max-age=600';
	return 'public, max-age=3600';
}

export default {
	async fetch(req, env, ctx) {
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

		// /naver?code=XXXXXX — 네이버 fchart 일별 OHLCV 프록시. gov(공공데이터, T+1 영업일 지연)가 아직
		// 발행 안 한 최신 거래일(금요일치=월요일 발행)을 프론트가 표시용 fresh-tail 로 채우게 한다. 정적
		// 사이트는 브라우저 CORS 로 네이버를 직접 못 부르므로 서버측(엣지) fetch 가 우회. 키 불필요(공개
		// 차트 API), 재배포 아님(사용자 세션 표시용). 10분 캐시 — EOD 갭 채움이라 분 단위 신선도면 충분.
		if (url.pathname === '/naver') {
			const jsonHeaders = { ...cors, 'Content-Type': 'application/json; charset=utf-8' };
			const code = (url.searchParams.get('code') || '').replace(/[^0-9A-Za-z]/g, '');
			if (!code) return new Response(JSON.stringify({ error: 'code required' }), { status: 400, headers: jsonHeaders });
			let txt = '';
			try {
				const fr = await fetch(
					`https://fchart.stock.naver.com/sise.nhn?symbol=${code}&timeframe=day&count=30&requestType=0`,
					{ headers: { 'User-Agent': 'Mozilla/5.0' } }
				);
				if (!fr.ok) throw new Error(`naver ${fr.status}`);
				txt = await fr.text(); // EUC-KR XML — data="..." 필드는 ASCII 라 regex 안전
			} catch (e) {
				return new Response(JSON.stringify({ error: String(e) }), { status: 502, headers: jsonHeaders });
			}
			const candles = [];
			for (const it of txt.matchAll(/data="([^"]+)"/g)) {
				const p = it[1].split('|');
				if (p.length < 6) continue;
				const c = Number(p[4]);
				if (!Number.isFinite(c) || c <= 0) continue;
				candles.push({ t: p[0], o: Number(p[1]) || c, h: Number(p[2]) || c, l: Number(p[3]) || c, c, v: Number(p[5]) || 0 });
			}
			candles.sort((a, b) => a.t.localeCompare(b.t));
			return new Response(
				JSON.stringify({ source: 'fchart.stock.naver.com', code, asOf: candles.at(-1)?.t ?? '', candles }),
				{ headers: { ...jsonHeaders, 'Cache-Control': 'public, max-age=600' } }
			);
		}
		const m = url.pathname.match(/^\/hf\/(.+)$/);
		if (!m) return new Response('not found — use /hf/<dataset-path>', { status: 404, headers: cors });
		const path = m[1].replace(/^\/+/, '').replace(/\.\.+/g, ''); // 경로 정규화 (상위 디렉터리 탈출 차단)
		const upstreamUrl = `${UPSTREAM}/${path}`;

		const fwd = new Headers();
		const range = req.headers.get('Range'); if (range) fwd.set('Range', range);
		const ifRange = req.headers.get('If-Range'); if (ifRange) fwd.set('If-Range', ifRange);
		const inm = req.headers.get('If-None-Match'); if (inm) fwd.set('If-None-Match', inm);

		// 전체 GET 엣지 캐시 조회 — 키는 업스트림 URL (Range/조건부 요청은 제외, 부분응답 오염 방지)
		const isFullGet = req.method === 'GET' && !range && !inm && !ifRange;
		const cacheKey = new Request(upstreamUrl);
		if (isFullGet) {
			const hit = await caches.default.match(cacheKey);
			if (hit) {
				const h2 = new Headers(hit.headers);
				for (const [k, v] of Object.entries(cors)) h2.set(k, v);
				h2.set('x-dl-edge', 'HIT');
				return new Response(hit.body, { status: hit.status, headers: h2 });
			}
		}

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
		h.set('Cache-Control', cacheControlFor(path));
		for (const [k, v] of Object.entries(cors)) h.set(k, v);

		const resp = new Response(req.method === 'HEAD' ? null : up.body, { status: up.status, headers: h });
		if (isFullGet && up.status === 200 && ctx) ctx.waitUntil(caches.default.put(cacheKey, resp.clone()));
		return resp;
	}
};
