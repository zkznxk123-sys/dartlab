<script lang="ts">
	// 발행 알림 opt-in — 새 글·카드 푸시 구독. 2단 게이트: 콜드에선 소프트 프롬프트만, OS 권한 팝업은 '알림 켜기'
	// 클릭(제스처) 안에서만. InstallPrompt 미러(하단 바)지만 위로 offset 해 시각 겹침 방지([07] §2·§6).
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { isStandalone, isIosSafari } from '$lib/pwa/platform';
	import {
		SUBSCRIBE_URL,
		DEFAULT_TOPICS,
		subscribePush,
		serializeSubscription
	} from '$lib/notify/subscription';

	let { topics = [...DEFAULT_TOPICS] }: { topics?: string[] } = $props();

	const DISMISS_KEY = 'dl-notify-dismissed';
	const VAPID_PUBLIC_KEY: string = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? '';

	type Phase = 'hidden' | 'soft' | 'subscribing' | 'on' | 'blocked';
	let phase = $state<Phase>('hidden');

	function dismissed(): boolean {
		try {
			return localStorage.getItem(DISMISS_KEY) === '1';
		} catch {
			return false;
		}
	}
	function remember() {
		try {
			localStorage.setItem(DISMISS_KEY, '1');
		} catch {
			/* 프라이빗 모드 등 — 무시 */
		}
	}

	async function subscribeAndPost() {
		const reg = await navigator.serviceWorker.ready;
		const sub = await subscribePush(reg, VAPID_PUBLIC_KEY);
		const res = await fetch(SUBSCRIBE_URL, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(serializeSubscription(sub, topics))
		});
		if (!res.ok) throw new Error(`subscribe ${res.status}`);
	}

	// 제스처: requestPermission 을 먼저(동기 제스처 보존) → granted 면 await 구독.
	async function enable() {
		phase = 'subscribing';
		let perm: NotificationPermission;
		try {
			perm = await Notification.requestPermission();
		} catch {
			phase = 'soft';
			return;
		}
		if (perm === 'granted') {
			try {
				await subscribeAndPost();
				phase = 'on';
			} catch {
				phase = 'soft'; // 구독/POST 실패 → 콜드 재시도 가능 상태로 복귀
			}
		} else if (perm === 'denied') {
			phase = 'blocked';
			remember(); // 콜드 자동 재시도 0
		} else {
			phase = 'soft';
		}
	}

	async function disable() {
		try {
			const reg = await navigator.serviceWorker.ready;
			const sub = await reg.pushManager.getSubscription();
			if (sub) {
				await Promise.allSettled([
					sub.unsubscribe(),
					fetch(SUBSCRIBE_URL, {
						method: 'DELETE',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ endpoint: sub.endpoint })
					})
				]);
			}
		} catch {
			/* 무시 */
		}
		phase = 'soft';
	}

	function close() {
		phase = 'hidden';
		remember();
	}

	onMount(() => {
		(async () => {
			// 가드 순서 — 하나라도 걸리면 requestPermission 미호출.
			if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) return; // ① 미지원
			if (!VAPID_PUBLIC_KEY) return; // ② 키 미주입 = 기능 off
			if (!isStandalone() && isIosSafari()) return; // ③ iOS 미설치 — InstallPrompt 가 설치유도(중복 안내 0)
			if (dismissed()) return; // ④ 닫음 기억
			if (Notification.permission === 'denied') {
				phase = 'blocked'; // ⑤ 영구차단 안내만
				return;
			}
			if (Notification.permission === 'granted') {
				// ⑥ 기존 구독 있으면 on, 없으면 조용히 구독→on
				try {
					const reg = await navigator.serviceWorker.ready;
					const existing = await reg.pushManager.getSubscription();
					if (existing) {
						phase = 'on';
					} else {
						await subscribeAndPost();
						phase = 'on';
					}
				} catch {
					phase = 'soft';
				}
				return;
			}
			phase = 'soft'; // ⑦ 'default' → 소프트 프롬프트
		})();
	});
