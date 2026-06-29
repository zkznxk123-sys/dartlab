// dartlab 푸시 허브 Worker — 웹푸시 구독 저장 + 발행 알림 발송만. 크롤·판정·요약 0(허브는 thin).
//
// 원칙([04] non-goal, [06] 상세설계):
// - D1 = 2테이블(subscriptions·topicSubs) + sentNonce. user_id·종목·개인조건 컬럼 영구 0.
// - 순수 WebCrypto(npm 0): VAPID JWT ES256 + aes128gcm 본문 암호화(RFC 8291 §3.4).
// - /send 는 러너 전용(Bearer + 결정적 nonce, CORS 없음). /subscribe 는 무인증 공개(SSRF host allowlist).
// - 발송 = JOIN 1회 대상조회 + Promise.allSettled 청크(직렬 금지) + 404/410 끝-일괄 batch purge.

const TOPIC_ALLOWLIST = new Set(['blogPublish', 'cardPublish']); // newOrders 제외 — P2 scan.orders 졸업 후
const PUSH_HOSTS = new Set(['fcm.googleapis.com', 'web.push.apple.com']); // mozilla 는 서브도메인(아래 별처리)
const B64URL_OK = /^[A-Za-z0-9_-]+={0,2}$/; // padding 허용(sub.toJSON().keys 정합, [07] §3)
const NONCE_WINDOW_S = 300;
const JWT_TTL_S = 12 * 60 * 60;
const PUSH_TTL_S = 4 * 24 * 60 * 60;
const SEND_CHUNK = 20; // allSettled 청크 — CF subrequest 50/req·push per-conn 한도 존중

const enc = new TextEncoder();
const nowSec = () => Math.floor(Date.now() / 1000);

// ── base64url ───────────────────────────────────────────────────────────────
function b64urlToBytes(s) {
	const pad = '='.repeat((4 - (s.length % 4)) % 4);
	const b64 = (s + pad).replace(/-/g, '+').replace(/_/g, '/');
	const bin = atob(b64);
	const out = new Uint8Array(bin.length);
	for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
	return out;
}
function bytesToB64url(input) {
	const arr = input instanceof Uint8Array ? input : new Uint8Array(input);
	let bin = '';
	for (let i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
	return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const b64urlStr = (str) => bytesToB64url(enc.encode(str));

function concatBytes(...parts) {
	let len = 0;
	for (const p of parts) len += p.length;
	const out = new Uint8Array(len);
	let off = 0;
	for (const p of parts) {
		out.set(p, off);
		off += p.length;
	}
	return out;
}

function timingSafeEqual(a, b) {
	const ab = enc.encode(a);
	const bb = enc.encode(b);
	if (ab.length !== bb.length) return false;
	let diff = 0;
	for (let i = 0; i < ab.length; i++) diff |= ab[i] ^ bb[i];
	return diff === 0;
}

async function hmacSha256(keyBytes, msgBytes) {
	const key = await crypto.subtle.importKey('raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
	return new Uint8Array(await crypto.subtle.sign('HMAC', key, msgBytes));
}

// ── VAPID JWT ES256 (npm 0 — crypto.subtle.sign 의 P1363 raw 64B = JWS ES256) ──
async function getVapidPrivKey(env) {
	const der = b64urlToBytes(env.VAPID_PRIVATE_KEY); // pkcs8 DER 의 base64url
	return crypto.subtle.importKey('pkcs8', der, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
}
async function makeVapidJwt(audOrigin, env, privKey) {
	const header = b64urlStr(JSON.stringify({ typ: 'JWT', alg: 'ES256' }));
	const payload = b64urlStr(JSON.stringify({ aud: audOrigin, exp: nowSec() + JWT_TTL_S, sub: env.VAPID_SUBJECT }));
	const input = `${header}.${payload}`;
	const sig = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, privKey, enc.encode(input));
	return `${input}.${bytesToB64url(new Uint8Array(sig))}`; // sig = P1363 raw 64B, DER 변환 0
}

// ── aes128gcm 본문 암호화 (RFC 8291 §3.4 2단계 HKDF — web-push WebCrypto 포팅) ──
// 평문 = JSON.stringify(notification 서브객체 {title,body,url,tag}). 07 §1 push 핸들러 event.data.json() 이 받음.
async function encryptPayload(p256dhB64, authB64, plaintext) {
	const uaPublic = b64urlToBytes(p256dhB64); // 구독 공개키 raw 65B
	const authSecret = b64urlToBytes(authB64); // auth_secret 16B
	const salt = crypto.getRandomValues(new Uint8Array(16));

	const asKeys = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
	const asPublic = new Uint8Array(await crypto.subtle.exportKey('raw', asKeys.publicKey)); // 65B
	const uaKey = await crypto.subtle.importKey('raw', uaPublic, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
	const ecdh = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: uaKey }, asKeys.privateKey, 256)); // 32B

	// 1단계: auth_secret 로 extract → keyinfo 로 expand → IKM
	const prkKey = await hmacSha256(authSecret, ecdh);
	const keyInfo = concatBytes(enc.encode('WebPush: info'), new Uint8Array([0]), uaPublic, asPublic);
	const ikm = (await hmacSha256(prkKey, concatBytes(keyInfo, new Uint8Array([1])))).slice(0, 32);

	// 2단계: salt(랜덤16B) 로 extract → CEK·NONCE 로 expand (salt 가 auth 가 아님에 주의)
	const prk = await hmacSha256(salt, ikm);
	const cek = (await hmacSha256(prk, concatBytes(enc.encode('Content-Encoding: aes128gcm'), new Uint8Array([0, 1])))).slice(0, 16);
	const nonce = (await hmacSha256(prk, concatBytes(enc.encode('Content-Encoding: nonce'), new Uint8Array([0, 1])))).slice(0, 12);

	const cekKey = await crypto.subtle.importKey('raw', cek, { name: 'AES-GCM' }, false, ['encrypt']);
	const record = concatBytes(enc.encode(plaintext), new Uint8Array([2])); // 0x02 = 단일 record delimiter
	const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce, tagLength: 128 }, cekKey, record));

	// RFC8188 헤더 + 본문: salt[16] || rs[4]=uint32(4096) || idlen[1]=65 || keyid=as_pub[65] || record
	const rs = new Uint8Array([0, 0, 0x10, 0x00]); // 4096 BE
	const idlen = new Uint8Array([65]);
	return concatBytes(salt, rs, idlen, asPublic, ciphertext);
}

