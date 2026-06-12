// 스토리지 계약 — surface 네임스페이스 키 기본 (02 §8): surface 내부 기능 추가가 contracts 개정을
// 강제하지 않도록 템플릿 리터럴 키. 닫힌 union 은 전역 키만.

export type DartLabSurfaceId = 'terminal' | 'viewer' | 'company' | 'scan' | 'map' | 'search' | 'ask';

export type GlobalStorageKey = 'lastCompany' | 'recentCompanies' | 'locale';

export type RuntimeStorageKey = `${DartLabSurfaceId}.${string}` | GlobalStorageKey;
// 예: 'terminal.chartState', 'terminal.backtestConfig', 'viewer.layout', 'ask.draft'

export interface StoragePort {
	get<T>(key: RuntimeStorageKey): Promise<T | null>;
	set<T>(key: RuntimeStorageKey, value: T): Promise<void>;
	remove(key: RuntimeStorageKey): Promise<void>;
	subscribe<T>(key: RuntimeStorageKey, cb: (value: T | null) => void): () => void;
}
