export interface TerminalParityPanel {
	id: string;
	label: string;
	source: 'company' | 'scan' | 'priceEvents' | 'network' | 'viewer';
}

export const TERMINAL_PARITY_PANELS: TerminalParityPanel[] = [
	{ id: 'company-card', label: '회사', source: 'company' },
	{ id: 'disclosure-index', label: '공시 인덱스', source: 'viewer' },
	{ id: 'kpi-strip', label: 'KPI', source: 'company' },
	{ id: 'price-events', label: '가격 · 공시 · 뉴스 이벤트', source: 'priceEvents' },
	{ id: 'financial-statements', label: '재무제표', source: 'company' },
	{ id: 'insight-summary', label: '요약', source: 'company' },
	{ id: 'risk-flags', label: '리스크 경고등', source: 'scan' },
	{ id: 'capital-debt-workforce', label: '환원 · 채무 · 인력', source: 'scan' },
	{ id: 'scan-board', label: '스캔 보드', source: 'scan' },
	{ id: 'network-peers', label: '관계 · 동종', source: 'network' },
	{ id: 'dart-facts', label: 'DART 팩트', source: 'viewer' },
];

export const TERMINAL_DATA_SOURCES = [
	'price-events',
	'company scan',
	'company show',
	'company index',
	'company insights',
	'company network',
];
