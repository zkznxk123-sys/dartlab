// IndexPort public 조립 — KR(gov/indices 직독) + US(FRED) 라우팅 단일 분기.
// gov·fred 모두 HF 공개 데이터 브라우저 직독(백엔드 0)이라 local 셸도 그대로 재사용(createLocalRuntime).
import type { Candle, IndexPort, IndexRef } from '@dartlab/ui-contracts';
import { KR_INDEX_PRESETS, US_INDEX_PRESETS } from '@dartlab/ui-contracts';
import { loadGovIndexCandles, scanGovIndexNames } from './govIndexSource';
import { loadFredIndexCandles, searchUsIndexPresets } from './fredIndexSource';

export function createPublicIndexPort(): IndexPort {
	return {
		async catalog(): Promise<IndexRef[]> {
			return [...KR_INDEX_PRESETS, ...US_INDEX_PRESETS]; // 화이트리스트 9종(상시)
		},
		async search(query: string, limit = 12): Promise<IndexRef[]> {
			const q = query.trim();
			if (!q) return [];
			const us = searchUsIndexPresets(q); // US preset 4종 라벨/ID 매칭(확장 0)
			const kr = await scanGovIndexNames(q, Math.max(0, limit - us.length)); // 잔여 한도만 KR 에(이중 limit 압착 방지)
			return [...us, ...kr].slice(0, limit);
		},
		series(ref: IndexRef): Promise<Candle[] | null> {
			return ref.market === 'US' ? loadFredIndexCandles(ref) : loadGovIndexCandles(ref); // 분기 단일 지점
		}
	};
}