async function sendOne(sub, plaintext, jwtByOrigin, env, privKey) {
	const origin = new URL(sub.endpoint).origin;
	if (!jwtByOrigin[origin]) jwtByOrigin[origin] = await makeVapidJwt(origin, env, privKey); // origin별 1회 메모
	const body = await encryptPayload(sub.p256dh, sub.auth, plaintext);
	const res = await fetch(sub.endpoint, {
		method: 'POST',
		headers: {
			TTL: String(PUSH_TTL_S),
			'Content-Encoding': 'aes128gcm',
			'Content-Type': 'application/octet-stream',
			Urgency: 'normal',
			Authorization: `vapid t=${jwtByOrigin[origin]}, k=${env.VAPID_PUBLIC_KEY}`
		},
		body
	});
	return res.status;
}

// ── CORS (siteSignals 형판) ───────────────────────────────────────────────────
function allowedOrigins(env) {
	return String(env.ALLOW_ORIGIN || '')
		.split(',')
		.map((o) => o.trim())
		.filter(Boolean);
}
function corsHeaders(req, env) {
	const origins = allowedOrigins(env);
	const origin = req.headers.get('Origin');
	const allowOrigin = origins.length && origin && origins.includes(origin) ? origin : origins[0] || '*';
	return {
		'Access-Control-Allow-Origin': allowOrigin,
		'Access-Control-Allow-Methods': 'POST, DELETE, OPTIONS',
		'Access-Control-Allow-Headers': 'Content-Type',
		Vary: 'Origin'
	};
}
const textRes = (msg, status, cors) => new Response(msg, { status, headers: cors });
function jsonRes(obj, cors) {
	return new Response(JSON.stringify(obj), { headers: { ...(cors || {}), 'Content-Type': 'application/json' } });
}

