// 서비스 계약 — terminal mode 의 service command registry (02 §7).
// 열화 티어 UX: localOnly 는 "존재는 보이되 실행 불가 + upgradeHint" — 완전 숨김은 시스템 명령만 (03 §1-7).

export type ServiceGroup = 'market' | 'filing' | 'finance' | 'viewer' | 'ai' | 'workspace' | 'export' | 'system';

export type ServiceAvailability = 'available' | 'localOnly' | 'disabled' | 'loading' | 'error';

export interface ServiceDescriptor {
	id: string;
	label: string;
	group: ServiceGroup;
	availability: ServiceAvailability;
	reason?: string;
	upgradeHint?: string; // localOnly 일 때 "로컬에서 사용 가능" 안내 — command palette 가 렌더
}

export interface ServiceRequirement {
	kind: 'code' | 'period' | 'filing' | 'evidence' | 'query';
}

export interface ServiceCommand {
	id: string;
	serviceId: string;
	label: string;
	icon?: string;
	shortcut?: string;
	mode: 'chat' | 'terminal' | 'both';
	requires?: ServiceRequirement[];
}

export interface ServiceContext {
	code?: string;
	period?: string;
	mode: 'chat' | 'terminal';
}

export interface ServiceCommandInput {
	commandId: string;
	context: ServiceContext;
	args?: Record<string, unknown>;
}

/** command 실행 결과는 status·toast·panel update·Ask event 중 하나로 normalize (02 §6.2). */
export interface ServiceCommandResult {
	kind: 'status' | 'toast' | 'panel' | 'ask';
	ok: boolean;
	message?: string;
	payload?: unknown;
}

export interface ServiceStatusEvent {
	serviceId: string;
	availability: ServiceAvailability;
	reason?: string;
}

export interface ServicesPort {
	listServices(context: ServiceContext): Promise<ServiceDescriptor[]>;
	listCommands(context: ServiceContext): Promise<ServiceCommand[]>;
	executeCommand(input: ServiceCommandInput): Promise<ServiceCommandResult>;
	subscribeStatus(cb: (status: ServiceStatusEvent) => void): () => void;
}
