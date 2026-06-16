// 백테스트 도메인 compat barrel — 기존 7 importer 무수정(03 §0.5.3). 분할: types(계약)·presets(전략)·engine(체결).
export { BT_COSTS, BT_ENGINE_VERSION } from './types';
export type {
	BtPresetKey,
	BtParamDef,
	BtPresetDef,
	BtCostsBp,
	BtTrade,
	BtWarning,
	BtMetrics,
	BtRunSpec,
	BtResult,
	BtSpecInput
} from './types';
export { BT_PRESETS } from './presets';
export { runBacktest } from './engine';
export { runPortfolioBacktest } from './portfolio';
export type { StrategySlot, ComboMetrics, ComboResult, PortfolioBtResult } from './portfolio';
