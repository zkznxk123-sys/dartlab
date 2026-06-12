// 사이트 신호 수집 Worker — 공개 문서 사이트의 사용성 신호를 D1 counter로만 누적한다.
//
// 원칙:
// - 원시 이벤트 로그를 append 저장하지 않는다.
// - 원시 IP, User-Agent 원문, 세션 ID, 검색어/입력값을 저장하지 않는다.
// - allowlist 이벤트만 받는다.
// - D1에는 일자 × path × eventName × bucket × target counter만 증가시킨다.

const ALLOWED_EVENTS = new Set(['pageView', 'dwell', 'scrollDepth', 'ctaClick', 'viewerOpen', 'dataDownload']);
const ALLOWED_DWELL_BUCKETS = new Set(['0-10s', '10-30s', '30-120s', '120s+']);
const ALLOWED_SCROLL_BUCKETS = new Set(['25', '50', '75', '100']);
const MAX_PATH_LEN = 160;
const MAX_TARGET_LEN = 80;

function allowedOrigins(env) {
	return String(env.ALLOW_ORIGIN || '')
		.split(',')
		.map((origin) => origin.trim())
		.filter(Boolean);
}

function isOriginAllowed(req, env) {
	const origins = allowedOrigins(env);
	if (!origins.length) return true;
	const origin = req.headers.get('Origin');
	return !origin || origins.includes(origin);
}

function corsHeaders(req, env) {
	const origins = allowedOrigins(env);
	const origin = req.headers.get('Origin');
	const allowOrigin = origins.length && origin && origins.includes(origin) ? origin : origins[0] || '*';
	return {
		'Access-Control-Allow-Origin': allowOrigin,
		'Access-Control-Allow-Methods': 'POST, OPTIONS',
		'Access-Control-Allow-Headers': 'Content-Type',
		'Vary': 'Origin'
	};
}

function normalizePath(value) {
	const raw = String(value ?? '').trim();
	if (!raw || raw.length > MAX_PATH_LEN) return null;
	let pathname = raw;
	try {
		pathname = new URL(raw, 'https://eddmpython.github.io').pathname;
	} catch {
		pathname = raw.split('?')[0].split('#')[0];
	}
	if (!pathname.startsWith('/')) pathname = `/${pathname}`;
	if (pathname.includes('..')) return null;
	return pathname.slice(0, MAX_PATH_LEN);
}

function normalizeTarget(value) {
	const text = String(value ?? '').trim();
	if (!text) return '';
	return text.replace(/[^가-힣A-Za-z0-9._:/-]/g, '').slice(0, MAX_TARGET_LEN);
}

function normalizeBucket(eventName, value) {
	const bucket = String(value ?? '').trim();
	if (!bucket) return '';
	if (eventName === 'dwell') return ALLOWED_DWELL_BUCKETS.has(bucket) ? bucket : null;
	if (eventName === 'scrollDepth') return ALLOWED_SCROLL_BUCKETS.has(bucket) ? bucket : null;
	return bucket.replace(/[^A-Za-z0-9._:-]/g, '').slice(0, 32);
}

function todayUtc() {
	return new Date().toISOString().slice(0, 10);
}

export default {
	async fetch(req, env) {
		const cors = corsHeaders(req, env);
		if (!isOriginAllowed(req, env)) return new Response('origin not allowed', { status: 403, headers: cors });
		if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
		if (req.method !== 'POST') return new Response('method not allowed', { status: 405, headers: cors });
		if (!env.SITE_SIGNALS_DB) return new Response('db not configured', { status: 503, headers: cors });

		let body;
		try {
			body = await req.json();
		} catch {
			return new Response('bad json', { status: 400, headers: cors });
		}

		const eventName = String(body?.eventName ?? '').trim();
		if (!ALLOWED_EVENTS.has(eventName)) return new Response('event not allowed', { status: 422, headers: cors });

		const path = normalizePath(body?.path);
		if (!path) return new Response('invalid path', { status: 422, headers: cors });

		const bucket = normalizeBucket(eventName, body?.bucket);
		if (bucket === null) return new Response('invalid bucket', { status: 422, headers: cors });

		const target = normalizeTarget(body?.target);
		const signalDate = todayUtc();
		const updatedAt = new Date().toISOString();

		try {
			await env.SITE_SIGNALS_DB.prepare(
				`INSERT INTO dailySignals (signalDate, path, eventName, bucket, target, count, updatedAt)
				 VALUES (?, ?, ?, ?, ?, 1, ?)
				 ON CONFLICT(signalDate, path, eventName, bucket, target)
				 DO UPDATE SET count = count + 1, updatedAt = excluded.updatedAt`
			)
				.bind(signalDate, path, eventName, bucket || '', target, updatedAt)
				.run();
		} catch {
			return new Response('db error', { status: 502, headers: cors });
		}

		return new Response('ok', { headers: cors });
	}
};
