import { describe, it, expect } from 'vitest';
import { urlBase64ToUint8Array, serializeSubscription, DEFAULT_TOPICS } from './subscription';

describe('urlBase64ToUint8Array', () => {
	it('padding 없는 base64url 복원', () => {
		// 'hi' = base64 'aGk=' → base64url 'aGk'
		const out = urlBase64ToUint8Array('aGk');
		expect(Array.from(out)).toEqual([0x68, 0x69]);
	});

	it('-_ 치환 문자 처리', () => {
		// bytes [0xfb, 0xff] = base64 '+/8=' → base64url '-_8'
		const out = urlBase64ToUint8Array('-_8');
		expect(Array.from(out)).toEqual([0xfb, 0xff]);
	});
});

describe('serializeSubscription', () => {
	it('toJSON 의 endpoint·keys 를 허브 body 형태로(토픽 포함)', () => {
		const fake = {
			endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
			toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/abc', keys: { p256dh: 'PPP', auth: 'AAA' } })
		} as unknown as PushSubscription;
		const payload = serializeSubscription(fake, [...DEFAULT_TOPICS]);
		expect(payload).toEqual({
			endpoint: 'https://fcm.googleapis.com/fcm/send/abc',
			keys: { p256dh: 'PPP', auth: 'AAA' },
			topics: ['blogPublish', 'cardPublish']
		});
	});

	it('keys 부재 시 빈 문자열 폴백', () => {
		const fake = {
			endpoint: 'https://web.push.apple.com/x',
			toJSON: () => ({ endpoint: 'https://web.push.apple.com/x' })
		} as unknown as PushSubscription;
		const payload = serializeSubscription(fake, ['blogPublish']);
		expect(payload.keys).toEqual({ p256dh: '', auth: '' });
	});
});
