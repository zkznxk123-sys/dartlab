// /send 회귀 — 인증(Bearer/nonce/ts) · 입력검증 · fan-out/purge. SHIP 게이트 9 시나리오.
// ⚠ 하네스 미스캐폴드면 미실행(TEST_SCAFFOLD.md). fan-out/purge 는 push 엔드포인트 outbound 를 fetchMock 으로
//    가로채야 한다 — 설치한 vitest-pool-workers 의 fetchMock API 로 맞춘다(버전별 상이).
import { env, SELF } from 'cloudflare:test';
import { beforeEach, describe, it, expect } from 'vitest';

const TOKEN = 'test-send-token'; // wrangler.toml/test env 의 PUSHHUB_SEND_TOKEN 와 일치시킬 것
const notification = { title: '[새 글] 테스트', body: '본문', url: '/blog/x', tag: 'blog:x' };

function headers({ token = TOKEN, nonce = 'n1', ts = Math.floor(Date.now() / 1000) } = {}) {
	const h = { 'Content-Type': 'application/json' };
	if (token !== null) h['Authorization'] = `Bearer ${token}`;
	if (nonce !== null) h['X-DL-Nonce'] = nonce;
	if (ts !== null) h['X-DL-Ts'] = String(ts);
	return h;
}
function send(body, opts) {
	return SELF.fetch('https://hub.test/send', { method: 'POST', headers: headers(opts), body: JSON.stringify(body) });
}

beforeEach(async () => {
	await env.PUSHHUB_DB.batch([
		env.PUSHHUB_DB.prepare('DELETE FROM topicSubs'),
		env.PUSHHUB_DB.prepare('DELETE FROM subscriptions'),
		env.PUSHHUB_DB.prepare('DELETE FROM sentNonce')
	]);
});

describe('POST /send 인증', () => {
	it('Bearer 누락 → 401', async () => {
		const res = await send({ topic: 'blogPublish', notification }, { token: null });
		expect(res.status).toBe(401);
	});
	it('Bearer 오류 → 401', async () => {
		const res = await send({ topic: 'blogPublish', notification }, { token: 'wrong' });
		expect(res.status).toBe(401);
	});
	it('nonce 누락 → 400', async () => {
		const res = await send({ topic: 'blogPublish', notification }, { nonce: null });
		expect(res.status).toBe(400);
	});
	it('ts 윈도 초과 → 401', async () => {
		const res = await send({ topic: 'blogPublish', notification }, { ts: Math.floor(Date.now() / 1000) - 9999 });
		expect(res.status).toBe(401);
	});
	it('nonce replay → 409', async () => {
		const first = await send({ topic: 'blogPublish', notification }, { nonce: 'dup' });
		expect(first.status).toBe(200);
		const replay = await send({ topic: 'blogPublish', notification }, { nonce: 'dup' });
		expect(replay.status).toBe(409);
	});
	it('notification 누락 → 422', async () => {
		const res = await send({ topic: 'blogPublish' }, { nonce: 'n-no-notif' });
		expect(res.status).toBe(422);
	});
	it('topic·endpoints 둘 다 없음 → 422', async () => {
		const res = await send({ notification }, { nonce: 'n-no-target' });
		expect(res.status).toBe(422);
	});
});

describe('POST /send fan-out (구독 0 = no-op)', () => {
	it('구독 없는 토픽 → 200 sent=0 (정상 no-op)', async () => {
		const res = await send({ topic: 'blogPublish', notification }, { nonce: 'n-empty' });
		expect(res.status).toBe(200);
		expect(await res.json()).toMatchObject({ sent: 0, pruned: 0, failed: 0 });
	});

	// fan-out + 404/410 purge: push 엔드포인트 outbound 를 fetchMock 으로 가로채 201/410 을 흉내내고,
	// 응답 {sent,pruned,failed} 집계와 purge 후 subscriptions 행 삭제를 검증한다.
	// 구현 시 설치한 vitest-pool-workers fetchMock 으로 작성([08] §5 발송 동시성·purge).
	it.todo('410 endpoint 는 purge 되고 201 은 sent 집계');
});
