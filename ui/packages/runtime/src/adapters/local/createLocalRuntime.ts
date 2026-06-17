// local adapter — 로컬 Python 서버(/api) 데이터 포트 실구현 조립 (책임 경계 02 §9.2).
// silent fallback 금지: 모든 포트 메서드는 단일 경로다 — 부재는 null/[] 정직 표기, 다른 소스 우회 없음.
// 데이터 포트(company·price·filing·finance·viewer·macro·report·scan.changes)=단계-5-2a, AiPort(SSE)=단계-5-2b.
// services(빈 레지스트리)·storage(localStorage)=자족 실구현, navigation=셸 주입(LocalRuntimeOptions)=단계-5-3a.
// map·search 만 단계-8 throw 게이트(호출 시 배선순서 위반 즉시 노출 — 공개 어댑터와 동일 패턴).
import type {
	DartLabRuntime,
	FinancePort,
	NavigationPort,
	RuntimeEnvironment
} from '@dartlab/ui-contracts';
import { createHfMacroPort } from '../public/sources/macroSource';
import { createPublicIndexPort } from '../public/sources/indexSource';
import { loadTerminalFinance } from '../public/sources/financeSource';
import { publicPricePort, publicNewsPort } from '../public/createPublicRuntime';
import { createReportSource } from '../public/sources/reportSource';
import { createServiceRegistry } from '../../services/serviceRegistry';
import { exportServiceRegistration } from '../../services/exportCommand';
import { localExportPort } from './sources/exportSource';
import { notWiredYet } from './fetchJson';
import type { ClientPanelInit, CompanyMeta, LocalCaches, PriceEventsPayload } from './localTypes';
import { localAiPort } from './sources/aiSource';
import { localStoragePort } from './sources/storageSource';
import { localCompanyPort } from './sources/companySource';
import { localFilingPort } from './sources/filingSource';
import { createDataCore } from '../../data/fetch/request';
import { localScanPort } from './sources/scanSource';
import { localViewerPort } from './sources/viewerSource';

export interface LocalRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
	apiBase?: string; // 기본 '' (same-origin /api; dev 는 vite proxy 가 127.0.0.1:8400 으로)
	/** SvelteKit 셸이 $app/navigation goto + $app/paths base 로 구현해 주입 — 어댑터는 framework-agnostic 유지. */
	navigation: NavigationPort;
}

// 터미널 재무 번들의 SSOT 는 발행 HF parquet(dart/finance/{code}.parquet) 이다 — 로컬 /api 엔드포인트가
// 아니라 macro 포트와 동일하게 공개 HF 소스를 공유한다(곧 "로컬이 깃헙페이지 자산을 공유"하는 공통 배선).
// 28 표준계정 정규화·10 카드 계산이 financeSource 한곳에 있어 공개/로컬이 동일 결과 — silent fallback 아닌 단일 경로.
function localFinancePort(): FinancePort {
	return { bundle: loadTerminalFinance };
}

export function createLocalRuntime(options: LocalRuntimeOptions): DartLabRuntime {
	const env: RuntimeEnvironment = { ...options.env, kind: 'local' };
	const apiBase = options.apiBase ?? '';
	// 회사 단위 fetch 1회 공유 (런타임 인스턴스 범위) — price·filing·company 포트가 같은 응답 재사용.
	const caches: LocalCaches = {
		priceEvents: new Map<string, Promise<PriceEventsPayload | null>>(),
		panelInit: new Map<string, Promise<ClientPanelInit | null>>(),
		meta: new Map<string, Promise<CompanyMeta | null>>()
	};
	const dataCore = createDataCore(); // 데이터 워크벤치 SSOT 코어(어댑터당 1) — RuntimeCache·RequestDedup 실배선
	// export Port 를 먼저 만들어 서비스 레지스트리(command)와 runtime.export 양쪽이 같은 인스턴스를 공유.
	const exportPort = localExportPort(apiBase);
	return {
		env,
		company: localCompanyPort(), // 공통배선 — 전부 HF(corpList·relations·profit-pool), 로컬 /api 불요
		// 주가 = 공개 gov HF 포트 재사용 (백엔드 0, 브라우저 단일 경로) — 로컬 :8400 미가동에도 차트가 퍼블릭과 동일.
		price: publicPricePort(),
		// 지수 = gov/indices + FRED 모두 HF 브라우저 직독 → price·macro 와 동일하게 공개 포트 그대로 재사용(백엔드 0).
		index: createPublicIndexPort(),
		filing: localFilingPort(apiBase, caches, dataCore),
		// 뉴스 = private 라 브라우저 직독 불가 → 퍼블릭 워커(/news) 포트 그대로 재사용(price 와 동일 "공유 자산").
		news: publicNewsPort(),
		finance: localFinancePort(),
		viewer: localViewerPort(),
		macro: createHfMacroPort(),
		report: createReportSource(dataCore), // 공통배선 — HF parquet 직독(백엔드 0, 어댑터 코어 주입). 옛 localReportPort 는 null 스텁이라 폐기.
		scan: localScanPort(),
		export: exportPort,
		get map() {
			return notWiredYet('map', '단계-8(map 추출)');
		},
		get search() {
			return notWiredYet('search', '단계-8(search 추출)');
		},
		ai: localAiPort(apiBase),
		// 로컬 명령 레지스트리 — export.tablesToExcel 등록(엔진 완전판 .xlsx). 다운로드 트리거는 surface 가 toast.payload 로.
		services: createServiceRegistry([exportServiceRegistration(exportPort)]),
		navigation: options.navigation, // 셸 주입 (framework-agnostic 유지)
		storage: localStoragePort(),
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
