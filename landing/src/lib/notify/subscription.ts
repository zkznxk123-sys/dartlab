// 웹푸시 구독 SSOT — service-worker.ts 와 NotifyOptIn.svelte 가 공유한다.
// 직렬화 형태·구독 URL·토픽 목록을 한 곳에서 정의해 허브([06])·러너([08])와 정합을 유지한다.
//
// 환경변수(둘 다 공개값, 미주입 시 graceful — NotifyOptIn 가드② hidden / SW 재구독 skip):
//   VITE_PUSHHUB_URL       허브 base (https://dartlab-push-hub.<sub>.workers.dev)
//   VITE_VAPID_PUBLIC_KEY  base64url uncompressed 공개키 (NotifyOptIn·SW 가 직접 읽음)

/** 허브 /subscribe 절대 URL. base 비면 빈 prefix → '/subscribe'(미주입 신호, 호출측이 가드). */
export const SUBSCRIBE_URL = (import.meta.env.VITE_PUSHHUB_URL ?? '').replace(/\/+$/, '') + '/subscribe';

/** P1 기본 토픽 — [06] TOPIC_ALLOWLIST 와 1:1(blogPublish·cardPublish). */
export const DEFAULT_TOPICS = ['blogPublish', 'cardPublish'];

export interface SubscribePayload {
	endpoint: string;
	keys: { p256dh: string; auth: string };
	topics: string[];
}

/** base64url(공개키) → applicationServerKey 용 Uint8Array. padding 복원 후 atob.
 *  명시 ArrayBuffer 백킹 — applicationServerKey(BufferSource<ArrayBuffer>) 타입 정합(TS 5.7 SharedArrayBuffer 분리). */
export function urlBase64ToUint8Array(b64: string): Uint8Array<ArrayBuffer> {
	const padding = '='.repeat((4 - (b64.length % 4)) % 4);
	const base64 = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/');
	const raw = atob(base64);
	const out = new Uint8Array(new ArrayBuffer(raw.length));
	for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
	return out;
}

/** PushSubscription → 허브 POST body. sub.toJSON() 의 keys(padding 포함 base64url 가능)는 허브가 허용. */
export function serializeSubscription(sub: PushSubscription, topics: string[]): SubscribePayload {
	const json = sub.toJSON();
	const keys = json.keys ?? { p256dh: '', auth: '' };
	return {
		endpoint: sub.endpoint,
		keys: { p256dh: keys.p256dh ?? '', auth: keys.auth ?? '' },
		topics
	};
}

/** 기존 구독 재사용 또는 신규 구독(userVisibleOnly 강제 — 미표시 발송 차단 규약). */
export async function subscribePush(
	reg: ServiceWorkerRegistration,
	vapidPublicKey: string
): Promise<PushSubscription> {
	const existing = await reg.pushManager.getSubscription();
	if (existing) return existing;
	return reg.pushManager.subscribe({
		userVisibleOnly: true,
		applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
	});
}
