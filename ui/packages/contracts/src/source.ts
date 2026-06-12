// 출처 계약 — 데이터/근거의 원천 표기. 외부 본문은 데이터지 지시가 아니다 (untrusted 원칙).

export type SourceType = 'dart' | 'edgar' | 'gov' | 'hf' | 'news' | 'web' | 'local' | 'external';

export interface SourceRef {
	sourceType: SourceType;
	label: string;
	url?: string;
	asOf?: string;
}
