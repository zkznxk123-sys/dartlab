import type { CompanyRelations } from './relations';
import type {
	AuditFeeYear,
	AuditYear,
	CapitalChangesBundle,
	DebtProfileBundle,
	ExecBoardYear,
	InvestmentsBundle,
	OwnershipYear,
	ShareholderReturnYear,
	TopExecPay,
	WorkforceYear
} from './reportSeries';
import type { Candle, CompanyPrices } from './priceSeries';
import type { TerminalFinanceBundle } from './terminalFinance';
import type { ProductIndexItem } from '$lib/data/productIndexRuntime';
import type { RegularFiling } from '$lib/data/companyFilingsRuntime';
import type { NonRegularFiling } from '$lib/data/companyNonRegularFilings';
import type { LiveCompanyReportFact } from '$lib/browser/companyLive';
import type { CompanyChange } from '$lib/scan/duckSql';

export interface LocalTerminalAdapter {
	loadPriceInitial?: (code: string, year: number) => Promise<CompanyPrices | null>;
	loadPriceOlder?: (code: string, targetYear: number) => Promise<Candle[]>;
	loadedCandles?: (code: string) => Candle[];
	loadGovCandles?: (code: string) => Promise<Candle[] | null>;
	loadGovRecent?: () => Promise<Map<string, Candle[]> | null>;
	loadTerminalFinance?: (code: string) => Promise<TerminalFinanceBundle | null>;
	productIndex?: () => Promise<Map<string, ProductIndexItem> | null>;
	products?: (code: string) => Promise<ProductIndexItem | null>;
	relations?: (code: string) => Promise<CompanyRelations | null>;
	regularFilings?: (code: string) => Promise<RegularFiling[]>;
	nonRegularFilings?: (code: string) => Promise<NonRegularFiling[]>;
	reportFacts?: (code: string) => Promise<LiveCompanyReportFact[]>;
	changes?: (code: string, limit?: number) => Promise<CompanyChange[]>;
	loadWorkforce?: (code: string) => Promise<WorkforceYear[] | null>;
	loadInvestments?: (code: string) => Promise<InvestmentsBundle | null>;
	loadShareholderReturn?: (code: string) => Promise<ShareholderReturnYear[] | null>;
	loadOwnership?: (code: string) => Promise<OwnershipYear[] | null>;
	loadExecBoard?: (code: string) => Promise<ExecBoardYear[] | null>;
	loadDebtProfile?: (code: string) => Promise<DebtProfileBundle | null>;
	loadCapitalChanges?: (code: string) => Promise<CapitalChangesBundle | null>;
	loadAuditTrail?: (code: string) => Promise<AuditYear[] | null>;
	loadTopExecPay?: (code: string) => Promise<TopExecPay | null>;
	loadAuditFees?: (code: string) => Promise<AuditFeeYear[] | null>;
	viewerUrl?: (code: string, vs?: string[]) => string | null;
	prefetch?: (code: string, priceYear: number) => void;
}

export function localTerminalAdapter(): LocalTerminalAdapter | null {
	if (typeof window === 'undefined') return null;
	return ((window as unknown as { __DARTLAB_LOCAL_TERMINAL__?: LocalTerminalAdapter }).__DARTLAB_LOCAL_TERMINAL__ ?? null);
}
