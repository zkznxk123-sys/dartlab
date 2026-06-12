// 내비게이션 계약 — surface 는 window.location/`$app` 을 직접 알지 않는다 (02 §1).
import type { ViewerOpenOptions } from './viewer';
import type { EvidenceSelection } from './evidence';

export interface AskContext {
	code?: string;
	evidence?: EvidenceSelection[];
}

export type DartLabRoute =
	| { kind: 'terminal'; code: string }
	| { kind: 'viewer'; code: string; options?: ViewerOpenOptions }
	| { kind: 'company'; code: string }
	| { kind: 'chat' }
	| { kind: 'ask'; context?: AskContext };

export interface NavigationPort {
	toTerminal(code: string): Promise<void>;
	toViewer(code: string, options?: ViewerOpenOptions): Promise<void>;
	toCompany(code: string): Promise<void>;
	toAsk(initialContext?: AskContext): Promise<void>;
	href(route: DartLabRoute): string;
}
