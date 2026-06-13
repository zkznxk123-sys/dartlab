// scan surface 공개 표면 (§8.1 — 작업면 한 폴더, index.ts 하나가 공개 API).
// 데이터 탐색기·SQL 노트북·스크리너 — landing /scan 라우트(컴포지션 루트)가 마운트. DuckDB-WASM 은 셸이
// provideScanDuckDb 로 주입(seam, SvelteKit/Vite 결합 절제). format·Sparkline 은 surface 자급(복사 — 후속 공유패키지).
// 외부 실소비(routes/scan·companyLive·scanRuntime.worker) import 로 검증된 심볼만 공개.

// ── 컴포넌트 ──
export { default as Grid } from './Grid.svelte';
export { default as ColumnGroupBar } from './ColumnGroupBar.svelte';
export { default as PresetModal } from './PresetModal.svelte';
export { default as CellTooltip } from './CellTooltip.svelte';
export { default as Distribution } from './Distribution.svelte';
export { default as InsightsFeed } from './InsightsFeed.svelte';
export { default as SavedSets } from './SavedSets.svelte';
export { default as Detail } from './Detail.svelte';
export { default as DataExplorer } from './DataExplorer.svelte';

// ── duckdb 쿼리 엔진 + seam ──
export {
	ensureDuckDb,
	loadCompanyChanges,
	provideScanDuckDb,
	type DartDb,
	type CompanyChange,
	type PriceMetrics,
	type ValuationMetrics,
	type DbState
} from './duckSql';
export { loadFinanceLiteRuntime, loadCompanyFinanceLitePeriods } from './financeLiteRuntime';

// ── 페이로드·메트릭·프리셋·타입 ──
export { encodeScanPayload, decodeScanPayload } from './url';
export { DEFAULT_COLUMNS, METRICS_BY_KEY, PINNED_COLUMNS, type MetricGroup } from './metrics';
export { PRESETS_BY_ID, type Preset, type RuntimeLoader } from './presets';
export type { SavedColumnSet, ScanNode, FilterCond, SortKey } from './types';
