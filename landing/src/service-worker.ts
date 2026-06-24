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

declare const self: ServiceWorkerGlobalScope;

const SHELL = `dartlab-shell-${version}`;
const SHELL_ASSETS = [...build, ...files];
const ASSET_SET = new Set(SHELL_ASSETS);

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

export {};
