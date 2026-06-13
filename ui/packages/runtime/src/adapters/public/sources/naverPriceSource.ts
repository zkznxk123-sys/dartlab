// 네이버 fchart 라이브 fresh-tail — gov(공공데이터포털, T+1 영업일 지연)가 아직 발행하지 않은
// 최신 거래일(예: 금요일치는 월요일 발행)을 표시용으로 채운다. 공개 HF 데이터셋(gov)은 그대로 두고
// 화면을 그릴 때만 네이버에서 가져와 mergeDedup 으로 tail 에 얹는다 — 재배포가 아니라 사용자 세션
// 표시용 fetch 이므로 저작권 안전. gov 와 네이버는 KRX 원천·원주가라 겹치는 날 값이 동일 → 점프 없음.
//   dev = /__naver 미들웨어(Node 서버측 fetch, 브라우저 CORS 우회).
//   프로덕션 = CF 프록시 네이버 라우트(예정) — 배선 전까진 미동작([] 반환).
import type { Candle } from '@dartlab/ui-contracts';

const browser = typeof window !== 'undefined';
// vite 환경 캐스트 — 런타임 패키지 tsc 는 vite/client 타입 무의존 (govPriceSource 동일 패턴)
const viteEnv = (import.meta as { env?: Record<string, string | boolean | undefined> }).env;

const cache = new Map<string, Candle[]>();

// 프로덕션 프록시 URL (CF 워커 /naver 라우트). 미설정 시 프로덕션에선 미동작([] = EOD 까지만) —
// origin.ts HF_RESOLVE · livePrice.ts QUOTE_WORKER 와 동일한 빌드-env 게이트 패턴(가역, 비우면 즉시 롤백).
const NAVER_PROXY = ((viteEnv?.VITE_DARTLAB_NAVER_PROXY as string | undefined) ?? '').replace(/\/+$/, '');

/** dev = Vite /__naver 미들웨어, 프로덕션 = CF 프록시 /naver 라우트. 둘 다 없으면 null(미동작). */
function naverEndpoint(code: string): string | null {
	const q = `code=${encodeURIComponent(code)}`;
	if (viteEnv?.DEV) return `/__naver?${q}`;
	if (NAVER_PROXY) return `${NAVER_PROXY}?${q}`;
	return null;
}

interface NaverFreshFile {
	source: string;
	code: string;
	asOf: string;
	candles: Candle[];
}

/** gov 미발행 최신 거래일을 네이버에서 채우는 fresh tail (오름차순 Candle[]). [] = 미지원·실패·미배선. */
export function loadNaverFresh(code: string): Promise<Candle[]> {
	if (!browser) return Promise.resolve([]);
	const c = code.trim();
	const url = naverEndpoint(c);
	if (!url) return Promise.resolve([]); // 프로덕션 + 프록시 미설정 → EOD(전일 종가)까지만
	const hit = cache.get(c);
	if (hit) return Promise.resolve(hit);
	return (async () => {
		try {
			const res = await fetch(url);
			if (!res.ok) {
				cache.set(c, []);
				return [];
			}
			const j = (await res.json()) as NaverFreshFile;
			const candles = Array.isArray(j.candles) ? j.candles : [];
			cache.set(c, candles);
			return candles;
		} catch {
			cache.set(c, []);
			return [];
		}
	})();
}
