import type {
	RailSection,
	SignalWindow,
	SiteSignalSpec,
	SiteSignalsPublicPayload
} from './types';

export const SIGNAL_WINDOWS: SignalWindow[] = [
	{ key: '7d', label: '7일', days: 7 },
	{ key: '30d', label: '30일', days: 30 },
	{ key: '90d', label: '90일', days: 90 },
	{ key: 'all', label: '전체', days: null }
];

export const RAIL_SECTIONS: RailSection[] = [
	{ key: 'overview', label: '개요', kicker: '원칙' },
	{ key: 'collect', label: '보는 것', kicker: '집계 신호' },
	{ key: 'exclude', label: '안 보는 것', kicker: '차단 항목' },
	{ key: 'public', label: '공개 지표', kicker: '표본 기준' },
	{ key: 'storage', label: '저장 흐름', kicker: 'D1 집계' },
	{ key: 'rollout', label: '변경 이력', kicker: '단계' }
];

export const SIGNAL_SPECS: SiteSignalSpec[] = [
	{
		key: 'pageView',
		group: 'collect',
		label: '페이지뷰',
		eventName: 'pageView',
		status: 'planned',
		storage: '일자 × 경로 counter',
		publicLevel: '집계 공개',
		purpose: '실제로 읽히는 문서와 도구 진입면 확인'
	},
	{
		key: 'dwellBucket',
		group: 'collect',
		label: '체류 구간',
		eventName: 'dwell',
		status: 'planned',
		storage: '일자 × 경로 × 시간구간 counter',
		publicLevel: '구간 집계 공개',
		purpose: '문서가 너무 길거나 중간에서 막히는 지점 확인'
	},
	{
		key: 'scrollDepth',
		group: 'collect',
		label: '스크롤 깊이',
		eventName: 'scrollDepth',
		status: 'planned',
		storage: '일자 × 경로 × 깊이구간 counter',
		publicLevel: '구간 집계 공개',
		purpose: '첫 화면·중간 섹션·하단 CTA의 도달률 확인'
	},
	{
		key: 'ctaClick',
		group: 'collect',
		label: 'CTA 클릭',
		eventName: 'ctaClick',
		status: 'planned',
		storage: '일자 × 경로 × target counter',
		publicLevel: '집계 공개',
		purpose: 'Viewer, Terminal, Skills 같은 핵심 진입 흐름 확인'
	},
	{
		key: 'viewerOpen',
		group: 'collect',
		label: '뷰어 진입',
		eventName: 'viewerOpen',
		status: 'planned',
		storage: '일자 × route family counter',
		publicLevel: '집계 공개',
		purpose: '정적 문서에서 실제 작업면으로 넘어가는 비율 확인'
	},
	{
		key: 'dataDownload',
		group: 'collect',
		label: '데이터 다운로드',
		eventName: 'dataDownload',
		status: 'planned',
		storage: '일자 × 파일종류 counter',
		publicLevel: '집계 공개',
		purpose: '공개 데이터셋 사용 흐름 확인'
	},
	{
		key: 'searchText',
		group: 'exclude',
		label: '검색어 원문',
		eventName: 'searchText',
		status: 'excluded',
		storage: '저장 안 함',
		publicLevel: '공개 안 함',
		purpose: '사용자 입력값은 사이트 신호 수집 범위에서 제외'
	},
	{
		key: 'sessionReplay',
		group: 'exclude',
		label: '세션 리플레이',
		eventName: 'sessionReplay',
		status: 'excluded',
		storage: '저장 안 함',
		publicLevel: '공개 안 함',
		purpose: '화면 녹화는 공개 문서 사이트 기준 과수집'
	},
	{
		key: 'rawIp',
		group: 'exclude',
		label: '원시 IP',
		eventName: 'rawIp',
		status: 'excluded',
		storage: '저장 안 함',
		publicLevel: '공개 안 함',
		purpose: '중복 방지보다 식별자 비저장을 우선'
	},
	{
		key: 'userAgent',
		group: 'exclude',
		label: 'User-Agent 원문',
		eventName: 'userAgent',
		status: 'excluded',
		storage: '저장 안 함',
		publicLevel: '공개 안 함',
		purpose: '기기/브라우저 분석은 필요해도 원문 fingerprint는 저장하지 않음'
	}
];

export const INITIAL_PUBLIC_PAYLOAD: SiteSignalsPublicPayload = {
	version: 1,
	status: 'inactive',
	generatedAt: '2026-06-11T00:00:00.000Z',
	source: 'landing/static/site-signals/rolling.json',
	minPublicSample: 10,
	windows: SIGNAL_WINDOWS,
	summaries: {
		'7d': {},
		'30d': {},
		'90d': {},
		all: {}
	}
};

export const STORAGE_STEPS = [
	{
		label: 'Browser',
		title: '브라우저 이벤트',
		body: '페이지·버튼·구간 같은 작고 명시적인 신호만 만든다. 검색어와 입력값은 payload에 넣지 않는다.'
	},
	{
		label: 'Worker',
		title: 'Cloudflare Worker',
		body: 'origin, method, event allowlist를 검증하고 경로·버킷을 정규화한다. IP와 User-Agent는 읽더라도 저장하지 않는다.'
	},
	{
		label: 'D1',
		title: 'D1 집계 테이블',
		body: '원시 row를 쌓지 않고 일자 × 경로 × 이벤트 × 버킷 counter만 증가시킨다.'
	},
	{
		label: 'Public JSON',
		title: '공개 집계본',
		body: '최소 표본 기준을 넘긴 집계만 landing/static/site-signals/*.json으로 노출한다.'
	}
];

export const ROLLOUT_STEPS = [
	{ label: '0', title: '원칙 공개', state: '현재', body: '수집 범위와 제외 항목을 먼저 고정한다.' },
	{ label: '1', title: 'Worker 배포', state: '다음', body: 'D1 집계 수신단을 배포하되 사이트 전역 배선은 별도 변경으로 둔다.' },
	{ label: '2', title: '소량 계측', state: '후속', body: '페이지뷰와 CTA 클릭부터 켠다. 체류·스크롤은 검증 후 추가한다.' },
	{ label: '3', title: '공개 JSON', state: '후속', body: 'k>=10 표본 기준을 통과한 집계만 화면에 연결한다.' }
];
