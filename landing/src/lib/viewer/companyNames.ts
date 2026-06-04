// 회사 유니버스(code → 회사명) — panel 엔 회사명 컬럼이 없어 ecosystem(scan 과 동일 소스)에서 해석.
// module-level promise 캐시 — 검색·뷰어가 공유(중복 fetch 0).
import { loadJson } from '$lib/data/dartlabData';

export interface Co {
	code: string;
	name: string;
}

let cache: Promise<Co[]> | null = null;

export function loadCompanies(): Promise<Co[]> {
	if (!cache) {
		cache = loadJson<{ nodes?: Array<{ id?: string; stockCode?: string; label?: string }> }>('map/ecosystem.json', {
			fetchFn: fetch,
			preferLocal: true
		})
			.then((eco) =>
				(eco?.nodes ?? [])
					.map((n) => ({ code: String(n.id ?? n.stockCode ?? ''), name: String(n.label ?? '') }))
					.filter((c) => c.code)
			)
			.catch(() => [] as Co[]);
	}
	return cache;
}