</script>

{#if phase !== 'hidden'}
	<div class="notifyBar" role="dialog" aria-label="DartLab 알림 설정">
		<img class="nIcon" src="{base}/icon-192.png" alt="" width="32" height="32" />
		<div class="nText">
			{#if phase === 'on'}
				<b>알림 켜짐</b>
				<span>새 글·카드를 알려드려요</span>
			{:else if phase === 'blocked'}
				<b>알림 차단됨</b>
				<span>브라우저 설정에서 허용으로 바꿔주세요</span>
			{:else}
				<b>새 글 알림 받기</b>
				<span>새 분석·카드뉴스가 올라오면 알림</span>
			{/if}
		</div>
		{#if phase === 'on'}
			<button class="nGhost" onclick={disable}>끄기</button>
		{:else if phase === 'blocked'}
			<!-- 재요청 버튼 0 (영구차단) -->
		{:else}
			<button class="nEnable" onclick={enable} disabled={phase === 'subscribing'}>
				{phase === 'subscribing' ? '…' : '알림 켜기'}
			</button>
		{/if}
		<button class="nClose" onclick={close} aria-label="닫기">✕</button>
	</div>
{/if}

<style>
	/* InstallPrompt(bottom 14px) 위로 stack — 둘 다 떠도 겹치지 않게 offset. */
	.notifyBar {
		position: fixed;
		left: 50%;
		bottom: calc(64px + env(safe-area-inset-bottom, 0px));
		transform: translateX(-50%);
		z-index: 80;
		display: flex;
		align-items: center;
		gap: 11px;
		width: min(380px, calc(100vw - 24px));
		padding: 10px 12px;
		border-radius: 14px;
		background: rgba(13, 17, 25, 0.96);
		border: 1px solid rgba(var(--dl-accent-rgb), 0.4);
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(8px);
		color: #e8eef6;
		animation: nIn 0.28s cubic-bezier(0.2, 0.9, 0.3, 1);
	}
	@keyframes nIn {
		from {
			opacity: 0;
			transform: translate(-50%, 14px);
		}
		to {
			opacity: 1;
			transform: translate(-50%, 0);
		}
	}
	.nIcon {
		flex: 0 0 auto;
		border-radius: 8px;
	}
	.nText {
		display: flex;
		flex-direction: column;
		gap: 1px;
		flex: 1 1 auto;
		min-width: 0;
		line-height: 1.3;
		overflow-wrap: normal;
		word-break: keep-all;
	}
	.nText b {
		font-size: 13px;
		font-weight: 700;
		color: #f5f8fc;
		white-space: nowrap;
	}
	.nText span {
		font-size: 11px;
		color: #9aa7bc;
	}
	.nEnable {
		flex: 0 0 auto;
		padding: 7px 14px;
		border: none;
		border-radius: 9px;
		background: var(--dl-accent);
		color: #06080d;
		font-size: 12.5px;
		font-weight: 800;
		cursor: pointer;
		transition: filter 0.15s;
	}
	.nEnable:hover {
		filter: brightness(1.08);
	}
	.nEnable:disabled {
		opacity: 0.6;
		cursor: default;
	}
	.nGhost {
		flex: 0 0 auto;
		padding: 7px 12px;
		border: 1px solid rgba(255, 255, 255, 0.18);
		border-radius: 9px;
		background: transparent;
		color: #cbd5e1;
		font-size: 12px;
		cursor: pointer;
	}
	.nGhost:hover {
		background: rgba(255, 255, 255, 0.06);
	}
	.nClose {
		flex: 0 0 auto;
		width: 26px;
		height: 26px;
		border: none;
		border-radius: 7px;
		background: transparent;
		color: #6b7688;
		font-size: 13px;
		cursor: pointer;
	}
	.nClose:hover {
		color: #cbd5e1;
		background: rgba(255, 255, 255, 0.06);
	}
</style>
