// /lab/terminal — DartLab Terminal (네이티브 Svelte). 실데이터를 landing loadJson 계약으로 로드.
// 본진 승격 시 이 +page 만 라우트로 복제하면 됨 ($lib/terminal 트리는 그대로 재사용).
import type { PageLoad } from './$types';
import { loadJson } from '$lib/data/dartlabData';
import type {
	FinanceFile,
	MacroFile,
	MetaFile,
	PricesFile,
	IndexRow,
	EcosystemFile,
	QuartersFile
} from '$lib/terminal/data/types';

export const ssr = false;
export const prerender = true;

export const load: PageLoad = async ({ fetch }) => {
	const opt = { fetchFn: fetch, preferLocal: true };
	const [finance, macro, meta, prices, index, eco, quarters] = await Promise.all([
		loadJson<FinanceFile>('dashboards/finance.json', opt),
		loadJson<MacroFile>('dashboards/macro.json', opt),
		loadJson<MetaFile>('dashboards/meta.json', opt),
		loadJson<PricesFile>('map/prices-snapshot.json', opt),
		loadJson<IndexRow[]>('map/search-index.json', opt),
		loadJson<EcosystemFile>('map/ecosystem.json', opt),
		loadJson<QuartersFile>('dashboards/quarters.json', opt)
	]);
	return {
		raw: {
			finance: finance ?? { years: [], companies: {} },
			macro: macro ?? null,
			meta: meta ?? null,
			prices: prices ?? { data: {} },
			index: index ?? [],
			eco: eco ?? null,
			quarters: quarters ?? null
		}
	};
};
