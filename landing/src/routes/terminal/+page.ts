// /terminal — DartLab Terminal 본진 라우트. 실데이터를 landing loadJson 계약으로 로드.
// UI 본체는 $lib/terminal 트리 ($lib/terminal/Terminal.svelte).
import { browser } from '$app/environment';
import type { PageLoad } from './$types';
import { loadJson } from '$lib/data/dartlabData';
import { prefetch, LAST_SYM_KEY } from '$lib/terminal/data/workbench';
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
	// 일별시세 조기 워밍 — 마지막 본 종목(없으면 기본 005930)의 주가·재무를 엔진 JSON 로드와
	// 병렬로 시작 (in-flight dedup 이라 패널 호출과 중복 fetch 0). 차트 첫 페인트 ~2s 단축.
	if (browser) {
		const last = localStorage.getItem(LAST_SYM_KEY) || '005930';
		prefetch(last, new Date().getFullYear());
	}
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
