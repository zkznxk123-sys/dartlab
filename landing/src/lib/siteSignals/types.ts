export type SignalStatus = 'inactive' | 'planned' | 'active' | 'excluded';

export type SignalGroup = 'collect' | 'exclude' | 'public' | 'storage';

export type SignalWindowKey = '7d' | '30d' | '90d' | 'all';

export type SiteSignalKey =
	| 'pageView'
	| 'dwellBucket'
	| 'scrollDepth'
	| 'ctaClick'
	| 'viewerOpen'
	| 'dataDownload'
	| 'searchText'
	| 'sessionReplay'
	| 'rawIp'
	| 'userAgent';

export type SiteSignalSpec = {
	key: SiteSignalKey;
	group: SignalGroup;
	label: string;
	eventName: string;
	status: SignalStatus;
	storage: string;
	publicLevel: string;
	purpose: string;
};

export type SignalWindow = {
	key: SignalWindowKey;
	label: string;
	days: number | null;
};

export type SiteSignalSummary = {
	count?: number;
	sampleN?: number;
	bucket?: string;
};

export type SiteSignalsPublicPayload = {
	version: 1;
	status: 'inactive' | 'active';
	generatedAt: string;
	source: string;
	minPublicSample: number;
	windows: SignalWindow[];
	summaries: Partial<Record<SignalWindowKey, Partial<Record<SiteSignalKey, SiteSignalSummary>>>>;
};

export type RailSectionKey = 'overview' | 'collect' | 'exclude' | 'public' | 'storage' | 'rollout';

export type RailSection = {
	key: RailSectionKey;
	label: string;
	kicker: string;
};
