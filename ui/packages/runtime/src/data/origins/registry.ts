// 오리진 레지스트리 — 데이터 워크벤치 SSOT 의 "어디서 가져오나" 단일 표. (mainPlan/data-workbench-ssot 02·03)
// P1: HF 계열(hf·hfRange) 만 등록 — 기존 origin.ts(HF URL SSOT)를 흡수. 나머지 오리진(news·naver 워커·
// localApi·duckdbHf·landingJson)은 P2 에서 등록. 미등록 호출은 명시 throw(배선순서 가드).
import { hfUrl, hfRangeUrl } from '../origin';

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
}

const MIN = 60_000;

// P1 등록분. hf=소형 통파일/seed(프록시 엣지캐시 경로), hfRange=byte-range(직결). origin.ts 정책 그대로 흡수.
const ORIGINS: Partial<Record<OriginId, OriginDef>> = {
	hf: { resolve: hfUrl, defaultCache: { scope: 'memory', ttlMs: 60 * MIN, maxEntries: 64 } },
	hfRange: { resolve: hfRangeUrl, defaultCache: { scope: 'memory', ttlMs: 60 * MIN, maxEntries: 128 } }
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
