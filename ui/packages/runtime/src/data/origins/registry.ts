// 오리진 레지스트리 — 데이터 워크벤치 SSOT 의 "어디서 가져오나" 단일 표. (mainPlan/data-workbench-ssot 02·03)
// P1: HF 계열(hf·hfRange) 만 등록 — 기존 origin.ts(HF URL SSOT)를 흡수.
// P2: news·naver 워커 등록 — newsSource/naverPriceSource 가 각자 복제하던 env 게이트 + dev 프록시 URL
//   조립을 여기로 흡수. 미배선(localApi·duckdbHf·landingJson)은 후속 wave. 미등록 호출은 명시 throw(배선순서 가드).
import { hfUrl, hfRangeUrl } from '../origin';

// vite env 안전 접근 — runtime 패키지 tsc 는 vite/client 타입 없이 검사된다(origin.ts 동일 패턴, 소비 앱이 번들 시 치환).
const viteEnv = (import.meta as { env?: Record<string, string | boolean | undefined> }).env;

// 워커 프록시 base URL(가역 빌드-env 게이트). 비우면 미설정 — 호출측이 originConfigured 로 미동작([]) 판정.
//   news = CF 워커 /news 라우트(전 환경 동일, dev 폴백 없음 — /__news 미들웨어는 구현된 적 없음).
//   naver = dev 는 Vite /__naver 미들웨어(브라우저 CORS 우회), 프로덕션은 CF 프록시 /naver 라우트.
const NEWS_PROXY = ((viteEnv?.VITE_DARTLAB_NEWS_PROXY as string | undefined) ?? '').replace(/\/+$/, '');
const NAVER_PROXY = ((viteEnv?.VITE_DARTLAB_NAVER_PROXY as string | undefined) ?? '').replace(/\/+$/, '');
const naverDev = Boolean(viteEnv?.DEV);

export type OriginId = 'hf' | 'hfRange' | 'localApi' | 'newsWorker' | 'naverWorker' | 'duckdbHf' | 'landingJson';

/** 캐시 정책 — 오리진별 차등(정직 TTL, 04 §정직 TTL). scope='none' = 무캐시. */
export interface CachePolicy {
	scope: 'memory' | 'persist' | 'none';
	ttlMs: number;
	maxEntries?: number;
}

interface OriginDef {
	resolve: (path: string) => string;
	defaultCache: CachePolicy;
	/** 게이트형 오리진(env 미설정 시 미동작). 미정의 = 항상 설정됨. */
	configured?: () => boolean;
}

const MIN = 60_000;

// 워커 라우트 URL 조립 — path = 종목 코드. 둘 다 `?code=<encoded>` 쿼리(옛 newsEndpoint/naverEndpoint 동일).
const newsWorkerUrl = (code: string): string => `${NEWS_PROXY}?code=${encodeURIComponent(code)}`;
const naverWorkerUrl = (code: string): string => {
	const q = `code=${encodeURIComponent(code)}`;
	return naverDev ? `/__naver?${q}` : `${NAVER_PROXY}?${q}`;
};

// hf=소형 통파일/seed(프록시 엣지캐시 경로), hfRange=byte-range(직결). origin.ts 정책 그대로 흡수.
// newsWorker·naverWorker=언론사 저작권 archive 워커 read(라이브 표시) — 신선도형이라 짧은 TTL.
const ORIGINS: Partial<Record<OriginId, OriginDef>> = {
	hf: { resolve: hfUrl, defaultCache: { scope: 'memory', ttlMs: 60 * MIN, maxEntries: 64 } },
	hfRange: { resolve: hfRangeUrl, defaultCache: { scope: 'memory', ttlMs: 60 * MIN, maxEntries: 128 } },
	newsWorker: {
		resolve: newsWorkerUrl,
		defaultCache: { scope: 'memory', ttlMs: 10 * MIN, maxEntries: 64 },
		configured: () => Boolean(NEWS_PROXY) // 프록시 미설정 → 미동작(빈 섹션), dev 폴백 없음
	},
	naverWorker: {
		resolve: naverWorkerUrl,
		defaultCache: { scope: 'memory', ttlMs: 10 * MIN, maxEntries: 64 },
		configured: () => naverDev || Boolean(NAVER_PROXY) // dev=미들웨어 / 프로덕션=프록시 설정 시
	}
};

/** 오리진 상대경로 → 절대 URL. 미등록 오리진은 throw(P2 등록 또는 배선순서 위반 노출). */
export function originUrl(id: OriginId, path: string): string {
	const def = ORIGINS[id];
	if (!def) throw new Error(`[origins] '${id}' 미등록 — data/origins/registry 에 추가하거나 배선순서 확인(P2).`);
	return def.resolve(path);
}

/** 오리진 기본 캐시 정책(호출부 override 가능). 미등록은 undefined. */
export function originCache(id: OriginId): CachePolicy | undefined {
	return ORIGINS[id]?.defaultCache;
}

/** 게이트형 오리진이 설정(배선)됐는지. false = 미동작([] 반환, 코어 호출 생략). 비게이트 오리진은 항상 true. */
export function originConfigured(id: OriginId): boolean {
	const def = ORIGINS[id];
	if (!def) return false;
	return def.configured ? def.configured() : true;
}
