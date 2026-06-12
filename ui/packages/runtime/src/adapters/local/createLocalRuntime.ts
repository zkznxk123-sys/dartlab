// local adapter skeleton — 구현은 단계-4a~5 에서 채운다.
// 책임 경계(02 §9.2): /api/* 로컬 서버·provider 는 Ask 엔진 뒤·HF/static fallback 을 surface 에 노출 금지.
// silent fallback 금지 — 미구현 호출은 명시적 오류로 실패한다.
import type { DartLabRuntime, RuntimeEnvironment } from '@dartlab/ui-contracts';

export interface LocalRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
	apiBase?: string; // 기본 '' (same-origin /api)
}

function notImplemented(port: string): never {
	throw new Error(`[local adapter] ${port} 는 단계-4a~5에서 구현된다 — 이 호출이 보이면 배선 순서 위반이다.`);
}

export function createLocalRuntime(options: LocalRuntimeOptions): DartLabRuntime {
	const env: RuntimeEnvironment = { ...options.env, kind: 'local' };
	return {
		env,
		get company() {
			return notImplemented('company');
		},
		get price() {
			return notImplemented('price');
		},
		get filing() {
			return notImplemented('filing');
		},
		get finance() {
			return notImplemented('finance');
		},
		get viewer() {
			return notImplemented('viewer');
		},
		get macro() {
			return notImplemented('macro');
		},
		get report() {
			return notImplemented('report');
		},
		get scan() {
			return notImplemented('scan');
		},
		get map() {
			return notImplemented('map');
		},
		get search() {
			return notImplemented('search');
		},
		get ai() {
			return notImplemented('ai');
		},
		get services() {
			return notImplemented('services');
		},
		get navigation() {
			return notImplemented('navigation');
		},
		get storage() {
			return notImplemented('storage');
		},
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