function isAllowedEndpoint(endpoint) {
	if (typeof endpoint !== 'string' || !endpoint) return false;
	let u;
	try {
		u = new URL(endpoint);
	} catch {
		return false;
	}
	if (u.protocol !== 'https:') return false;
	const h = u.hostname;
	return PUSH_HOSTS.has(h) || h.endsWith('.push.services.mozilla.com');
}
function classifyUa(endpoint) {
	const h = new URL(endpoint).hostname;
	if (h === 'web.push.apple.com') return 'apple';
	if (h === 'fcm.googleapis.com') return 'fcm';
	if (h.endsWith('.push.services.mozilla.com')) return 'mozilla';
	return 'other';
}

// ── 라우트 핸들러 ──────────────────────────────────────────────────────────────
async function handleSubscribe(req, env, cors) {
	let body;
	try {
		body = await req.json();
	} catch {
		return textRes('bad json', 400, cors);
	}
	const { endpoint, keys, topics } = body || {};
	if (!isAllowedEndpoint(endpoint)) return textRes('invalid endpoint', 422, cors);
	if (!keys || !B64URL_OK.test(keys.p256dh || '') || !B64URL_OK.test(keys.auth || '')) return textRes('invalid keys', 422, cors);
	const topicList = Array.isArray(topics) ? topics.filter((t) => TOPIC_ALLOWLIST.has(t)) : [];
	if (!topicList.length) return textRes('no valid topics', 422, cors);

	const now = new Date().toISOString();
	const uaClass = classifyUa(endpoint);
	// 멱등 단일효과: subscriptions UPSERT + topicSubs 전량 교체(DELETE + INSERT OR IGNORE). batch 원자성 비의존([06] §6).
	await env.PUSHHUB_DB.batch([
		env.PUSHHUB_DB.prepare(
			`INSERT INTO subscriptions (endpoint, p256dh, auth, uaClass, createdAt, lastSeenAt) VALUES (?, ?, ?, ?, ?, ?)
			 ON CONFLICT(endpoint) DO UPDATE SET p256dh = excluded.p256dh, auth = excluded.auth, lastSeenAt = excluded.lastSeenAt`
		).bind(endpoint, keys.p256dh, keys.auth, uaClass, now, now),
		env.PUSHHUB_DB.prepare(`DELETE FROM topicSubs WHERE endpoint = ?`).bind(endpoint),
		...topicList.map((t) =>
			env.PUSHHUB_DB.prepare(`INSERT OR IGNORE INTO topicSubs (endpoint, topic, subscribedAt) VALUES (?, ?, ?)`).bind(endpoint, t, now)
		)
	]);
	return textRes('ok', 200, cors);
}

async function handleDelete(req, env, cors) {
	let body;
	try {
		body = await req.json();
	} catch {
		return textRes('bad json', 400, cors);
	}
	const { endpoint, topics } = body || {};
	if (typeof endpoint !== 'string' || !endpoint) return textRes('endpoint required', 422, cors);

	if (Array.isArray(topics) && topics.length) {
		// 부분해지 — 지정 토픽만 제거. 남은 토픽 0 이면 subscription 도 삭제.
		const ph = topics.map(() => '?').join(',');
		await env.PUSHHUB_DB.prepare(`DELETE FROM topicSubs WHERE endpoint = ? AND topic IN (${ph})`).bind(endpoint, ...topics).run();
		const remain = await env.PUSHHUB_DB.prepare(`SELECT COUNT(*) AS n FROM topicSubs WHERE endpoint = ?`).bind(endpoint).first();
		if (!remain || remain.n === 0) {
			await env.PUSHHUB_DB.prepare(`DELETE FROM subscriptions WHERE endpoint = ?`).bind(endpoint).run();
		}
	} else {
		// 전체삭제 — subscriptions 1줄, topicSubs 는 FK CASCADE 자동([06] §2).
		await env.PUSHHUB_DB.prepare(`DELETE FROM subscriptions WHERE endpoint = ?`).bind(endpoint).run();
	}
	return textRes('ok', 200, cors);
}

