// TanStack Query key 카탈로그 — dashboard 도메인 한정.
// 다른 도메인 (chat 등) 과 prefix 'dash' 로 격리.

export const dashKeys = {
	all: ['dash'] as const,
	search: (q: string) => ['dash', 'search', q] as const,
	dashboard: (code: string, periodKind: 'annual' | 'quarterly' = 'annual') =>
		['dash', 'dashboard', code, periodKind] as const,
	tabDashboard: (
		tab: string,
		code: string,
		periodKind: 'annual' | 'quarterly' = 'annual',
	) => ['dash', 'tab', tab, code, periodKind] as const,
	tabLayout: (
		tab: string,
		code: string,
		view: string | null,
		periodKind: 'annual' | 'quarterly' = 'annual',
	) => ['dash', 'layout', tab, code, view ?? 'none', periodKind] as const,
	card: (cardKey: string, code: string, periodKind: 'annual' | 'quarterly' = 'annual') =>
		['dash', 'card', cardKey, code, periodKind] as const,
	catalog: () => ['dash', 'catalog'] as const,
	companyMeta: (code: string) => ['dash', 'companyMeta', code] as const,
	companyIndex: (code: string) => ['dash', 'companyIndex', code] as const,
	companyTopic: (code: string, topic: string) => ['dash', 'companyTopic', code, topic] as const,
	companyScanAll: (code: string) => ['dash', 'companyScanAll', code] as const,
	companyInsights: (code: string) => ['dash', 'companyInsights', code] as const,
	companyNetwork: (code: string, hops = 1) => ['dash', 'companyNetwork', code, hops] as const,
	terminalBundle: (code: string) => ['dash', 'terminalBundle', code] as const,
};
