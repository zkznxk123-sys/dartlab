/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * dartlab Service Worker — 설치형 PWA(앱 셸 오프라인) + 데이터 무간섭.
 *
 * - 앱 셸(build/files: 해시 불변 JS·CSS·정적 자산)은 install 시 프리캐시 → cache-first.
 * - 내비게이션(HTML)은 network-first → 성공분 캐시 → 오프라인이면 캐시 폴백.
 * - ⛔ 크로스오리진(HF parquet·프록시 /media·/news 등 데이터)은 SW 가 절대 가로채지 않는다. hyparquet/DuckDB
 *   의 Range 요청을 네트워크에 그대로 맡겨야 첫 방문자의 저장소·메모리를 불리지 않는다(설계 불변).
 */
import { build, files, version } from '$service-worker';
import {
	SUBSCRIBE_URL,
	DEFAULT_TOPICS,
	serializeSubscription,
	urlBase64ToUint8Array
} from '$lib/notify/subscription';
import { safeNotificationUrl } from '$lib/notify/url';

declare const self: ServiceWorkerGlobalScope;

const SHELL = `dartlab-shell-${version}`;
const SHELL_ASSETS = [...build, ...files];
const ASSET_SET = new Set(SHELL_ASSETS);

// 웹푸시(P1) 상수. 미주입(빈 키/URL)이면 push 재구독·발송이 graceful no-op.
const VAPID_PUBLIC_KEY: string = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? '';
const BASE = import.meta.env.BASE_URL.replace(/\/$/, ''); // '/dartlab' (BASE_PATH 빌드) — 클릭/표시 404 가드
const ICON = `${import.meta.env.BASE_URL}icon-192.png`;

self.addEventListener('install', (event) => {
	event.waitUntil(
		(async () => {
			const cache = await caches.open(SHELL);
			await cache.addAll(SHELL_ASSETS);
			await self.skipWaiting();
		})()
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			// 이전 버전 셸 캐시 + 옛 HF parquet full-body 캐시(dartlab-scan-*) 제거.
			const keys = await caches.keys();
			await Promise.all(
				keys
					.filter((k) => k.startsWith('dartlab-scan-') || (k.startsWith('dartlab-shell-') && k !== SHELL))
					.map((k) => caches.delete(k))
			);
			await self.clients.claim();
		})()
	);
});

self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	const url = new URL(req.url);

	// ⛔ 크로스오리진(HF·프록시·뉴스 등 데이터) — SW 무간섭. 네트워크 그대로.
	if (url.origin !== self.location.origin) return;

	// 앱 셸 자산(해시 불변) — 캐시 우선.
	if (ASSET_SET.has(url.pathname)) {
		event.respondWith(
			(async () => {
				const cached = await caches.match(req);
				return cached ?? fetch(req);
			})()
		);
		return;
	}

	// 내비게이션(HTML) — 네트워크 우선, 성공분 캐시, 오프라인이면 캐시 폴백.
	if (req.mode === 'navigate') {
		event.respondWith(
			(async () => {
				try {
					const res = await fetch(req);
					const cache = await caches.open(SHELL);
					cache.put(req, res.clone());
					return res;
				} catch {
					const cached = await caches.match(req);
					return (
						cached ??
						new Response('오프라인 — 연결을 확인하세요.', {
							status: 503,
							headers: { 'Content-Type': 'text/html; charset=utf-8' }
						})
					);
				}
			})()
		);
		return;
	}

	// 그 외 same-origin GET — 기본 네트워크(가로채지 않음).
});

// ── 웹푸시(P1) — push/notificationclick/pushsubscriptionchange ([07] §1) ──────────

// 발송 본문 = aes128gcm 평문 {title,body,url,tag}. url 은 app-path(base 없음) → 여기서 BASE 접두 + origin 검증.
self.addEventListener('push', (event) => {
	event.waitUntil(
		(async () => {
			let payload: { title?: string; body?: string; url?: string; tag?: string } = {};
			try {
				payload = event.data?.json() ?? {};
			} catch {
				payload = {}; // 파싱 실패 → 고정문구 fallback (항상 showNotification — 미표시=userVisibleOnly 위반)
			}
			const title = payload.title || 'DartLab';
			const body = payload.body || '새 소식이 있습니다.';
			const url = safeNotificationUrl(BASE, payload.url, self.location.origin); // BASE 접두 + origin 고정(피싱 차단)
			await self.registration.showNotification(title, {
				body,
				tag: payload.tag,
				icon: ICON,
				badge: ICON,
				data: { url }
			});
		})()
	);
});

self.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const url = (event.notification.data && event.notification.data.url) || `${BASE}/`;
	event.waitUntil(
		(async () => {
			const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
			for (const client of windows) {
				if (new URL(client.url).origin === self.location.origin) {
					await client.focus();
					try {
						await (client as WindowClient).navigate(url);
					} catch {
						/* navigate 미지원 — focus 만 */
					}
					return;
				}
			}
			await self.clients.openWindow(url);
		})()
	);
});

// lib.dom 버전별로 타입 부재 → 수동 선언.
interface PushSubscriptionChangeEvent extends ExtendableEvent {
	readonly newSubscription: PushSubscription | null;
	readonly oldSubscription: PushSubscription | null;
}
self.addEventListener('pushsubscriptionchange', ((event: PushSubscriptionChangeEvent) => {
	event.waitUntil(
		(async () => {
			if (!import.meta.env.VITE_PUSHHUB_URL || !VAPID_PUBLIC_KEY) return; // 허브 URL·키 미주입 → graceful skip
			// oldSubscription.options 에 원래 applicationServerKey 보존 → 재구독 시 VAPID 키 플러밍 거의 불요.
			const sub =
				event.newSubscription ??
				(await self.registration.pushManager.subscribe(
					(event.oldSubscription?.options as PushSubscriptionOptionsInit) ?? {
						userVisibleOnly: true,
						applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
					}
				));
			await fetch(SUBSCRIBE_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(serializeSubscription(sub, [...DEFAULT_TOPICS]))
			});
			// 구 endpoint 는 /send 404/410 inline purge 로 자가청소(별도 DELETE 불요).
		})()
	);
}) as EventListener);

export {};
