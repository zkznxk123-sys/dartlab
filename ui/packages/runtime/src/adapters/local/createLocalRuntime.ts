// local adapter — 로컬 Python 서버(/api) 데이터 포트 실구현 조립 (책임 경계 02 §9.2).
// silent fallback 금지: 모든 포트 메서드는 단일 경로다 — 부재는 null/[] 정직 표기, 다른 소스 우회 없음.
// 데이터 포트(company·price·filing·finance·viewer·macro·report·scan.changes)=단계-5-2a, AiPort(SSE)=단계-5-2b.
// services(빈 레지스트리)·storage(localStorage)=자족 실구현, navigation=셸 주입(LocalRuntimeOptions)=단계-5-3a.
// map·search 만 단계-8 throw 게이트(호출 시 배선순서 위반 즉시 노출 — 공개 어댑터와 동일 패턴).
import type {
	Candle,
	DartLabRuntime,
	FinancePort,
	NavigationPort,
	RuntimeEnvironment
} from '@dartlab/ui-contracts';
import { createHfMacroPort } from '../public/sources/macroSource';
import { createServiceRegistry } from '../../services/serviceRegistry';
import { notWiredYet } from './fetchJson';
import type { ClientPanelInit, CompanyMeta, LocalCaches, PriceEventsPayload } from './localTypes';
import { localAiPort } from './sources/aiSource';
import { localStoragePort } from './sources/storageSource';
import { localCompanyPort } from './sources/companySource';
import { localFilingPort } from './sources/filingSource';
import { localPricePort } from './sources/priceSource';
import { localReportPort } from './sources/reportSource';
import { localScanPort } from './sources/scanSource';
import { localViewerPort } from './sources/viewerSource';

export interface LocalRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
	apiBase?: string; // 기본 '' (same-origin /api; dev 는 vite proxy 가 127.0.0.1:8400 으로)
	/** SvelteKit 셸이 $app/navigation goto + $app/paths base 로 구현해 주입 — 어댑터는 framework-agnostic 유지. */
	navigation: NavigationPort;
}

// 로컬 서버는 정규화 재무 번들 엔드포인트 미보유 — null = 데이터셋 미존재 정직 표기.
// (공개 어댑터는 HF parquet; 로컬은 후속 단계에서 /api 재무 엔드포인트 신설 시 배선.)
function localFinancePort(): FinancePort {
	return {
		async bundle() {
			return null;
		}
	};
}

export function createLocalRuntime(options: LocalRuntimeOptions): DartLabRuntime {
	const env: RuntimeEnvironment = { ...options.env, kind: 'local' };
	const apiBase = options.apiBase ?? '';
	// 회사 단위 fetch 1회 공유 (런타임 인스턴스 범위) — price·filing·company 포트가 같은 응답 재사용.
	const caches: LocalCaches = {
		priceEvents: new Map<string, Promise<PriceEventsPayload | null>>(),
		loadedCandles: new Map<string, Candle[]>(),
		panelInit: new Map<string, Promise<ClientPanelInit | null>>(),
		meta: new Map<string, Promise<CompanyMeta | null>>()
	};
	return {
		env,
		company: localCompanyPort(apiBase, caches),
		price: localPricePort(apiBase, caches),
		filing: localFilingPort(apiBase, caches),
		finance: localFinancePort(),
		viewer: localViewerPort(),
		macro: createHfMacroPort(),
		report: localReportPort(),
		scan: localScanPort(),
		get map() {
			return notWiredYet('map', '단계-8(map 추출)');
		},
		get search() {
			return notWiredYet('search', '단계-8(search 추출)');
		},
		ai: localAiPort(apiBase),
		services: createServiceRegistry([]), // 로컬 명령 레지스트리 — 등록은 후속(빈 레지스트리=명령 없음 정직)
		navigation: options.navigation, // 셸 주입 (framework-agnostic 유지)
		storage: localStoragePort(),
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
