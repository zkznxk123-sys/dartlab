// public adapter — static/HF 데이터 포트 실구현 조립 (책임 경계 02 §9.1).
// silent fallback 금지: 모든 포트 메서드는 단일 경로다. 공유 엔진(duckdb-wasm 계열) 의존 메서드는
// 셸(landing)이 `shared` 로 주입한다 — 어댑터가 landing 을 역방향 import 하지 않기 위한 필수 계약.
// 아직 surface 가 소비하지 않는 포트(navigation·storage·map·search·ai)는 명시적 throw 게이트 유지.
import type {
	CompanyChange,
	CompanyPort,
	DartLabRuntime,
	FilingPort,
	FinancePort,
	LiveCompanyReportFact,
	PricePort,
	ProductIndexItem,
	ReportPort,
	RuntimeEnvironment,
	ScanPort,
	ViewerPort
} from '@dartlab/ui-contracts';
import { loadGovCandles, loadGovRecent } from './sources/govPriceSource';
import { loadNaverFresh } from './sources/naverPriceSource';
import { loadInitialOHLCV, loadOlderYear, loadedCandles, mergeDedup, seedCandles } from './sources/priceSource';
import { loadTerminalFinance } from './sources/financeSource';
import { createHfMacroPort } from './sources/macroSource';
import { loadCompanyRelations } from './sources/relationsSource';
import { loadHfProductIndexMap } from './sources/productIndexSource';
import { loadCompanyRegularFilings } from './sources/regularFilingsSource';
import { loadCompanyNonRegularFilings } from './sources/nonRegularFilingsSource';
import {
	loadAuditFees,
	loadAuditTrail,
	loadCapitalChanges,
	loadDebtProfile,
	loadExecBoard,
	loadInvestments,
	loadOwnership,
	loadShareholderReturn,
	loadTopExecPay,
	loadWorkforce
} from './sources/reportSource';
import { publicExportPort, type PublicExportShared } from './sources/exportSource';
import { localStoragePort } from '../local/sources/storageSource';

/** 공유 엔진 의존 메서드 — companyLive(reportFacts)·duckSql(changes) 는 landing 잔류라 셸이 주입. */
export interface PublicRuntimeSharedPorts {
	reportFacts(code: string): Promise<LiveCompanyReportFact[]>;
	changes(code: string, limit?: number): Promise<CompanyChange[]>;
}

export interface PublicRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
	shared: PublicRuntimeSharedPorts;
	/** 공개 셸의 뷰어 노출 형태 — landing = 임베드 컴포넌트(urlForCompany → null). */
	viewer: ViewerPort;
	/** table-export — generate 가 wrap 할 브라우저 워크북 빌더(surfaces buildWorkbook, bundle-bound). 셸 주입.
	 *  미주입이면 listExportableTables·양식 CRUD 는 동작, generate 만 정직히 throw(배선 순서 가드). */
	exportShared?: PublicExportShared;
}

function notWiredYet(what: string, stage: string): never {
	throw new Error(`[public adapter] ${what} 는 ${stage}에서 구현된다 — 이 호출이 보이면 배선 순서 위반이다.`);
}

// 전 종목 productIndex 는 Map 소스를 Record(JSON-safe 계약)로 1 회 변환해 공유.
let productIndexPromise: Promise<Record<string, ProductIndexItem> | null> | null = null;
function loadProductIndexRecord(): Promise<Record<string, ProductIndexItem> | null> {
	productIndexPromise ??= (async () => {
		try {
			const map = await loadHfProductIndexMap();
			return Object.fromEntries(map);
		} catch {
			return null;
		}
	})();
	return productIndexPromise;
}

