/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

/**
 * dartlab Service Worker.
 *
 * HF parquet 은 브라우저 Cache Storage 에 전체 저장하지 않는다. hyparquet/DuckDB 의
 * Range 요청은 네트워크에 그대로 맡겨야 첫 방문자의 저장소와 메모리를 불리지 않는다.
 */

declare const self: ServiceWorkerGlobalScope;

self.addEventListener('install', (event) => {
	// 즉시 활성화 — 새 SW 가 기존 SW 대신 take over
	event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			// 이전 버전의 HF parquet full-body cache 제거.
			const keys = await caches.keys();
			await Promise.all(
				keys
					.filter((k) => k.startsWith('dartlab-scan-'))
					.map((k) => caches.delete(k))
			);
			await self.clients.claim();
		})()
	);
});

export {};
