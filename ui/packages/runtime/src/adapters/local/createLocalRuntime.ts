// local adapter — 로컬 Python 서버(/api) 데이터 포트 실구현 조립 (책임 경계 02 §9.2).
// silent fallback 금지: 모든 포트 메서드는 단일 경로다 — 부재는 null/[] 정직 표기, 다른 소스 우회 없음.
// 데이터 포트(company·price·filing·finance·viewer·macro·report·scan.changes)=단계-5-2a, AiPort(SSE)=단계-5-2b.
// services·navigation·storage 는 단계-5-3(셸 주입), map·search 는 단계-8 —
// 미배선은 명시적 throw 게이트(공개 어댑터와 동일 패턴, 호출 시 배선순서 위반 즉시 노출).
import type { Candle, DartLabRuntime, FinancePort, RuntimeEnvironment } from '@dartlab/ui-contracts';
import { createHfMacroPort } from '../public/sources/macroSource';
import { notWiredYet } from './fetchJson';
import type { ClientPanelInit, CompanyMeta, LocalCaches, PriceEventsPayload } from './localTypes';
import { localAiPort } from './sources/aiSource';
import { localCompanyPort } from './sources/companySource';
import { localFilingPort } from './sources/filingSource';
import { localPricePort } from './sources/priceSource';
import { localReportPort } from './sources/reportSource';
import { localScanPort } from './sources/scanSource';
import { localViewerPort } from './sources/viewerSource';

export interface LocalRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
	apiBase?: string; // 기본 '' (same-origin /api; dev 는 vite proxy 가 127.0.0.1:8400 으로)
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
		get services() {
			return notWiredYet('services', '단계-5-3(서비스 레지스트리 배선)');
		},
		get navigation() {
			return notWiredYet('navigation', '단계-5-3(셸 내비 주입)');
		},
		get storage() {
			return notWiredYet('storage', '단계-5-3(셸 스토리지 주입)');
		},
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
