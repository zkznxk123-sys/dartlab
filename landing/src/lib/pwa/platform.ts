// PWA 플랫폼 감지 — InstallPrompt·NotifyOptIn 공유 SSOT.
// InstallPrompt.svelte 원본 동작 그대로(순수 이동, 로직 불변). 브라우저 전용(navigator/window 가정).

/** 홈화면 아이콘으로 연 standalone 실행인가(설치 완료 신호). */
export function isStandalone(): boolean {
	return (
		window.matchMedia('(display-mode: standalone)').matches ||
		(navigator as unknown as { standalone?: boolean }).standalone === true
	);
}

/** iOS Safari 탭인가(beforeinstallprompt·웹푸시 게이트가 다름 — Chrome/Firefox/Edge for iOS 제외). */
export function isIosSafari(): boolean {
	const ua = navigator.userAgent;
	return /iphone|ipad|ipod/i.test(ua) && /safari/i.test(ua) && !/crios|fxios|edgios/i.test(ua);
}
