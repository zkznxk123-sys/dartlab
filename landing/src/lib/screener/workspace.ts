/**
 * 스크리너 워크스페이스 — 다중 탭 LocalStorage 저장.
 *
 * 사용자가 여러 조건 셋을 탭으로 보관하고 한 클릭으로 전환할 수 있게.
 * Excel 시트 패턴. 페이지 진입 시 LocalStorage 에서 자동 복원.
 */

import type { Cond, SortKey } from './types';

const STORAGE_KEY = 'dartlab.screener.workspace.v1';
const MAX_TABS = 12;

export interface ScreenerTab {
	id: string;
	name: string;
	conds: Cond[];
	sorts: SortKey[];
	industries: string[];
	presetId: string | null;
}

export interface Workspace {
	tabs: ScreenerTab[];
	activeTabId: string | null;
}

export function newTabId(): string {
	return `tab-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

export function emptyWorkspace(): Workspace {
	return { tabs: [], activeTabId: null };
}

export function loadWorkspace(): Workspace {
	if (typeof localStorage === 'undefined') return emptyWorkspace();
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return emptyWorkspace();
		const parsed = JSON.parse(raw) as Partial<Workspace>;
		if (!Array.isArray(parsed.tabs)) return emptyWorkspace();
		return {
			tabs: parsed.tabs.slice(0, MAX_TABS),
			activeTabId: parsed.activeTabId ?? null
		};
	} catch {
		return emptyWorkspace();
	}
}

export function saveWorkspace(ws: Workspace): void {
	if (typeof localStorage === 'undefined') return;
	try {
		const trimmed: Workspace = {
			tabs: ws.tabs.slice(0, MAX_TABS),
			activeTabId: ws.activeTabId
		};
		localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
	} catch {
		/* quota exceeded — ignore */
	}
}

export function addTab(ws: Workspace, tab: ScreenerTab): Workspace {
	const tabs = [...ws.tabs, tab].slice(0, MAX_TABS);
	return { tabs, activeTabId: tab.id };
}

export function removeTab(ws: Workspace, tabId: string): Workspace {
	const tabs = ws.tabs.filter((t) => t.id !== tabId);
	const activeTabId = ws.activeTabId === tabId ? (tabs[0]?.id ?? null) : ws.activeTabId;
	return { tabs, activeTabId };
}

export function updateTab(ws: Workspace, tabId: string, patch: Partial<ScreenerTab>): Workspace {
	return {
		...ws,
		tabs: ws.tabs.map((t) => (t.id === tabId ? { ...t, ...patch } : t))
	};
}

export function renameTab(ws: Workspace, tabId: string, name: string): Workspace {
	return updateTab(ws, tabId, { name: name.trim() || '이름없음' });
}
