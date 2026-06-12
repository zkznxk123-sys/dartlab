// 뷰어 계약 — standalone route / embedded component / external url 3형 (02 §3.4).
import type { RegularFiling, NonRegularFiling } from './filing';

export interface ViewerOpenOptions {
	vs?: string[]; // N사 비교 (?vs=)
	period?: string;
	sectionKey?: string;
}

export interface ViewerPort {
	mode: 'embedded-route' | 'component' | 'external-url';
	urlForCompany(code: string, options?: ViewerOpenOptions): string | null;
	openCompany(code: string, options?: ViewerOpenOptions): Promise<void>;
	openFiling(filing: RegularFiling | NonRegularFiling): Promise<void>;
}
