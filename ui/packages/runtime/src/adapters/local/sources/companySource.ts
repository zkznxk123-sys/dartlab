// 로컬 company 포트 — relations 는 /api(로컬 Python 서버)/meta, 전 종목 product·회사정보 인덱스는
// 공개 HF corpList.parquet 공유(macro·finance 와 동일한 "로컬이 깃헙페이지 자산을 공유"하는 단일 경로).
// 이 데이터의 SSOT 자체가 HF parquet 이라 silent fallback 이 아니다 — 공개 어댑터와 동일 결과 = 미러.
import type { CompanyPort, CompanyRelations, ProductIndexItem } from '@dartlab/ui-contracts';
import { getJson } from '../fetchJson';
import { loadHfProductIndexMap } from '../../public/sources/productIndexSource';
import { loadIndustryProfitPool } from '../../public/sources/industryPoolSource';
import type { CompanyMeta, LocalCaches } from '../localTypes';

function loadMeta(apiBase: string, caches: LocalCaches, code: string): Promise<CompanyMeta | null> {
	const c = code.trim();
	let p = caches.meta.get(c);
	if (!p) {
		p = getJson<CompanyMeta>(apiBase, `/api/company/${encodeURIComponent(c)}/meta`);
		caches.meta.set(c, p);
	}
	return p;
}

// 전 종목 product/회사정보 인덱스 = 공개 HF 소스를 Record(JSON-safe 계약)로 1 회 변환·공유 (공개 어댑터와 동일).
let productIndexPromise: Promise<Record<string, ProductIndexItem> | null> | null = null;
function loadProductIndexRecord(): Promise<Record<string, ProductIndexItem> | null> {
	productIndexPromise ??= (async () => {
		try {
			return Object.fromEntries(await loadHfProductIndexMap());
		} catch {
			return null;
		}
	})();
	return productIndexPromise;
}

export function localCompanyPort(apiBase: string, caches: LocalCaches): CompanyPort {
	return {
		// 단일 회사 제품/프로필 = 공개 HF 인덱스 조회 (공개 products(code) 와 동일 — ceo/결산/상장/본사/홈페이지 포함).
		async products(code) {
			const rec = await loadProductIndexRecord();
			return rec?.[code.trim()] ?? null;
		},
		// 전 종목 인덱스 = 공개 HF 자산 공유 (옛 null = 미보유 표기는 미러 깨짐 → 깃헙페이지 자산 직접 로드로 정정).
		productIndex: loadProductIndexRecord,
		async relations(code) {
			const meta = await loadMeta(apiBase, caches, code);
			if (!meta || !meta.corpName) return null;
			// 로컬 관계망 정규화는 단계-8(scan/map) 영역 — 회사 존재 시 빈 관계 반환(null 아님).
			return {
				suppliers: [],
				customers: [],
				peers: [],
				neighborCount: 0,
				blog: null
			} satisfies CompanyRelations;
		},
		// 라이브 보고서 팩트 — 로컬 미배선. 해당 없음 = [].
		async reportFacts() {
			return [];
		},
		// 산업 profit-pool = 공개 정적 자산(map/industries/{id}.json) 공유 — 로컬 단일사여도 산업 격자는 실데이터.
		industryProfitPool: loadIndustryProfitPool
	};
}
