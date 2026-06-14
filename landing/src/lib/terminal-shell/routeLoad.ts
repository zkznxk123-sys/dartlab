// /terminal(본진) · /lab/terminal-dev(격리 개발) 공용 라우트 로더 SSOT — 복사 드리프트 차단.
// landing 셸 글루: getPublicRuntime(컴포지션 루트)·$app 의존이라 surface 패키지로 못 옮긴다 (단계-4b).
// 씨데이터 JSON 7종 병렬 로드 + 마지막 본 종목 워밍업(주가·재무·제품맵 — public runtime 포트 경유).
import { browser } from '$app/environment';
import { base } from '$app/paths';
import { loadJson, setStaticBase } from '@dartlab/ui-runtime/data/dartlabData';
import { getPublicRuntime } from '$lib/runtime/publicRuntime';
import {
	LAST_SYM_KEY,
	warmCompany,
	type FinanceFile,
	type MacroFile,
	type MetaFile,
	type PricesFile,
	type IndexRow,
	type EcosystemFile,
	type QuartersFile,
	type IndustryStatsFile,
	type RawData
} from '@dartlab/ui-surfaces/terminal';

// ⚠ base 주입을 모듈 평가 시점에 강제한다. +layout.svelte 의 setStaticBase 는 컴포넌트 스크립트라
// +page.ts 의 load(=loadTerminalRaw) 보다 늦게 돈다 — 그 사이 runtime base='' 라 GitHub Pages 에서
// `${base}/map/ecosystem.json` 이 `/map/ecosystem.json`(앞 슬래시) 로 나가 404 → HF 폴백(다른/느린
// 씨데이터)으로 빠졌다. 이 모듈은 +page.ts 가 import 하는 순간(=load 호출 전) 평가되므로 여기서
// 한 번 박으면 터미널 load 가 항상 deploy 된 정적 씨데이터를 먼저 맞힌다.
setStaticBase(base);

export async function loadTerminalRaw(fetchFn: typeof fetch): Promise<{ raw: RawData }> {
	// 일별시세 조기 워밍 — 마지막 본 종목(없으면 기본 005930)의 주가·재무를 씨데이터 JSON 로드와
	// 병렬로 시작 (in-flight dedup 이라 패널 호출과 중복 fetch 0). 차트 첫 페인트 ~2s 단축.
	if (browser) {
		const last = localStorage.getItem(LAST_SYM_KEY) || '005930';
		warmCompany(getPublicRuntime(), last);
	}
	const opt = { fetchFn, preferLocal: true };
	const [finance, macro, meta, prices, index, eco, quarters, industryStats] = await Promise.all([
		loadJson<FinanceFile>('dashboards/finance.json', opt),
		// macro 도 HF-first — mapBuild 가 매일 publish 하는 소형 파일 (git 정적 사본 동결 사고 재발 방지)
		loadJson<MacroFile>('dashboards/macro.json', { fetchFn }),
		loadJson<MetaFile>('dashboards/meta.json', opt),
		// 시세 스냅샷만 HF-first — 일배치(buildPricesSnapshot.py)가 매 영업일 HF 를 갱신하는데
		// preferLocal 이면 배포 시점 정적 사본이 영원히 이겨 asOf 가 동결된다 (4/24 사고).
		loadJson<PricesFile>('map/prices-snapshot.json', { fetchFn }),
		loadJson<IndexRow[]>('map/search-index.json', opt),
		loadJson<EcosystemFile>('map/ecosystem.json', opt),
		loadJson<QuartersFile>('dashboards/quarters.json', opt),
		// 업종 분포 밴드 — map 이 쓰던 자산(p10~p90), 스캔등급 다이얼로그 분포 컨텍스트용. 정적 동결 OK(일배치 무관).
		loadJson<IndustryStatsFile>('map/industryStats.json', opt)
	]);
	return {
		raw: {
			finance: finance ?? { years: [], companies: {} },
			macro: macro ?? null,
			meta: meta ?? null,
			prices: prices ?? { data: {} },
			index: index ?? [],
			eco: eco ?? null,
			quarters: quarters ?? null,
			industryStats: industryStats ?? null
		} as RawData
	};
}
