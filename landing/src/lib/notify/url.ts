// 알림 목적지 URL 안전 해석 — payload.url(app-path, base 없음)에 BASE 접두 + origin 고정(피싱 차단).
// SW push/notificationclick 가 공유. 순수 함수라 vitest 로 회귀(외부 origin·base 누락·악성 스킴).
//
// 핵심 불변: 결과는 *항상* 우리 origin 의 path+search 다. payloadUrl 이 절대 URL/스킴이어도 base('/...')
// 접두 후 origin 기준 상대해석되어 외부로 못 나간다(최악 = 우리 도메인의 404, 피싱·javascript: 불가).

export function safeNotificationUrl(base: string, payloadUrl: string | undefined, origin: string): string {
	const home = `${base}/`;
	if (!payloadUrl) return home;
	try {
		const dest = new URL(base + payloadUrl, origin);
		if (dest.origin === origin) return dest.pathname + dest.search;
	} catch {
		/* URL 파싱 실패 → 홈 */
	}
	return home;
}