async function handleSend(req, env) {
	// (1) Bearer — 발송 권한(상수시간 비교)
	const auth = req.headers.get('Authorization') || '';
	if (!timingSafeEqual(auth, `Bearer ${env.PUSHHUB_SEND_TOKEN}`)) return new Response('unauthorized', { status: 401 });

	// (2) nonce + ts 윈도 — replay 창 닫기(서명 없음)
	const nonce = req.headers.get('X-DL-Nonce') || '';
	const ts = parseInt(req.headers.get('X-DL-Ts') || '0', 10);
	if (!nonce) return new Response('nonce required', { status: 400 });
	const now = nowSec();
	if (!ts || Math.abs(now - ts) > NONCE_WINDOW_S) return new Response('stale', { status: 401 });
	try {
		await env.PUSHHUB_DB.prepare(`INSERT INTO sentNonce (nonce, ts) VALUES (?, ?)`).bind(nonce, now).run();
	} catch {
		return new Response('replay', { status: 409 }); // PK 충돌 = (topic,slug) 멱등
	}

	let body;
	try {
		body = await req.json();
	} catch {
		return new Response('bad json', { status: 400 });
	}
	const notification = body && body.notification;
	if (!notification || typeof notification !== 'object') return new Response('notification required', { status: 422 });
	const plaintext = JSON.stringify(notification); // {title,body,url,tag} 서브객체만(봉투 아님)

	// 대상 조회 = JOIN 1회(N+1 금지) 또는 endpoints[] 타겟
	let rows;
	if (Array.isArray(body.endpoints) && body.endpoints.length) {
		const ph = body.endpoints.map(() => '?').join(',');
		rows = (await env.PUSHHUB_DB.prepare(`SELECT endpoint, p256dh, auth FROM subscriptions WHERE endpoint IN (${ph})`).bind(...body.endpoints).all()).results;
	} else if (typeof body.topic === 'string' && body.topic) {
		rows = (
			await env.PUSHHUB_DB.prepare(
				`SELECT s.endpoint, s.p256dh, s.auth FROM topicSubs t JOIN subscriptions s ON s.endpoint = t.endpoint WHERE t.topic = ?`
			)
				.bind(body.topic)
				.all()
		).results;
	} else {
		return new Response('topic or endpoints required', { status: 422 });
	}

	const jwtByOrigin = {}; // origin별 JWT 1회 메모(push origin 3개뿐)
	let sent = 0;
	let failed = 0;
	const toPurge = [];
	// 대상 0이면 VAPID 키 import 건너뜀 — 불필요 작업 제거 + 무구독 발송이 정상 no-op(sent:0).
	const privKey = rows.length ? await getVapidPrivKey(env) : null;
	for (let i = 0; i < rows.length; i += SEND_CHUNK) {
		const chunk = rows.slice(i, i + SEND_CHUNK);
		const settled = await Promise.allSettled(chunk.map((sub) => sendOne(sub, plaintext, jwtByOrigin, env, privKey)));
		settled.forEach((r, j) => {
			if (r.status === 'fulfilled') {
				const code = r.value;
				if (code >= 200 && code < 300) sent++;
				else if (code === 404 || code === 410) toPurge.push(chunk[j].endpoint);
				else failed++; // 429/5xx = 보존
			} else {
				failed++;
			}
		});
	}

	let pruned = 0;
	if (toPurge.length) {
		const ph = toPurge.map(() => '?').join(',');
		await env.PUSHHUB_DB.prepare(`DELETE FROM subscriptions WHERE endpoint IN (${ph})`).bind(...toPurge).run(); // CASCADE 가 topicSubs 정리
		pruned = toPurge.length;
	}
	return jsonRes({ sent, pruned, failed });
}

export default {
	async fetch(req, env) {
		const path = new URL(req.url).pathname;

		if (path === '/subscribe') {
			const cors = corsHeaders(req, env);
			if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
			if (!env.PUSHHUB_DB) return textRes('db not configured', 503, cors);
			if (req.method === 'POST') return handleSubscribe(req, env, cors);
			if (req.method === 'DELETE') return handleDelete(req, env, cors);
			return textRes('method not allowed', 405, cors);
		}

		if (path === '/send') {
			// server-to-server — CORS·OPTIONS 없음
			if (req.method !== 'POST') return new Response('method not allowed', { status: 405 });
			if (!env.PUSHHUB_DB) return new Response('db not configured', { status: 503 });
			return handleSend(req, env);
		}

		return new Response('not found', { status: 404 });
	}
};
