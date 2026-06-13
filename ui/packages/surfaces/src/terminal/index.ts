// terminal surface 공개 표면 (§8.1 — 작업면 한 폴더, index.ts 하나가 공개 API).
// 셸(landing route · ui/web 브리지)이 소비하는 마운트 표면 + 셸 글루(routeLoad)가 쓰는 데이터 형태만 공개.
// 내부 부품(panels·charts·ui·engine 헬퍼)은 비공개 — 트리 내부 상대 import 로만 접근.
export { default as TerminalSurface } from './TerminalSurface.svelte';
export { createEngine } from './data/engine';
export type { Engine } from './data/engine';
export type {
	TerminalHosts,
	TerminalBrandLinks,
	ViewerStudioHostProps,
	FinanceDialogHostProps
} from './data/hosts';
export { LAST_SYM_KEY } from './data/lastSymbol';
export { warmCompany } from './data/warmup';
// 데이터 형태 — landing 셸 글루(terminal-shell/routeLoad.ts)의 RawData 조립 + ui/web 브리지(localTerminalData) 소비.
export type {
	RawData,
	FinanceCompany,
	FinanceFile,
	MacroFile,
	MetaFile,
	PricesFile,
	IndexRow,
	EcosystemFile,
	QuartersFile
} from './data/types';
