// /subscribe 회귀 — SSRF allowlist · topic 필터 · UPSERT 멱등 · DELETE 부분/전체(CASCADE).
// ⚠ 하네스 미스캐폴드면 미실행(TEST_SCAFFOLD.md). 'cloudflare:test' import·migration 바인딩은 설치 버전에 맞춤.
import { env, SELF } from 'cloudflare:test';
import { beforeEach, describe, it, expect } from 'vitest';

const APPLE = 'https://web.push.apple.com/sub/abc';
const keys = { p256dh: 'BPa-test_key', auth: 'AAAA_auth' };

async function post(body) {
	return SELF.fetch('https://hub.test/subscribe', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

beforeEach(async () => {
	await env.PUSHHUB_DB.batch([
		env.PUSHHUB_DB.prepare('DELETE FROM topicSubs'),
		env.PUSHHUB_DB.prepare('DELETE FROM subscriptions'),
		env.PUSHHUB_DB.prepare('DELETE FROM sentNonce')
	]);
});

describe('POST /subscribe', () => {
	it('비-allowlist host 는 422 (SSRF 차단)', async () => {
		const res = await post({ endpoint: 'https://evil.example.com/x', keys, topics: ['blogPublish'] });
		expect(res.status).toBe(422);
	});

	it('allowlist 밖 topic 은 필터되어 0개면 422', async () => {
		const res = await post({ endpoint: APPLE, keys, topics: ['hackerTopic'] });
		expect(res.status).toBe(422);
	});

	it('유효 구독 → 200 + subscriptions·topicSubs 적재', async () => {
		const res = await post({ endpoint: APPLE, keys, topics: ['blogPublish', 'cardPublish', 'nope'] });
		expect(res.status).toBe(200);
		const sub = await env.PUSHHUB_DB.prepare('SELECT uaClass FROM subscriptions WHERE endpoint=?').bind(APPLE).first();
		expect(sub.uaClass).toBe('apple');
		const topics = (await env.PUSHHUB_DB.prepare('SELECT topic FROM topicSubs WHERE endpoint=? ORDER BY topic').bind(APPLE).all()).results;
		expect(topics.map((t) => t.topic)).toEqual(['blogPublish', 'cardPublish']); // nope 필터됨
	});

	it('재구독 UPSERT 멱등 — 토픽 전량 교체', async () => {
		await post({ endpoint: APPLE, keys, topics: ['blogPublish', 'cardPublish'] });
		await post({ endpoint: APPLE, keys, topics: ['blogPublish'] }); // 줄임
		const topics = (await env.PUSHHUB_DB.prepare('SELECT topic FROM topicSubs WHERE endpoint=?').bind(APPLE).all()).results;
		expect(topics.map((t) => t.topic)).toEqual(['blogPublish']);
		const count = await env.PUSHHUB_DB.prepare('SELECT COUNT(*) AS n FROM subscriptions WHERE endpoint=?').bind(APPLE).first();
		expect(count.n).toBe(1); // 중복 row 0
	});
});

describe('DELETE /subscribe', () => {
	async function del(body) {
		return SELF.fetch('https://hub.test/subscribe', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
	}

	it('전체삭제 → subscriptions 1줄 + topicSubs CASCADE', async () => {
		await post({ endpoint: APPLE, keys, topics: ['blogPublish', 'cardPublish'] });
		expect((await del({ endpoint: APPLE })).status).toBe(200);
		const sub = await env.PUSHHUB_DB.prepare('SELECT COUNT(*) AS n FROM subscriptions WHERE endpoint=?').bind(APPLE).first();
		const top = await env.PUSHHUB_DB.prepare('SELECT COUNT(*) AS n FROM topicSubs WHERE endpoint=?').bind(APPLE).first();
		expect(sub.n).toBe(0);
		expect(top.n).toBe(0); // CASCADE
	});

	it('부분해지 → 지정 토픽만, 남으면 subscription 유지', async () => {
		await post({ endpoint: APPLE, keys, topics: ['blogPublish', 'cardPublish'] });
		await del({ endpoint: APPLE, topics: ['cardPublish'] });
		const top = (await env.PUSHHUB_DB.prepare('SELECT topic FROM topicSubs WHERE endpoint=?').bind(APPLE).all()).results;
		expect(top.map((t) => t.topic)).toEqual(['blogPublish']);
		const sub = await env.PUSHHUB_DB.prepare('SELECT COUNT(*) AS n FROM subscriptions WHERE endpoint=?').bind(APPLE).first();
		expect(sub.n).toBe(1);
	});

	it('부분해지로 토픽 0 되면 subscription 도 삭제', async () => {
		await post({ endpoint: APPLE, keys, topics: ['blogPublish'] });
		await del({ endpoint: APPLE, topics: ['blogPublish'] });
		const sub = await env.PUSHHUB_DB.prepare('SELECT COUNT(*) AS n FROM subscriptions WHERE endpoint=?').bind(APPLE).first();
		expect(sub.n).toBe(0);
	});
});
