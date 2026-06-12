// /terminal(본진) · /lab/terminal-dev(격리 개발) 공용 라우트 로더 SSOT — 복사 드리프트 차단.
// 씨데이터 JSON 7종 병렬 로드 + 마지막 본 종목 prefetch(주가·재무·제품맵 워밍업).
import { browser } from '$app/environment';
import { loadJson } from '$lib/data/dartlabData';
import { prefetch, LAST_SYM_KEY } from '$lib/terminal/data/workbench';
import type {
	FinanceFile,
	MacroFile,
	MetaFile,
	PricesFile,
	IndexRow,
	EcosystemFile,
	QuartersFile,
	RawData
} from '$lib/terminal/data/types';

export async function loadTerminalRaw(fetchFn: typeof fetch): Promise<{ raw: RawData }> {
	// 일별시세 조기 워밍 — 마지막 본 종목(없으면 기본 005930)의 주가·재무를 씨데이터 JSON 로드와
	// 병렬로 시작 (in-flight dedup 이라 패널 호출과 중복 fetch 0). 차트 첫 페인트 ~2s 단축.
	if (browser) {
		const last = localStorage.getItem(LAST_SYM_KEY) || '005930';
		prefetch(last, new Date().getFullYear());
	}
	const opt = { fetchFn, preferLocal: true };
	const [finance, macro, meta, prices, index, eco, quarters] = await Promise.all([
		loadJson<FinanceFile>('dashboards/finance.json', opt),
		// macro 도 HF-first — mapBuild 가 매일 publish 하는 소형 파일 (git 정적 사본 동결 사고 재발 방지)
		loadJson<MacroFile>('dashboards/macro.json', { fetchFn }),
		loadJson<MetaFile>('dashboards/meta.json', opt),
		// 시세 스냅샷만 HF-first — 일배치(buildPricesSnapshot.py)가 매 영업일 HF 를 갱신하는데
		// preferLocal 이면 배포 시점 정적 사본이 영원히 이겨 asOf 가 동결된다 (4/24 사고).
		loadJson<PricesFile>('map/prices-snapshot.json', { fetchFn }),
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
		} as RawData
	};
}