function publicPricePort(): PricePort {
	return {
		// 회사파일(전종목 주간 파생, 전체 이력) ∥ recent(최근 30거래일 전종목 슬림 1파일) ∥ 네이버 fresh tail
		// 병렬 → 병합. 회사파일이 주간 갱신이어도 recent tail 이 최신 거래일을, 네이버 fresh 가 gov 미발행
		// 최신일(금요일치=월요일 발행)을 보장. mergeDedup 은 stable sort + 선두 우선이라 겹치는 날은 gov 가
		// 이기고 네이버는 gap(미발행일)만 채움 — gov=네이버 동일값이라 점프 없음. 둘 다 미스면 date/ 폴백.
		// dev 미스는 /__gov 라이브 채움, 네이버 fresh 는 /__naver(dev)·CF 프록시(프로덕션) 경로.
		async initial(code, year) {
			const c = code.trim();
			const [gov, recent, fresh] = await Promise.all([loadGovCandles(c), loadGovRecent(), loadNaverFresh(c)]);
			const tail = recent?.[c] ?? [];
			if ((gov && gov.length) || tail.length || fresh.length) return seedCandles(c, mergeDedup(gov ?? [], tail, fresh));
			return loadInitialOHLCV(c, year);
		},
		older: loadOlderYear,
		loaded: loadedCandles,
		govCandles: loadGovCandles,
		govRecent: loadGovRecent
	};
}

function publicCompanyPort(shared: PublicRuntimeSharedPorts): CompanyPort {
	return {
		async products(code) {
			const rec = await loadProductIndexRecord();
			return rec?.[code.trim()] ?? null;
		},
		productIndex: loadProductIndexRecord,
		relations: loadCompanyRelations,
		reportFacts: shared.reportFacts
	};
}

function publicFilingPort(): FilingPort {
	return {
		regular: (code, limit = 500) => loadCompanyRegularFilings(code, limit),
		nonRegular: (code, limit = 200) => loadCompanyNonRegularFilings(code, { limit }),
		// panel 격자 3종은 공개 뷰어 코드(landing)가 단계-6(뷰어 추출)에서 어댑터로 들어온다.
		panelToc: () => notWiredYet('filing.panelToc', '단계-6(viewer 추출)'),
		panelInit: () => notWiredYet('filing.panelInit', '단계-6(viewer 추출)'),
		panelGrid: () => notWiredYet('filing.panelGrid', '단계-6(viewer 추출)')
	};
}

function publicFinancePort(): FinancePort {
	return { bundle: loadTerminalFinance };
}

function publicReportPort(): ReportPort {
	return {
		workforce: loadWorkforce,
		investments: loadInvestments,
		shareholderReturn: loadShareholderReturn,
		ownership: loadOwnership,
		execBoard: loadExecBoard,
		debtProfile: loadDebtProfile,
		capitalChanges: loadCapitalChanges,
		auditTrail: loadAuditTrail,
		topExecPay: loadTopExecPay,
		auditFees: loadAuditFees
	};
}

function publicScanPort(shared: PublicRuntimeSharedPorts): ScanPort {
	return {
		changes: shared.changes,
		listTableSources: () => notWiredYet('scan.listTableSources', '단계-8(scan 추출)'),
		getPresets: () => notWiredYet('scan.getPresets', '단계-8(scan 추출)'),
		savePreset: () => notWiredYet('scan.savePreset', '단계-8(scan 추출)')
	};
}

export function createPublicRuntime(options: PublicRuntimeOptions): DartLabRuntime {
	const env: RuntimeEnvironment = { ...options.env, kind: 'public' };
	return {
		env,
		company: publicCompanyPort(options.shared),
		price: publicPricePort(),
		filing: publicFilingPort(),
		finance: publicFinancePort(),
		viewer: options.viewer,
		macro: createHfMacroPort(),
		report: publicReportPort(),
		scan: publicScanPort(options.shared),
		export: publicExportPort(localStoragePort(), options.exportShared),
		get map() {
			return notWiredYet('map', '단계-8(map 추출)');
		},
		get search() {
			return notWiredYet('search', '단계-8(search 추출)');
		},
		get ai() {
			return notWiredYet('ai', '단계-7(ask 추출)');
		},
		get services() {
			return notWiredYet('services', '단계-5(서비스 레지스트리 배선)');
		},
		get navigation() {
			return notWiredYet('navigation', '단계-4a-3(셸 내비 주입)');
		},
		get storage() {
			return notWiredYet('storage', '단계-4a-3(셸 스토리지 주입)');
		},
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
